#!/usr/bin/env python3

"""
This scripts provides minimalistic modbus TCP command line client with minimal dependencies.
"""

################################################################################################
## LINTING
################################################################################################
# pylint: disable=redefined-outer-name


################################################################################################
## IMPORTS
################################################################################################
import sys
import argparse
import socket
from array import array
from struct import unpack, pack


################################################################################################
## CONSTANTS
################################################################################################

MODBUS_EXCEPTION_CODES = {
    1: "Illegal Function Code",
    2: "Illegal Data Address",
    3: "Illegal Data Value",
    4: "Server Failure",
    5: "Acknowledge",
    6: "Server Busy",
    10: "Gateway Problem (0x0A)",
    11: "Gateway Problem (0x0B)"
}

################################################################################################
# GLOBAL FUNCTIONS
################################################################################################

#-----------------------------------------------------------------------------------------------
# CONVERSION FUNCTIONS
#-----------------------------------------------------------------------------------------------
def uint16_to_int16(ui):
    """Converts an unsigned 16bit integer to a signed 16bit integer."""
    if ui < 0 or ui >= 65536 or not isinstance(ui, int):
        raise ValueError
    if ui > 32767:
        return ui - 65536
    else:
        return ui

def int16_to_uint16(i):
    """Converts a signed 16bit integer to an unsigned 16bit integer."""
    if i < -32768 or i > 32767:
        raise ValueError
    if i < 0:
        return i + 65536
    else:
        return i

def hex_byte_to_chr(byte):
    """Converts a hex byte to a character."""
    nr = int(byte, 16)
    # return empty string if character is not printable
    if nr >= 0 and nr < 32:
        return ""
    elif nr < 256:
        return chr(nr)
    else:
        raise ValueError

def uint16_to_double_char(val):
    """Converts an unsigned 16bit integer to a string of two characters."""
    if val > 65535 or val < 0:
        raise ValueError
    hexstr = hex(val)
    hexstr = hexstr[2:].zfill(4)  # remove '0x' and pad with zeros to ensure 4 chars = 2 bytes
    chr1 = hex_byte_to_chr(hexstr[:2])
    chr2 = hex_byte_to_chr(hexstr[2:])
    return chr1 + " " + chr2

def string_to_valid_address(addr_str):
    """Converts a string to a valid Modbus address."""
    addr = int(addr_str)
    if addr > 65535 or addr < 0:
        raise ValueError
    return addr

def string_to_valid_value(val_str):
    """Converts a string to a valid Modbus value."""
    if val_str[:2] == "0x":
        val = int(val_str, 16)
    else:
        val = int(val_str)
    if val < 0:
        val = uint16_to_int16(val)
    if val < 0 or val > 65535:
        raise ValueError
    return val

def modbus_exception_code_to_string(exception_code):
    """Converts a Modbus exception code to a human readable string."""

    return MODBUS_EXCEPTION_CODES.get(exception_code, "Unknown exception code")

#-----------------------------------------------------------------------------------------------
# WORKER FUNCTIONS
#-----------------------------------------------------------------------------------------------
def perform_readout(reg_groups, args, client, result_set):
    """Reads out the registers specified in reg_groups and stores the results in result_set."""
    for reg_group in reg_groups:
        if args.verbose:
            print("Trying to get registers", reg_group, "...")
        reg_strings = reg_group.split("-")
        start  = 0
        length = 1
        if len(reg_strings)==1:
            start = string_to_valid_address(reg_strings[0])
        elif len(reg_strings)==2:
            start = string_to_valid_address(reg_strings[0])
            end   = string_to_valid_address(reg_strings[1])
            if end == start:
                length = 1
            elif end > start:
                length = end - start + 1
            else:
                length = start - end + 1
                start  = end
            if length > 125:
                print_verbose(args, f"""Requested readout of more than 125 registers,
                              which Modbus does not support {reg_group}...""")
                raise ValueError
        else:
            print_verbose(args, "Unable to parse register group! Will skip this one")
            continue

        # let the working client actually read
        results = client.read_holding_regs(start_address=start, length=length, verbose=args.verbose)

        if len(results) != length:
            raise UserWarning
        result_set.append(ReadoutResultSet(start, length, results))
        print_verbose(args, f"Raw data: {results}")

