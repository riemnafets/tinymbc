#!/usr/bin/env python3

################################################################################################
## IMPORTS
################################################################################################
import sys
import signal
import argparse
import socket
from array import array
from struct import unpack, pack
from math import ceil
from random import randint


################################################################################################
# GLOBAL FUNCTIONS
################################################################################################

#-----------------------------------------------------------------------------------------------
# CONVERSION FUNCTIONS
#-----------------------------------------------------------------------------------------------
def uint16ToInt16(ui):
    if (ui < 0 or ui > 65536):
        raise ValueError
    if (ui > 32767):
        return ui - 65536
    else:
        return ui

def int16ToUint16(i):
    if (i < -32768 or i > 32767):
        raise ValueError
    if (i < 0):
        return i + 65536
    else:
        return i

def hexByteToChr(byte):
    nr = int(byte, 16)
    # return empty string if character is not printable
    if(nr >= 0 and nr < 32): return ""
    elif(nr < 256):          return chr(nr)
    else:                    raise ValueError

def uint16ToDoubleChar(val):
    if (val > 65535 or val < 0):
        raise ValueError
    hexstr = hex(val)
    hexstr = hexstr[2:].zfill(4)  # remove '0x' and pad with zeros to ensure 4 chars = 2 bytes
    chr1 = hexByteToChr(hexstr[:2])
    chr2 = hexByteToChr(hexstr[2:])
    return(chr1 + " " + chr2)

def stringToValidAddress(addrStr):
    addr = int(addrStr)
    if (addr > 65535 or addr < 0):
        raise ValueError
    return addr

def stringToValidValue(valStr):
    if (valStr[:2] == "0x"): 
        val = int(valStr, 16)
    else:
        val = int(valStr)
    if(val < 0):
        val = uint16ToInt16(val)
    if(val < 0 or val > 65535):
        raise ValueError
    return val

def modbusExceptionCodeToString(exceptionCode):
    CODE_MAP = {
        1: "Illegal Function Code",
        2: "Illegal Data Address",
        3: "Illegal Data Value",
        4: "Server Failure",
        5: "Acknowledge",
        6: "Server Busy",
        10: "Gateway Problem (0x0A)",
        11: "Gateway Problem (0x0B)"
    }
    return CODE_MAP.get(exceptionCode, "Unknown exception code")

#-----------------------------------------------------------------------------------------------
# WORKER FUNCTIONS
#-----------------------------------------------------------------------------------------------
def performReadout(regGroups, args, client, resultSet):
    for regGroup in regGroups:
        if (args.verbose): print("Trying to get registers", regGroup, "...")
        regStrings = regGroup.split("-")
        start  = 0
        length = 1
        if len(regStrings)==1:
            start = stringToValidAddress(regStrings[0])
        elif len(regStrings)==2:
            start = stringToValidAddress(regStrings[0])
            end   = stringToValidAddress(regStrings[1])
            if (end == start):
                length = 1
            elif (end > start):
                length = end - start + 1
            else:
                length = start - end + 1
                start  = end
            if (length > 125): 
                if (args.verbose): print("Requested readout of more than 125 registers, which "
                                         "Modbus does not support", regGroup, "...")
                raise ValueError
        else:
            if (args.verbose): print("Unable to parse register group! Will skip this one")
            continue

        # let the working client actually read    
        results = client.readHoldingRegs(startAddress=start, length=length, verbose=args.verbose)

        if (len(results) != length): raise UserWarning
        resultSet.append(ReadoutResultSet(start, length, results))
        if (args.verbose): print("Raw data:", results)

def performWrite(regGroups, args, client):
    for regGroup in regGroups:
        if (args.verbose): print("\nTrying to write registers", regGroup, "...")
        regStrings = regGroup.split("=")
        if len(regStrings)==2:
            addr = stringToValidAddress(regStrings[0])
            val  = stringToValidValue(regStrings[1])
        else:
            if (args.verbose): print("Unable to parse register group! Will skip this one")
            continue
        
        # let the working client actually write
        results = client.writeSingleReg(address=addr, value=val)
        
        if (args.verbose): print("Raw response:", results)

