#=======================================================================
#       $Id: sqlrepo.py,v 1.1 2011/01/17 20:21:41 pythontech Exp pythontech $
#	Repository using sqlite
#=======================================================================
import sqlite3
import psync
import os

class SqlRepo(psync.Repo):
    def __init__(self, filename):
        self.filename = filename
        exists = os.path.exists(filename)
        self.conn = sqlite3.connect(filename)
        self.cursor = self.conn.cursor()
        if exists:
            self._create_tables()

    def getstate(self, path):
        id = self._pathid(path)
        if id is None:
            return None
        sql = 'SELECT type,avsn,bvsn FROM state WHERE id=?'
        row = self._1row(sql, id)
        if row is None:
            return None
        return psync.RepoState(*row)

    def setstate(self, path, type, avsn, bvsn):
        id = self._pathid(path, True)
        sql = 'INSERT OR REPLACE INTO state (id,type,a,b) VALUES (?,?,?,?)'
        self._add(sql, id, type, avsn, bvsn)

    def delstate(self, path):
        id = self._pathid(path)
        if id is None:
            return
        # FIXME recursion
        sql = 'DELETE FROM state WHERE id=?'
        self._do(sql, id)

    def getconflict(self, path):
        id = self._pathid(path)
        if id is None:
            return None
        sql = 'SELECT conflict FROM state WHERE id=?'
        row = self._1row(sql, id)
        if row is None:
            return None
        return row[0]

    def setconflict(self, path, conflict):
        id = self._pathid(path)
        if id is None:
            raise Exception, 'Setting conflict for unknown path %s' % repr(path)
        sql = 'UPDATE state SET conflict=? WHERE id=?'
        self._do(sql, conflict, id)

    def readdir(self, path):
        id = self._pathid(path)
        if id is None:
            return []
        sql = 'SELECT leaf FROM item WHERE parent=?'
        dir = []
        for row in self._iterrows(sql, id):
            dir.append(row[0])
        return dir

    def _create_tables(self):
        c = self.conn.cursor()
        c.execute('CREATE TABLE item (id INTEGER PRIMARY KEY, parent INTEGER, leaf TEXT);')
        c.execute('CREATE TABLE state (id INTEGER PRIMARY KEY, type TEXT, a TEXT, b TEXT, conflict TEXT);')
        #c.execute('CREATE INDEX child ON item(parent,leaf);')

    def _pathid(self, path, create=False):
        # Get primary key for path, optionally creating if not in database
        id = 0
        for step in path:
            row = self._1row('SELECT id FROM item WHERE parent=? AND leaf=?',
                             pid, step)
            if row is None:
                if not create:
                    return None
                # Create new item
                sql = 'INSERT INTO item (id,parent,leaf) VALUES (NULL,?,?);'
                cid = self._add(sql, id, step)
            else:
                cid, = row
            id = cid
        return id

    def _do(self, sql, *values):
        c = self.conn.cursor
        c.execute(sql, values)

    def _1row(self, sql *values):
        c = self.conn.cursor
        c.execute(sql, values)
        return c.fetchone()

    def _iterrows(self, sql, *values):
        c = self.conn.cursor()
        c.execute(sql, values)
        while True:
            row = c.fetchone()
            if not row:
                return
            yield row

    def _add(self, sql, *values):
        c = self.conn.cursor()
        c.execute(sql, values)
        return c.lastrowid
