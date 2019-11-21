import telegraminterface as Telegram
import time

from datetime import datetime
from multiprocessing import Manager, Process
from src.utils.dbhelper import DBHelper, Users
from textSimilarity import TextSimilarity

db = DBHelper()
users = Users()
textSimilarity  = TextSimilarity()

def updates(messageDict,similarityDict,parentTimes):
    lastUpdateID = 0
    while True:
        updates = Telegram.GetUpdates(lastUpdateID)
        if len(updates["result"]) > 0:
            lastUpdateID = Telegram.GetLastUpdateId(updates) + 1
            messageDict, similarityDict, parentTimes = handleUpdates(updates,messageDict,similarityDict,parentTimes)
            print("messagedict in updates: ", len(messageDict))
            print("similarityDict in updates: ", len(similarityDict))
            print("parentTimes in updates: ", len(parentTimes))

def sendSummary(messageDict,similarityDict,parentTimes):
    while True:
        for parent in parentTimes.keys():
            children = similarityDict[parent]
            timeofMessage = parentTimes[parent]
            timeSinceParentMessage = getTimeDifference(timeofMessage,datetime.now())
            if timeSinceParentMessage > 10:
                textSummary = getSummarisedText(parent,children,messageDict)
                if textSummary != "":
                    textSummary = '10s since parent message:\n\n{}\n\nshowing summary for {} similar messages:\n\n{}'.format(messageDict[parent], len(similarityDict[parent]), textSummary)
                    sendMessageToAllUsers(textSummary)
                del parentTimes[parent]
        print('\n\nsendSummary process, messageDict: ', len(messageDict))
        print("sendsummary process, similarityDict: ", len(similarityDict))
        print("sendSummary processs, parentTimes: ", len(parentTimes))
        time.sleep(1)

def handleUpdates(updates,messageDict,similarityDict,parentTimes):
    for update in updates["result"]:
        try:
            text, chat, messageID = getTelegramMessage(update)
        except:
            text, chat, messageID = getTelegramChannelPost(update)
        if text == '/deleteall':
            db.delete_all()
            messageDict = clearDictProxy(messageDict) # for thread manager to detect delete changes
            similarityDict = clearDictProxy(similarityDict) # for thread manager to detect delete changes
            parentTimes = clearDictProxy(parentTimes) # for thread manager to detect delete changes
            Telegram.SendMessage("All items have been deleted from the database", chat,)
        elif text == "/start":
            Telegram.SendMessage('Welcome to the FishNet bot, where messages are in abundance and the net catches them all\n\nPlease enter a password with the prefix / to gain access', chat)
        elif text == "/itsabouttime69":
            Telegram.SendMessage('Well you got it right... guess I should start sending you messages now', chat)
            users.add_user(chat)
            Telegram.SendAnimation(chat)
        else:
            timeOfProcessing = datetime.now()
            db.add_item(text, chat,messageID, datetime.now())
            messageDict = db.updateDict(messageDict)
            messageCount = len(messageDict) 

            if messageCount > 1:
                similarityDict = compareMessages(messageDict,similarityDict)
                if isMessageSendAllowed(messageID,similarityDict):
                    sendMessageToAllUsers(messageDict[messageID])
                if messageCount > 2:
                    if messageID in similarityDict.keys():
                        parentTimes = updateParentTimes(parentTimes,[messageID],timeOfProcessing)
                    similarityDict, parentTimes = hasParentSummaryBeenSent(messageID,similarityDict,parentTimes,timeOfProcessing)   
                else:
                    parentTimes = updateParentTimes(parentTimes,similarityDict.keys(),timeOfProcessing)
            elif messageCount == 1:
                sendMessageToAllUsers(messageDict[messageID])
    return messageDict, similarityDict, parentTimes

def getTelegramMessage(update):
    text = update["message"]["text"]
    chat = update["message"]["chat"]["id"]
    messageID = update["message"]["message_id"]
    return text, chat, messageID

def getTelegramChannelPost(update):
    text = update["channel_post"]["text"]
    chat = update["channel_post"]["chat"]["id"]
    messageID = update["channel_post"]["message_id"]
    return text, chat, messageID

def clearDictProxy(dictionary):
    temp = dictionary
    temp.clear()
    dictionary = temp
    return dictionary

def compareMessages(messageDict,similarityDict):
    if isEmpty(similarityDict): # if this is the first comparison being made
        text, keys = getFirstComparisonTextAndKeys(messageDict)
        similarity = textSimilarity.GetSingleSimilarity(text)
        if similarity > 0.7:
            similarityDict[keys[0]] = [keys[1]]
        else:
            similarityDict[keys[0]] = []
            similarityDict[keys[1]] = []
    else:
        parent, child = existingComparisons(similarityDict)
        tempParent, tempKey = messagesToCompare(messageDict,parent,child)
        similarityDict = addToSimilarityDict(tempParent,tempKey,similarityDict)
    return similarityDict