def perform_write(reg_groups, args, client):
    """Writes the registers specified in reg_groups."""
    for reg_group in reg_groups:
        print_verbose(args, f"\nTrying to write registers {reg_group} ...")
        reg_strings = reg_group.split("=")
        if len(reg_strings)==2:
            addr = string_to_valid_address(reg_strings[0])
            reg_vals = reg_strings[1].split(";")
            vals = []
            for reg_val in reg_vals:
                vals.append(string_to_valid_value(reg_val))
        else:
            print_verbose(args, "Unable to parse register group! Will skip this one")
            continue

        # let the working client actually write
        results = []
        if len(vals) == 1:
            results = client.write_single_reg(address=addr, value=vals[0])
        elif len(vals) > 1:
            results = client.write_multi_regs(address=addr, values=vals)
        elif args.verbose:
            print("Found no vals to transmit! Will skip this one")
            continue

        print_verbose(args, f"Raw response: {results}")

def print_verbose(args, to_print):
    """Prints if args.verbose is set."""
    if args.verbose:
        print(to_print)

#-----------------------------------------------------------------------------------------------
# RESULT PRINTOUT FUNCTIONS
#-----------------------------------------------------------------------------------------------
def print_as_table(result_set):
    """Prints the results in a nice table."""
    print('---------------------------------------')
    print('Reg.  |   Hex  | int16  | uint16 | char')
    print('---------------------------------------')
    for readout_result in result_set:
        for idx, val in enumerate(readout_result.results):
            print('{:>5} | 0x{:0>4x} | {:>6} | {:>6} | {:>1}'.format(
              readout_result.start+idx, val, val, uint16_to_int16(val), uint16_to_double_char(val)))

def print_as_plain(args, result_set):
    """Prints the results in a plain format."""
    first = True
    for readout_result in result_set:
        for val in enumerate(readout_result.results):
            if first:
                first = False
            else:
                print(',', end='')
            if args.datatype == "uint":
                print(f"{uint16_to_int16(val)}", end='')
            elif args.datatype == "chr":
                print(f"{chr(val)}", end='')
            elif args.datatype == "hex":
                print(f"0x{val:0>4x}", end='')
            else:
                print(f"{val}", end='')
    print('') # closing newline character


################################################################################################
# CLASSES
################################################################################################

# client class doing the actual Modbus communication
class ModbusClient:
    """A simple Modbus TCP client."""
    def __init__(self, host='localhost', port=502, unitid=1, timeout=2):
        self.host           = host
        self.port           = port
        self.unitid         = unitid
        self.transaction_id = 0
        self.sock           = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))

    def read_holding_regs(self, start_address, length, verbose):
        """Reads out the registers specified by start_address and length."""
        FUNCTION_CODE = 3
        MSG_LENGTH    = 6

        # calculate bytes required for construction of request
        start_add_hi = start_address >> 8
        start_add_lo = start_address & 0x00FF
        length_hi   = length >> 8
        length_lo   = length & 0x00FF
        if self.transaction_id < 255:
            self.transaction_id = self.transaction_id + 1
        else: self.transaction_id = 1

        # construct and send request
        request = array('B', [0, self.transaction_id, 0, 0, 0, MSG_LENGTH,         # "header"
                              self.unitid, FUNCTION_CODE,                          # "message"
                              start_add_hi, start_add_lo, length_hi, length_lo])
        self.sock.send(request)

        # get response
        bytes_expected = length * 2
        rcv_buffer     = array('B', [0] * (bytes_expected + 9))                # header length: 9
        self.sock.recv_into(rcv_buffer)

        # process response
        returned_transaction_id = rcv_buffer[1]
        returned_function_ode  = rcv_buffer[7]
        nr_of_bytes_transmitted  = rcv_buffer[8]
        if verbose:
            if returned_function_ode == 128 + FUNCTION_CODE:
                exception_code = rcv_buffer[8]
                print("Error: Modbus exception occured:",
                      modbus_exception_code_to_string(exception_code))
            elif returned_function_ode  != FUNCTION_CODE:
                print("Error: Response refers to unexpected function code!")
            elif nr_of_bytes_transmitted  != bytes_expected:
                print("Error: Response contains unexpected number of bytes!")

        if (returned_transaction_id != self.transaction_id or
           returned_function_ode  != FUNCTION_CODE or
           nr_of_bytes_transmitted  != bytes_expected):
            return []
        else:
            if verbose:
                print("Response looks fine!")
            return unpack('>' + 'H' * length, rcv_buffer[9:(9 + bytes_expected)])

    def write_single_reg(self, address, value):
        """Writes a single register specified by address with value."""
        FUNCTION_CODE = 6
        MSG_LENGTH    = 6

        # calculate bytes required for construction of request
        add_hi = address >> 8
        add_lo = address & 0x00FF
        value = b'' + pack('>H', int(value))
        if self.transaction_id < 255:
            self.transaction_id = self.transaction_id + 1
        else: self.transaction_id = 1

        # construct and send request
        request = array('B', [0, self.transaction_id, 0, 0, 0, MSG_LENGTH,         # header
                              self.unitid, FUNCTION_CODE, add_hi, add_lo])          # message
        request.extend(value)                                                     # payload
        self.sock.send(request)

        # get response
        buffer = array('B', [0] * 20)
        self.sock.recv_into(buffer)
        # \todo: error handling
        return buffer

    def write_multi_regs(self, address, values):
        """Writes multiple registers specified by address with values."""
        FUNCTION_CODE = 16

        # calculate bytes required for construction of request
        add_hi = address >> 8
        add_lo = address & 0x00FF

        payload = b''
        for value in values:
            payload = payload + pack('>H', int(value))

        nr_of_regs = int(len(payload) / 2)                      # nr of 16bit registers to write
        len_hi = nr_of_regs >> 8
        len_lo = nr_of_regs & 0x00FF
        pl_length = len(payload)                                # nr of bytes to write
        msg_length = 7 + pl_length

        if self.transaction_id < 255:
            self.transaction_id = self.transaction_id + 1
        else: self.transaction_id = 1

        # construct and send request
        request = array('B', [0, self.transaction_id, 0, 0, 0, msg_length,                # header
                 self.unitid, FUNCTION_CODE, add_hi, add_lo, len_hi, len_lo, pl_length])  # msg
        request.extend(payload)                                                           # payload
        self.sock.send(request)

        # get response
        buffer = array('B', [0] * 20)
        self.sock.recv_into(buffer)
        # \todo: error handling
        return buffer


