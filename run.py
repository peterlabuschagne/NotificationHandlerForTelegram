# Put the code here that you need to run the application/start the application
import config

from multiprocessing import Manager, Process 
from src.handlers.reader import updates, sendSummary
from src.db import users, notifications


notifications = notifications.Notifications()
users = users.Users()

def main():
    manager = Manager()
    messageDict = manager.dict()
    similarityDict = manager.dict()
    parentTimes = manager.dict()
    messagesToBlock = manager.list()
    updatesProcess = Process(target=updates, args=(messageDict,similarityDict,parentTimes,messagesToBlock,))
    sendSummaryProcess = Process(target=sendSummary, args=(messageDict,similarityDict,parentTimes,))
    updatesProcess.start()
    sendSummaryProcess.start()
    updatesProcess.join()
    sendSummaryProcess.join()

if __name__ == '__main__':
    # setup
    notifications.setup()
    users.setup()

    # config
    users.delete_all()
    for chatID in config.Users:    
        users.addUser(chatID)
    
    # run
    main()