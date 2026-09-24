import unittest
import sys
import os

# Ensure the demo_repo is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from calculator import add, subtract, multiply, divide, power, calculate_average


class TestCalculator(unittest.TestCase):

    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 1), 0)
        self.assertEqual(add(0, 0), 0)

    def test_subtract(self):
        self.assertEqual(subtract(10, 4), 6)
        self.assertEqual(subtract(2, 5), -3)

    def test_multiply(self):
        self.assertEqual(multiply(3, 7), 21)
        self.assertEqual(multiply(-2, 4), -8)

    def test_divide(self):
        self.assertEqual(divide(10, 2), 5.0)
        with self.assertRaises(ValueError):
            divide(10, 0)

    def test_power(self):
        self.assertEqual(power(2, 3), 8)
        self.assertEqual(power(5, 0), 1)

    def test_calculate_average(self):
        self.assertEqual(calculate_average([10, 20, 30]), 20.0)
        self.assertEqual(calculate_average([]), 0.0)


if __name__ == "__main__":
    unittest.main()
