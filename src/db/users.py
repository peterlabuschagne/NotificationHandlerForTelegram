import sqlite3

class Users:
    def __init__(self, dbname="users.sqlite"):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname)
        self.cursor = self.conn.cursor()

    def setup(self):
        tblstmt = "CREATE TABLE IF NOT EXISTS users (chatID text)"
        usersidx = "CREATE INDEX IF NOT EXISTS usersIndex ON users (chatID ASC)" 
        self.conn.execute(tblstmt)
        self.conn.execute(usersidx)
        self.conn.commit()

    def addUser(self, chatID):
        stmt = "INSERT INTO users (chatID) VALUES (?)"
        args = (chatID, )
        self.conn.execute(stmt, args)
        self.conn.commit()

    def delete_user(self, chatID):
        stmt = "DELETE FROM users WHERE chatID = (?)"
        args = (chatID, )
        self.conn.execute(stmt, args)
        self.conn.commit()

    def delete_all(self):
        stmt = "DELETE FROM users "
        self.conn.execute(stmt)
        self.conn.commit()

    def count_users(self):
        try:
            stmt = "SELECT COUNT(*) FROM users"
            self.cursor.execute(stmt)
            count = self.cursor.fetchone()
            return count[0]
        except Exception as e:
            self.cursor.close()
            print(e)
            return -1

    def get_users(self):
        stmt = "SELECT chatID FROM users"
        return [x[0] for x in self.conn.execute(stmt)]