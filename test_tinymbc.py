import unittest
import tinymbc

class TestConversionMethods(unittest.TestCase):

    def test_uint16ToInt16(self):
        self.assertEqual(tinymbc.uint16_to_int16(0),      0)
        self.assertEqual(tinymbc.uint16_to_int16(1234),   1234)
        self.assertEqual(tinymbc.uint16_to_int16(65535), -1)
        self.assertEqual(tinymbc.uint16_to_int16(64302), -1234)
        self.assertRaises(ValueError, tinymbc.uint16_to_int16, 65536)
        self.assertRaises(ValueError, tinymbc.uint16_to_int16, -1)
        self.assertRaises(ValueError, tinymbc.uint16_to_int16, 1.5)

    def test_int16ToUint16(self):
        self.assertEqual(tinymbc.int16_to_uint16(0),     0)
        self.assertEqual(tinymbc.int16_to_uint16(1000),  1000)
        self.assertEqual(tinymbc.int16_to_uint16(-1000), 64536)
        self.assertRaises(ValueError, tinymbc.int16_to_uint16, -32769)
        self.assertRaises(ValueError, tinymbc.int16_to_uint16, 32768)

    def test_modbusExceptionCodeToString(self):
        self.assertEqual(tinymbc.modbus_exception_code_to_string(0), "Unknown exception code")
        self.assertEqual(tinymbc.modbus_exception_code_to_string(-1), "Unknown exception code")
        self.assertEqual(tinymbc.modbus_exception_code_to_string(1234), "Unknown exception code")
        self.assertEqual(tinymbc.modbus_exception_code_to_string(1), "Illegal Function Code")
        self.assertEqual(tinymbc.modbus_exception_code_to_string(2), "Illegal Data Address")
        self.assertEqual(tinymbc.modbus_exception_code_to_string(3), "Illegal Data Value")
        self.assertEqual(tinymbc.modbus_exception_code_to_string(4), "Server Failure")
        self.assertEqual(tinymbc.modbus_exception_code_to_string(5), "Acknowledge")
        self.assertEqual(tinymbc.modbus_exception_code_to_string(6), "Server Busy")
        self.assertEqual(tinymbc.modbus_exception_code_to_string(10), "Gateway Problem (0x0A)")
        self.assertEqual(tinymbc.modbus_exception_code_to_string(11), "Gateway Problem (0x0B)")

if __name__ == '__main__':
    unittest.main()