def isEmpty(anyStructure):
    if anyStructure:
        return False
    else:
        return True

def getFirstComparisonTextAndKeys(messageDict):
    text = []
    keys = [list(messageDict.keys())[0]]
    keys.append(list(messageDict.keys())[1])
    text.append(messageDict[keys[0]])
    text.append(messageDict[keys[1]])
    return text, keys

def updateParentTimes(parentTimes, keys, timeOfProcessing):
    for key in keys:
        parentTimes[key] = timeOfProcessing
    return parentTimes

def GetMaxKeyID(self, dictionary):
    maxID = 0
    for key in dictionary.keys():
        if key > maxID:
            maxID = key
    return maxID

def existingComparisons(similarityDict):
    parent = [p for p in similarityDict.keys()]
    child = getChild(similarityDict)
    return parent, child    

def getChild(similarityDict):
    values = [v for v in similarityDict.values()]
    child = []
    for sublist in values:
        for item in sublist:
            child.append(item)
    return child

def messagesToCompare(messageDict,parent,child):
    text = []
    keys = []
    i = 0
    for key in messageDict.keys():
        if key not in parent: # if key is in parent, then don't need to compare it to itself
            if key not in child: # compare to see if similar to any parents
                for p in parent:
                    text.clear()
                    text.append(messageDict[p]) 
                    text.append(messageDict[key])
                    similarity = textSimilarity.GetSingleSimilarity(text)
                    if similarity > 0.7:
                        keys.append(p)
                        keys.append(key)
                        return False, keys
                    tempParent = key
                    i += 1
    return tempParent, False

def addToSimilarityDict(tempParent, tempKey, similarityDict):
    tempDict = dict()
    tempDict = similarityDict
    if not tempParent: 
        tempDict[tempKey[0]] = [tempKey[1]] + tempDict[tempKey[0]]
    if not tempKey: 
        tempDict[tempParent] = []
    return tempDict

def isMessageSendAllowed(messageID, similarityDict):
    if isMessageAParentWithoutChildren(messageID,similarityDict):
        return True
    else: 
        return False

def isMessageAParentWithoutChildren(messageID, similarityDict):
    if messageID in similarityDict.keys():
        if isEmpty(similarityDict[messageID]):
            return True
        return False
    else:
        return False

def hasParentSummaryBeenSent(messageID, similarityDict, parentTimes, timeOfProcessing):
    parent = doesMessageIDHaveParent(messageID,similarityDict)
    if not parent:
        return similarityDict, parentTimes
    elif parent not in parentTimes.keys():
        similarityDict = setNewParent(parent, messageID, similarityDict)
        parentTimes[messageID] = timeOfProcessing
        return similarityDict, parentTimes
    return similarityDict, parentTimes
    
def doesMessageIDHaveParent(messageID,similarityDict):
    for parent in similarityDict.keys():
        if messageID in similarityDict[parent]:
            return parent
    return False

def setNewParent(oldKey,newKey,dictionary):
    dictionary[newKey] = removeDictValue(dictionary[oldKey], newKey) + [oldKey]
    del dictionary[oldKey]
    return dictionary

def removeDictValue(values, newKey):
    temp = []
    for messageID in values:
        if newKey != messageID:
            temp.append(messageID)
    return temp
        
def getTimeDifference(startMessage,endMessage):
    startMessage = datetime.strptime(str(startMessage), '%Y-%m-%d %H:%M:%S.%f')
    endMessage = datetime.strptime(str(endMessage), '%Y-%m-%d %H:%M:%S.%f')
    difference = endMessage - startMessage
    seconds = (difference.total_seconds())
    return seconds

def sendMessageToAllUsers(text):
    for user in users.get_users():
        Telegram.SendMessage(text,user)

def getSummarisedText(parent,children,messageDict):
    uniqueText = getUniqueText(parent,children,messageDict)
    uniqueText = concatenate(uniqueText)
    return uniqueText

def getUniqueText(parent,children,messageDict):
    uniqueText = []
    for child in children:
        text = [messageDict[parent],messageDict[child]]
        uniqueList = textSimilarity.GetSingleUniqueText(text)
        for unique in uniqueList:
            if unique not in uniqueText:
                uniqueText += [unique]
    return uniqueText

def concatenate(textArray):
    string = ""
    for text in textArray:
        string += text
        string += ", "
    string = string[:-2]
    return string


