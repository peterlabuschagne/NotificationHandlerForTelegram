import json
import requests
import urllib

TOKEN = "<botToken>"
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
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chatID)
    if replyMarkup:
        url += "&reply_markup={}".format(replyMarkup)
    GetUrl(url)

def SendAnimation(chatID):
    url = URL + "sendAnimation?chat_id={}&animation=https://media.giphy.com/media/YVNiYNd87ddxgi8vnm/giphy.gif".format(chatID)
    GetUrl(url)