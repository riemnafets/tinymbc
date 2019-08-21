# tinymbc - The tiny Modbus TCP client

tinymbc aims to be for Modbus TCP what curl is for HTTP: an ergonomic, non-interactive command line interface to the underlying protocol for easy manual or scripted usage.

## Usage

```
tinymbc.py [-h] [-v] [-s SERVER] [-u UNITID] [-o {table,plain}]
                  [-d {int,uint,chr,hex}]
                  [-t {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60}]
                  {read,write} registers

Perform a read or write operation on some Modbus TCP server

positional arguments:
  {read,write}          operation to perform ('write' is not implemented yet)
  registers             group of registers[=values] to read/write from/to;
                        grouping is only supported for read-operations. See
                        examples below.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         increase output verbosity
  -s SERVER, --server SERVER
                        Modbus server to connect to
  -u UNITID, --unitid UNITID
                        Modbus unit ID to connect to
  -o {table,plain}, --output {table,plain}
                        Output format: just the 'plain' results or a nice
                        'table'
  -d {int,uint,chr,hex}, --datatype {int,uint,chr,hex}
                        Datatype to interpret results as (ignored for output
                        formats other than 'plain')
  -t {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60}, --timeout {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60}
                        Timeout in seconds for each single Modbus query to
                        complete (0: no timeout)

Examples:
tinymb.py read 1-10,42-99,101,40123     # read all these registers
tinymb.py write 17=42                   # write 42 to reg. 17
tinymb.py write 17=0x42,42=17           # write 0x42 to reg. 17 and 17 to reg. 42
```

## Installation

No need to install anything. Just run the core script tinymbc.py or put it somewhere in your search path for easier access.


## Limitations

Currently, only holding registers readout (Modbus function code 3) and writing of single holding registers (Modbus function code 6) are supported. 

I do not have any plans to add the usage of coil registers or the more archaic Modbus types like Modbus RTU.
