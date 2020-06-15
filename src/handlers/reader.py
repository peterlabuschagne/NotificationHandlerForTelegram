import time

from datetime import datetime
from multiprocessing import Manager, Process
from src.db import notifications, users
from src.handlers import telegram as Telegram
from src.handlers.textSimilarity import TextSimilarity

notifications = notifications.Notifications()
users = users.Users()
textSimilarity  = TextSimilarity()

def updates(messageDict,similarityDict,parentTimes,messagesToBlock):
    lastUpdateID = 0
    while True:
        try:
            updates = Telegram.GetUpdates(lastUpdateID)
            print("Last update request: ", datetime.now())
            if len(updates["result"]) > 0:
                lastUpdateID = Telegram.GetLastUpdateId(updates) + 1
                messageDict, similarityDict, parentTimes, messagesToBlock = handleUpdates(updates,messageDict,similarityDict,parentTimes,messagesToBlock)
                print("messagedict in updates: ", len(messageDict))
                print("similarityDict in updates: ", len(similarityDict))
                print("Summaries in updates: ", len(parentTimes))
        except Exception as e:
            print("GetUpdates exception, waiting 10s before retry")
            print("Exception: ", e)
            time.sleep(10)
            pass
        

def sendSummary(messageDict,similarityDict,parentTimes):
    secondsToWait = 360
    while True:
        for parent in parentTimes.keys():
            children = similarityDict[parent]
            timeofMessage = parentTimes[parent]
            timeSinceParentMessage = getTimeDifference(timeofMessage,datetime.now())
            if timeSinceParentMessage > secondsToWait:
                textSummary = getSummarisedText(parent,children,messageDict)
                if textSummary != "":
                    textSummary = '{}s since parent message:\n\n{}\n\nshowing summary for {} similar messages:\n\n{}'.format(secondsToWait,messageDict[parent], len(similarityDict[parent]), textSummary)
                    sendMessageToAllUsers(textSummary)
                del parentTimes[parent]
        time.sleep(1)

def handleUpdates(updates,messageDict,similarityDict,parentTimes,messagesToBlock):
    for update in updates["result"]:
        try:
            text, chat, messageID = getTelegramMessage(update)
        except:
            text, chat, messageID = getTelegramChannelPost(update)
        if text == '/deleteall':
            notifications.delete_all()
            messageDict = clearDictProxy(messageDict) # for thread manager to detect delete changes
            similarityDict = clearDictProxy(similarityDict) # for thread manager to detect delete changes
            parentTimes = clearDictProxy(parentTimes) # for thread manager to detect delete changes
            Telegram.SendMessage("All items have been deleted from the FishNet database", chat,)
        elif text == "/start":
            Telegram.SendMessage('Welcome to the FishNet bot, where messages are in abundance and the net catches them all\n\nPlease enter a password with the prefix / to gain access', chat)
        elif text == "/itsabouttime69":
            if str(chat) not in users.get_users():
                Telegram.SendMessage('Well you got it right... guess I should start sending you messages now', chat)
                users.addUser(chat)
                Telegram.SendAnimation(chat)
                print(users.get_users())
        elif text == "/running":
            Telegram.SendMessage('Yes, it is still running', chat)
        elif text == "/summary":
            summaryMessage = "sendSummary process, messageDict: {}, similarityDict: {}, Pending Summaries: {}".format(len(messageDict), len(similarityDict), len(parentTimes))
            Telegram.SendMessage(summaryMessage, chat)
        elif text == "/getSummary":
            for parent in parentTimes.keys():
                children = similarityDict[parent]
                textSummary = getSummarisedText(parent,children,messageDict)
                Telegram.SendMessage(textSummary,chat)
        elif text.startswith("/blocked"):
            message = text[8:]
            Telegram.SendMessage('You have blocked {}'.format(text), chat)
            messagesToBlock = blockMessage(message,similarityDict,messageDict,messagesToBlock)
            
        elif text.startswith("/"):
            Telegram.SendMessage('Unrecognized Command', chat)
            continue
        else:
            print(messageID)
            if True: 
                timeOfProcessing = datetime.now()
                notifications.add_item(text, chat,messageID, datetime.now())
                messageDict = notifications.updateDict(messageDict)
                messageCount = len(messageDict) 

                if messageCount > 1:
                    similarityDict = compareMessages(messageDict,similarityDict)
                    if isMessageSendAllowed(messageID,similarityDict,parentTimes,timeOfProcessing):
                        sendMessageToAllUsers(messageDict[messageID])
                    if messageCount > 2:
                        if messageID in similarityDict.keys():
                            parentTimes = updateParentTimes(parentTimes,[messageID],timeOfProcessing)
                        similarityDict, parentTimes = hasParentSummaryBeenSent(messageID,similarityDict,parentTimes,timeOfProcessing,text)
                    else:
                        parentTimes = updateParentTimes(parentTimes,similarityDict.keys(),timeOfProcessing)
                elif messageCount == 1:
                    sendMessageToAllUsers(messageDict[messageID])
    return messageDict, similarityDict, parentTimes, messagesToBlock

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
    if not tempParent: # == False
        tempDict[tempKey[0]] = [tempKey[1]] + tempDict[tempKey[0]]
    if not tempKey: # == False
        tempDict[tempParent] = []
    return tempDict

def isMessageSendAllowed(messageID, similarityDict,parentTimes,timeOfProcessing):
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

def hasParentSummaryBeenSent(messageID, similarityDict, parentTimes, timeOfProcessing, currentMessage):
    parent = doesMessageIDHaveParent(messageID,similarityDict)
    if not parent:
        return similarityDict, parentTimes
    elif parent not in parentTimes.keys():
        similarityDict = setNewParent(parent, messageID, similarityDict)
        parentTimes[messageID] = timeOfProcessing
        sendMessageToAllUsers(currentMessage)
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
    messageResponse = list()
    for user in users.get_users():
        messageResponse.append(Telegram.SendMessage(text,user))
    return messageResponse

def deleteMessageForAllUsers(messageIDs):
    i = 0
    for user in users.get_users():
        Telegram.DeleteMessage(messageIDs[i],user)
        i += 1

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

def populateSentMessageIDs(content):
    sentMessageIDs = list()
    try:
        for response in content:
            sentMessageIDs.append(response["result"]["message_id"])
    except:
        pass
    return sentMessageIDs

def blockMessage(message,similarityDict,messageDict,messagesToBlock):
    parent = findParent(message,similarityDict,messageDict)
    if parent != 0:
        temp = messagesToBlock
        temp.append(parent)
        messagesToBlock = temp
    return messagesToBlock


def findParent(message,similarityDict,messageDict):
    text = list()
    text.append(message)
    text.append(message)
    for key in similarityDict.keys():
        text[1] = messageDict[key]
        similarity = textSimilarity.GetSingleSimilarity(text)
        if similarity > 0.7:
            return key
    return 0
        