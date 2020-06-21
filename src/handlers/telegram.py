import config
import json
import requests
import urllib

TOKEN = config.Token
URL = "https://api.telegram.org/bot{}/".format(TOKEN)

def GetUrl(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content

def GetJsonFromUrl(url):
    content = GetUrl(url)
    js = json.loads(content)
    return js

def GetUpdates(offset=None):
    url = URL + "getUpdates?timeout=100"
    if offset:
        url += "&offset={}".format(offset)
    js = GetJsonFromUrl(url)
    return js

def GetLastUpdateId(updates):
    updateIDs = []
    for update in updates["result"]:
        updateIDs.append(int(update["update_id"]))
    return max(updateIDs)

def SendMessage(text, chatID, replyMarkup=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}".format(text, chatID)
    if replyMarkup:
        url += "&reply_markup={}".format(replyMarkup)
    return GetJsonFromUrl(url)

def SendAnimation(chatID):
    url = URL + "sendAnimation?chat_id={}&animation=https://media.giphy.com/media/YVNiYNd87ddxgi8vnm/giphy.gif".format(chatID)
    GetUrl(url)

def DeleteMessage(messageID, chatID):
    url = URL + "deleteMessage?chat_id={}&message_id={}".format(chatID,messageID)
    return GetJsonFromUrl(url)

def GetMessage(update):
    text = update["message"]["text"]
    chat = update["message"]["chat"]["id"]
    messageID = update["message"]["message_id"]
    return text, chat, messageID

def GetChannelPost(update):
    text = update["channel_post"]["text"]
    chat = update["channel_post"]["chat"]["id"]
    messageID = update["channel_post"]["message_id"]
    return text, chat, messageID

def MessageDetails(update):
    try:
        return GetMessage(update)
    except:
        return GetChannelPost(update)

def IsCommand(text):
    return text.startswith('/')

def populateSentMessageIDs(content):
    sentMessageIDs = list()
    try:
        for response in content:
            sentMessageIDs.append(response["result"]["message_id"])
    except:
        pass
    return sentMessageIDs

