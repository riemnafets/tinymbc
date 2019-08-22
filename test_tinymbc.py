import unittest
import tinymbc

class TestConversionMethods(unittest.TestCase):

    def test_uint16ToInt16(self):
        self.assertEqual(tinymbc.uint16ToInt16(0),      0)
        self.assertEqual(tinymbc.uint16ToInt16(1234),   1234)
        self.assertEqual(tinymbc.uint16ToInt16(65535), -1)
        self.assertEqual(tinymbc.uint16ToInt16(64302), -1234)
        self.assertRaises(ValueError, tinymbc.uint16ToInt16, 65536)
        self.assertRaises(ValueError, tinymbc.uint16ToInt16, -1)
        self.assertRaises(ValueError, tinymbc.uint16ToInt16, 1.5)

    def test_int16ToUint16(self):
        self.assertEqual(tinymbc.int16ToUint16(0),     0)
        self.assertEqual(tinymbc.int16ToUint16(1000),  1000)
        self.assertEqual(tinymbc.int16ToUint16(-1000), 64536)
        self.assertRaises(ValueError, tinymbc.int16ToUint16, -32769)
        self.assertRaises(ValueError, tinymbc.int16ToUint16, 32768)

    def test_modbusExceptionCodeToString(self):
        self.assertEqual(tinymbc.modbusExceptionCodeToString(0), "Unknown exception code")
        self.assertEqual(tinymbc.modbusExceptionCodeToString(-1), "Unknown exception code")
        self.assertEqual(tinymbc.modbusExceptionCodeToString(1234), "Unknown exception code")
        self.assertEqual(tinymbc.modbusExceptionCodeToString(1), "Illegal Function Code")
        self.assertEqual(tinymbc.modbusExceptionCodeToString(2), "Illegal Data Address")
        self.assertEqual(tinymbc.modbusExceptionCodeToString(3), "Illegal Data Value")
        self.assertEqual(tinymbc.modbusExceptionCodeToString(4), "Server Failure")
        self.assertEqual(tinymbc.modbusExceptionCodeToString(5), "Acknowledge")
        self.assertEqual(tinymbc.modbusExceptionCodeToString(6), "Server Busy")
        self.assertEqual(tinymbc.modbusExceptionCodeToString(10), "Gateway Problem (0x0A)")
        self.assertEqual(tinymbc.modbusExceptionCodeToString(11), "Gateway Problem (0x0B)")

if __name__ == '__main__':
    unittest.main()

