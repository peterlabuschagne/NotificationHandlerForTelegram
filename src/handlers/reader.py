import config
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
            print("Last update request: ", datetime.now()) # make this a command that can be queried by telegram
            if len(updates["result"]) > 0:
                lastUpdateID = Telegram.GetLastUpdateId(updates) + 1
                messageDict, similarityDict, parentTimes, messagesToBlock = handleUpdates(updates,messageDict,similarityDict,parentTimes,messagesToBlock)
                
                # remove these prints and set as command that can be queried OR make one method
                print("messagedict in updates: ", len(messageDict))
                print("similarityDict in updates: ", len(similarityDict))
                print("Summaries in updates: ", len(parentTimes))
        except Exception as e:
            # log these exceptions into DB
            print("GetUpdates exception, waiting 10s before retry")
            print("Exception: ", e)
            time.sleep(10)
            pass
        

def sendSummary(messageDict,similarityDict,parentTimes):
    secondsToWait = config.SummaryDelay # WIP - would be nice to set this in telegram
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
        # rather check for channel/normal message here
        try:
            text, chat, messageID = Telegram.GetMessage(update)
        except:
            text, chat, messageID = Telegram.GetChannelPost(update)
        # could summarize these into commands method
        if text == '/deleteall':
            notifications.delete_all()
            messageDict = clearDictProxy(messageDict) # for thread manager to detect delete changes
            similarityDict = clearDictProxy(similarityDict) # for thread manager to detect delete changes
            parentTimes = clearDictProxy(parentTimes) # for thread manager to detect delete changes
            Telegram.SendMessage("All items have been deleted from the FishNet database", chat)
        elif text == "/start":
            Telegram.SendMessage('Welcome to the FishNet bot, where messages are in abundance and the net catches them all\n\nPlease enter a password with the prefix / to gain access', chat)
        elif text == "/selectedpassword":
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
                    similarityDict = textSimilarity.CompareMessages(messageDict,similarityDict)
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

def clearDictProxy(dictionary):
    temp = dictionary
    temp.clear()
    dictionary = temp
    return dictionary

def isEmpty(anyStructure):
    if anyStructure:
        return False
    else:
        return True

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
        similarity = textSimilarity.getSingleSimilarity(text)
        if similarity > 0.7:
            return key
    return 0
        