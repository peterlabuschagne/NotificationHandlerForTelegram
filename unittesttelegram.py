import json
import requests
import time
import urllib

TOKEN = "<botToken>"
URL = "https://api.telegram.org/bot{}/".format(TOKEN)

def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content

def sendMessage(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?chat_id={}&text={}".format(chat_id, text)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    print(get_url(url))

def main():
    chatID = '<chatID>'
    messages = ["this is my first message", "this is my second message", "this is my third message"]
    for text in messages:
        sendMessage(text,chatID)
        print("sending Text: ", text)
        time.sleep(0.5)
if __name__ == '__main__':
    main()