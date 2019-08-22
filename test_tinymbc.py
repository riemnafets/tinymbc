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

if __name__ == '__main__':
    unittest.main()