#-----------------------------------------------------------------------------------------------
# RESULT PRINTOUT FUNCTIONS
#-----------------------------------------------------------------------------------------------
def printAsTable(resultSet):
    print('---------------------------------------')
    print('Reg.  |   Hex  | int16  | uint16 | char')
    print('---------------------------------------')
    for readoutResult in resultSet:
        for idx, val in enumerate(readoutResult.results):
            print('{:>5} | 0x{:0>4x} | {:>6} | {:>6} | {:>1}'.format(
                readoutResult.start+idx, val, val, uint16ToInt16(val), uint16ToDoubleChar(val)))

def printAsPlain(resultSet):
    first = True
    for readoutResult in resultSet:
        for idx, val in enumerate(readoutResult.results):
            if first: 
                first = False
            else:
                print(',', end='')
            if(args.datatype == "uint") :  print("{}".format(uint16ToInt16(val)), end='')
            elif(args.datatype == "chr") : print("{}".format(chr(val)), end='')
            elif(args.datatype == "hex") : print("0x{:0>4x}".format(val), end='')
            else:                          print("{}".format(val), end='')
    print('') # closing newline character


################################################################################################
# CLASSES
################################################################################################

# client class doing the actual Modbus communication
class client:
    def __init__(self, host='localhost', port=502, unitid=1, timeout=2):
        self.host          = host
        self.port          = port
        self.unitid        = unitid
        self.transactionID = 0
        self.sock          = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))

    def readHoldingRegs(self, startAddress, length, verbose):
        FUNCTION_CODE = 3
        MSG_LENGTH    = 6

        # calculate bytes required for construction of request
        startAddHi = startAddress >> 8
        startAddLo = startAddress & 0x00FF
        lengthHi   = length >> 8
        lengthLo   = length & 0x00FF
        if self.transactionID < 255: 
            self.transactionID = self.transactionID + 1
        else: self.transactionID = 1

        # construct and send request
        request = array('B', [0, self.transactionID, 0, 0, 0, MSG_LENGTH,         # "header"
                              self.unitid, FUNCTION_CODE,                         # "message"
                              startAddHi, startAddLo, lengthHi, lengthLo]) 
        self.sock.send(request)

        # get response
        bytesExpected = length * 2
        rcvBuffer     = array('B', [0] * (bytesExpected + 9))                # header length: 9
        self.sock.recv_into(rcvBuffer)

        # process response
        returnedTransactionId = rcvBuffer[1]
        returnedFunctionCode  = rcvBuffer[7]
        nrOfBytesTransmitted  = rcvBuffer[8]
        if(verbose): 
            if(returnedFunctionCode == 128 + FUNCTION_CODE): 
                exceptionCode = rcvBuffer[8]
                print("Error: Modbus exception occured:", modbusExceptionCodeToString(exceptionCode))
            elif(returnedFunctionCode  != FUNCTION_CODE): 
                print("Error: Response refers to unexpected function code!")
            elif(nrOfBytesTransmitted  != bytesExpected): 
                print("Error: Response contains unexpected number of bytes!")
                
        if(returnedTransactionId != self.transactionID or 
           returnedFunctionCode  != FUNCTION_CODE or
           nrOfBytesTransmitted  != bytesExpected): 
            return []
        else:
            if(verbose): print("Response looks fine!")
            return unpack('>' + 'H' * length, rcvBuffer[9:(9 + bytesExpected)])
        
    def writeSingleReg(self, address, value):
        FUNCTION_CODE = 6
        MSG_LENGTH    = 6

        # calculate bytes required for construction of request
        addHi = address >> 8
        addLo = address & 0x00FF
        value = b'' + pack('>H', int(value))
        if self.transactionID < 255: 
            self.transactionID = self.transactionID + 1
        else: self.transactionID = 1

        # construct and send request
        request = array('B', [0, self.transactionID, 0, 0, 0, MSG_LENGTH,         # header
                              self.unitid, FUNCTION_CODE, addHi, addLo])          # message
        request.extend(value)
        self.sock.send(request)

        # get response
        buffer = array('B', [0] * 20)
        self.sock.recv_into(buffer)
        # \todo: error handling
        return(buffer)