class ReadoutResultSet:
    """A set of results from a readout operation."""
    def __init__(self, start, length, results):
        self.start   = start
        self.length  = length
        self.results = results


################################################################################################
## THE ACTUAL SCRIPT
################################################################################################

if __name__ == '__main__':
    #-----------------------------------------------------------------------------------------------
    # COMMAND LINE PARSING
    #-----------------------------------------------------------------------------------------------
    # pylint: disable=C0301
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
    # pylint: enable=C0301

    args = parser.parse_args()
    regGroups = args.registers.split(",")

    #-----------------------------------------------------------------------------------------------
    # MODBUS CONNECTION ESTABLISHMENT
    #-----------------------------------------------------------------------------------------------
    try:
        print_verbose(args, f"Will try to connect to unit {args.unitid} on {args.server}:502 ...")
        mb_client = ModbusClient(host=args.server, unitid=args.unitid, timeout=args.timeout)
        print_verbose(args, "... connected!")
    except ConnectionRefusedError:
        sys.exit("Could not connect to server! Please check connection details.")

    #-----------------------------------------------------------------------------------------------
    # MODBUS OPERATION
    #-----------------------------------------------------------------------------------------------
    if args.operation == "read":
        result_set: list[ReadoutResultSet] = []
        try:
            perform_readout(regGroups, args, mb_client, result_set)

        except ValueError:
            sys.exit("Invalid input! Probably invalid register definition. "
                     "You might want to run with option '--verbose'.")
        except socket.timeout:
            sys.exit("Did not receive reply in due time! Maybe wrong unit ID? "
                     "You might want to run with option '--verbose'.")
        except UserWarning:
            sys.exit("Did not receive any results! Did you try to read non-supported registers?"
                     "You might want to run with option '--verbose'.")

        print_verbose(args, f"Received {len(result_set)} sets of results")

        if args.output == "table":
            print_as_table(result_set)
        elif args.output == "plain":
            print_as_plain(args, result_set)


    elif args.operation == "write":
        try:
            perform_write(regGroups, args, mb_client)

        except socket.timeout:
            sys.exit("Did not receive reply in due time! Maybe wrong unit ID? "
                     "You might want to run with option '--verbose'.")
        except ValueError:
            print("Something went wrong while writing. "
                  "You might want to run with option '--verbose'.")
