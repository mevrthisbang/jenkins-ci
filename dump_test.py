import unittest
from dump_function import add

class TestSnippet(unittest.TestCase):

    def test_add_function_set_1(self):

        print(f"Testing function - add Set 1")

        data_list = [[1, 1, 2], [6, 6, 12], [15, 20, 35]]

        for data in data_list:
            result = add(data[0], data[1])

            self.assertEqual(result, data[2])

            print(f"Test data - {data}")

    def test_add_function_set_2(self):
        print(f"Testing function - add Set 2")
        data_list = [[75, 17, 92], [645, 6, 651], [432, 2343, 2775]]                                                                                                 301]]

        for data in data_list:
            result = add(data[0], data[1])

            self.assertEqual(result, data[2])

            print(f"Test data - {data}")


if __name__ == "__main__":
    unittest.main(verbosity=2)