class ReadoutResultSet:
    def __init__(self, start, length, results):
        self.start   = start
        self.length  = length
        self.results = results


################################################################################################
## THE ACTUAL SCRIPT
################################################################################################

#-----------------------------------------------------------------------------------------------
# COMMAND LINE PARSING 
#-----------------------------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Perform a read or write operation on some Modbus TCP server", 
                                 epilog="Examples:\n"
                                 "tinymb.py read 1-10,42-99,101,40123     # read all these registers\n"
                                 "tinymb.py write 17=42                   # write 42 to reg. 17\n"
                                 "tinymb.py write 17=0x42,42=17           # write 0x42 to reg. 17 and 17 to reg. 42\n",
                                 formatter_class=argparse.RawDescriptionHelpFormatter
                                 )
parser.add_argument("-v", "--verbose",  help="increase output verbosity",    
                                        action="store_true")
parser.add_argument("-s", "--server",   type=str, help="Modbus server to connect to",  
                                        default="localhost")
parser.add_argument("-u", "--unitid",   type=int, help="Modbus unit ID to connect to", 
                                        default=1)
parser.add_argument("-o", "--output",   type=str, help="Output format: just the 'plain' results or a nice 'table'",               
                                        default="table", choices=["table", "plain"])
parser.add_argument("-d", "--datatype", type=str, help="Datatype to interpret results as (ignored for output formats other than 'plain')", 
                                        choices=["int", "uint", "chr", "hex"])
parser.add_argument("-t", "--timeout",  type=int, help="Timeout in seconds for each single Modbus query to complete (0: no timeout)", 
                                        default=5, choices=range(0, 61))
parser.add_argument("operation",        type=str, help="operation to perform",         
                                        choices=["read", "write"])
parser.add_argument("registers",        type=str, help="group of registers[=values] to read/write from/to; grouping is only supported for read-operations. See examples below.")

args = parser.parse_args()
regGroups = args.registers.split(",")


#-----------------------------------------------------------------------------------------------
# MODBUS CONNECTION ESTABLISHMENT 
#-----------------------------------------------------------------------------------------------
try:
    if (args.verbose): print("Will try to connect to unit {} on {}:502 ..."
                       .format(args.unitid, args.server))
    client = client(host=args.server, unitid=args.unitid, timeout=args.timeout)
    if (args.verbose): print("... connected!")
except ConnectionRefusedError:
    sys.exit("Could not connect to server! Please check connection details.")


#-----------------------------------------------------------------------------------------------
# MODBUS OPERATION 
#-----------------------------------------------------------------------------------------------
if (args.operation == "read"):
    resultSet = []
    try:
        performReadout(regGroups, args, client, resultSet)

    except ValueError:
        sys.exit("Invalid input! Probably invalid register definition. You might want to run with option '--verbose'.")
    except socket.timeout:
        sys.exit("Did not receive reply in due time! Maybe wrong unit ID? You might want to run with option '--verbose'.")
    except UserWarning: 
        sys.exit("Did not receive any results! Did you try to read non-supported registers? You might want to run with option '--verbose'.")

    if (args.verbose): print("Received {} sets of results".format(len(resultSet)))

    if (args.output == "table"):   printAsTable(resultSet)
    elif (args.output == "plain"): printAsPlain(resultSet)

elif (args.operation == "write"):
    try:
        performWrite(regGroups, args, client)

    except socket.timeout:
        sys.exit("Did not receive reply in due time! Maybe wrong unit ID? You might want to run with option '--verbose'.")
    except ValueError:
        print("Something went wrong while writing. You might want to run with option '--verbose'.")
