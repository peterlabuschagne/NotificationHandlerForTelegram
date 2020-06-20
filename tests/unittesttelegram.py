import config
import json
import requests
import time
import urllib
import unittest

import src.handlers.telegram as telegram

class testTelegram(unittest.TestCase):
    def testSendMessage(self):
        users = config.Users
        messages = ["this is my first message", "this is my second message", "this is my third message"]
        for text in messages:
            for chatID in users:
                telegram.SendMessage(text,chatID)
                print("sending Text: ", text)
                time.sleep(0.5)
