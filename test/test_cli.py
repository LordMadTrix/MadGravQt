import sys
import unittest

state = 0


class TestCommandLineInterface(unittest.TestCase):
    def test_cli(self):
        from madgrav import main

        sys.argv = "madgrav -Zpe quit".split(" ")
        main.run()
