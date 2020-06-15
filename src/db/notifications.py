import sqlite3
import operator


class Notifications:
    def __init__(self, dbname="notifications.sqlite"):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname)
        self.cursor = self.conn.cursor()

    def setup(self):
        tblstmt = "CREATE TABLE IF NOT EXISTS items (description text, owner text, messageID, datetime timestamp)"
        itemidx = "CREATE INDEX IF NOT EXISTS itemIndex ON items (description ASC)" 
        ownidx = "CREATE INDEX IF NOT EXISTS ownIndex ON items (owner ASC)"
        self.conn.execute(tblstmt)
        self.conn.execute(itemidx)
        self.conn.execute(ownidx)
        self.conn.commit()

    def add_item(self, item_text, owner, messageID, datetime):
        stmt = "INSERT INTO items (description, owner, messageID, datetime) VALUES (?, ?, ?, ?)"
        args = (item_text, owner, messageID, datetime)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def delete_item(self, item_text, owner):
        stmt = "DELETE FROM items WHERE description = (?) AND owner = (?)"
        args = (item_text, owner)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def delete_all(self):
        stmt = "DELETE FROM items"
        self.conn.execute(stmt)
        self.conn.commit()

    def delete_last(self):
        stmt = "DELETE FROM items WHERE messageID = (SELECT MAX(messageID) FROM items)"
        self.conn.execute(stmt)
        self.conn.commit()

    def count_items(self):
        try:
            stmt = "SELECT COUNT(*) FROM items"
            self.cursor.execute(stmt)
            count = self.cursor.fetchone()
            return count[0]
        except Exception as e:
            self.cursor.close()
            print(e)
            return -1

    def get_items(self, owner=None):
        stmt = "SELECT description FROM items"
        if owner:
            stmt +=  " WHERE owner = (?) ORDER BY messageID"
            args = (owner, )
            return [x[0] for x in self.conn.execute(stmt, args)]
        else:
            stmt += " ORDER BY messageID"
            return [x[0] for x in self.conn.execute(stmt)]

    def getDict(self, owner=None):
        dictionary = {}
        stmt = "SELECT description, messageID FROM items"
        if owner:
            stmt +=  " WHERE owner = (?) ORDER BY messageID"
            args = (owner, )
            return self.returnDict(dictionary, stmt, args)
        else:
            stmt += " ORDER BY messageID"
            self.cursor.execute(stmt)
            return self.returnDict(dictionary, stmt) 

    def getMessageTime(self, messageID):
        stmt = "SELECT datetime FROM items WHERE messageID = (?)"
        args = (messageID, )
        self.cursor.execute(stmt, args)
        return self.cursor.fetchone()

    def updateDict(self, dictionary, owner=None):
        if dictionary:
            maxID = self.GetMaxMessageID(dictionary)
        else:
            maxID = 0
        stmt = "SELECT description, messageID from items"
        if owner:
            stmt +=  " WHERE owner = (?) AND messageID > (?) ORDER BY messageID"
            args = (owner, maxID, )
            return self.returnDict(dictionary, stmt, args)
        else:
            stmt += " WHERE messageID > (?) ORDER BY messageID"
            args = (maxID, )
            return self.returnDict(dictionary, stmt, args) 

    def returnDict(self, dictionary, stmt, args=None):
        if args:
            self.cursor.execute(stmt,args)
            result = self.cursor.fetchall()
            for description, messageID in result:
                dictionary[messageID] = description
            return dictionary
        else:
            self.cursor.execute(stmt)
            result = self.cursor.fetchall()
            for description, messageID in result:
                dictionary[messageID] = description
            return dictionary

    def GetMaxMessageID(self, dictionary):
        maxID = 0
        for key in dictionary.keys():
            if key > maxID:
                maxID = key
        return maxID
        