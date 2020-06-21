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
    lastRequest = datetime.now
    while True:
        try:
            updates = Telegram.GetUpdates(lastUpdateID)
            if len(updates["result"]) > 0:
                lastUpdateID = Telegram.GetLastUpdateId(updates) + 1
                messageDict, similarityDict, parentTimes, messagesToBlock = handleUpdates(updates,messageDict,similarityDict,parentTimes,messagesToBlock,lastRequest)

            lastRequest = datetime.now()
        except Exception as ex:
            requestException = 'updates exception with last request {}, waiting 10s before retry\n\nException: {}'.format(lastRequest,ex)  
            print(requestException)
            time.sleep(10)
            pass
        

def sendSummary(messageDict,similarityDict,parentTimes):
    while True:
        try:
            for parent in parentTimes.keys():
                secondsToWait = config.SummaryInterval
                children = similarityDict[parent]
                timeofMessage = parentTimes[parent]
                timeSinceParentMessage = getTimeDifference(timeofMessage,datetime.now())
                if timeSinceParentMessage > secondsToWait:
                    textSummary = textSimilarity.GetSummarisedText(parent,children,messageDict)
                    if textSummary != "":
                        textSummary = '{}s since parent message:\n\n{}\n\nshowing summary for {} similar messages:\n\n{}'.format(secondsToWait,messageDict[parent], len(similarityDict[parent]), textSummary)
                        sendMessageToAllUsers(textSummary)
                    del parentTimes[parent]
            time.sleep(1)
        except Exception as ex:
            sendSummaryException = 'sendSummary exception at {}, waiting 10s before retry\n\nException: {}'.format(datetime.now,ex)  
            print(sendSummaryException)
            time.sleep(10)
            pass
        

def handleUpdates(updates,messageDict,similarityDict,parentTimes,messagesToBlock,lastRequest):
    for update in updates["result"]:
        text, chat, messageID = Telegram.MessageDetails(update)
        # WIP - could summarize these into commands method
        if Telegram.IsCommand(text):
            if text.startswith("/blocked"):
                try:
                    message = text[8:] # WIP - find index instead
                    Telegram.SendMessage('You have blocked {}'.format(message), chat)
                    messagesToBlock = blockMessage(message,similarityDict,messageDict,messagesToBlock)
                    Telegram.SendMessage('The following message has now been added to blocked messages:\n\n{}'.format(message), chat)
                except:
                    Telegram.SendMessage('Message could not be blocked',chat)
                    # WIP - check if the message has already been blocked
                    # WIP - log exception as to why the message couldn't be blocked
                    pass
            # WIP - view blocked messages command
            elif text == '/deleteall':
                notifications.delete_all()
                messageDict = clearDictProxy(messageDict) # for thread manager to detect delete changes
                similarityDict = clearDictProxy(similarityDict) # for thread manager to detect delete changes
                parentTimes = clearDictProxy(parentTimes) # for thread manager to detect delete changes
                Telegram.SendMessage("All items have been deleted from the FishNet database", chat)
            elif text == "/getsummary":
                for parent in parentTimes.keys():
                    children = similarityDict[parent]
                    textSummary = textSimilarity.GetSummarisedText(parent,children,messageDict)
                    Telegram.SendMessage(textSummary,chat)
            elif text == "/running":
                Telegram.SendMessage('Yes, it is still running\nLast update request: ' + str(lastRequest), chat)
            elif text == '/{}'.format(config.SignUpPassword):
                if str(chat) not in users.get_users():  
                    Telegram.SendMessage('Well you got it right... guess I should start sending you messages now', chat)
                    users.addUser(chat)
                    Telegram.SendAnimation(chat)
                    print(users.get_users())
            elif text.startswith("/setinterval"):
                try:
                    oldInterval = config.SummaryInterval
                    newInterval = text[12:]
                    config.SummaryInterval = newInterval
                    Telegram.SendMessage('Summary interval set from {}s to {}s'.format(oldInterval, newInterval), chat)
                except:
                    Telegram.SendMessage('Could not set summary interval, ensure correct message format of /setinterval<seconds>',chat)
                    pass
            elif text == "/start":
                Telegram.SendMessage('Welcome to the FishNet bot, where messages are in abundance and the net catches them all\n\nPlease enter a password with the prefix / to gain access', chat)
            elif text == "/status":
                summaryMessage = 'Total Messages: {}\nGrouped Messages: {}\nPending Summaries: {}'.format(len(messageDict), len(similarityDict), len(parentTimes))
                Telegram.SendMessage(summaryMessage, chat)
            else:
                Telegram.SendMessage('Unrecognized Command', chat)

        else:
            print(messageID)
            if True: # WIP - accept specific user/channel messages only
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
        