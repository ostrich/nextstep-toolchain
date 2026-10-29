"""Ensure incomplete or contradictory guest logs cannot look like a clean run."""
import unittest
from finish import parse_guest


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.good = ('API BEGIN\nAPI RESULT native-a exit 0 signal 0\n'
                     'API RESULT compat-a exit 1 signal 0\nAPI END 2 tests 1 failures\n')
        self.expected = {'native-a', 'compat-a'}

    def test_complete(self):
        self.assertEqual(len(parse_guest(self.good, self.expected)), 2)

    def test_missing_result(self):
        with self.assertRaises(ValueError):
            parse_guest(self.good.replace('API RESULT compat-a exit 1 signal 0\n', ''), self.expected)

    def test_duplicate(self):
        with self.assertRaises(ValueError):
            parse_guest(self.good.replace('compat-a', 'native-a'), self.expected)

    def test_bad_count(self):
        with self.assertRaises(ValueError):
            parse_guest(self.good.replace('1 failures', '0 failures'), self.expected)

    def test_inconsistent_signal(self):
        with self.assertRaises(ValueError):
            parse_guest(self.good.replace('exit 1 signal 0', 'exit 0 signal 10'), self.expected)

    def test_signalled_child(self):
        self.assertEqual(len(parse_guest(self.good.replace('exit 1 signal 0', 'exit -1 signal 10'), self.expected)), 2)

    def test_truncated(self):
        with self.assertRaises(ValueError):
            parse_guest(self.good.split('API END')[0], self.expected)


if __name__ == '__main__':
    unittest.main()
