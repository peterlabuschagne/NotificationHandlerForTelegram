# Put the code here that you need to run the application/start the application
from src.reader import Manager, Process, db, users, sendSummary, updates

def main():
    manager = Manager()
    messageDict = manager.dict()
    similarityDict = manager.dict()
    parentTimes = manager.dict()
    updatesProcess = Process(target=updates, args=(messageDict,similarityDict,parentTimes,))
    sendSummaryProcess = Process(target=sendSummary, args=(messageDict,similarityDict,parentTimes,))
    updatesProcess.start()
    sendSummaryProcess.start()
    updatesProcess.join()
    sendSummaryProcess.join()

if __name__ == '__main__':
    db.setup()
    users.setup()
    users.delete_all()
    users.add_user('729427424')
    main()