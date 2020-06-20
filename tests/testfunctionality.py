import src.handlers.telegram as telegram
import unittest

class TestFunctionality(unittest.TestCase):
    def testOverall(self):
        #  generate messages
        # send generated messages
        telegram.SendMessage()