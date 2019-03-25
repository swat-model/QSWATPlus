# -*- coding: utf-8 -*-

import sqlite3
import time
import hashlib

db = 'C:/QSWAT_Projects/Sudan/srini/sudan10k/sudan10k.sqlite'
selectSql = 'SELECT * FROM subbasins JOIN subbasins2 ON subbasins.ID = subbasins2.ID2'
createSql = 'CREATE TABLE subbasins3 AS {0}'.format(selectSql)
indexSQL = 'CREATE UNIQUE INDEX subbasins3_id_index ON subbasins3 (ID)'
extractJoinSql = 'SELECT ID, AREA, AREA2 FROM subbasins JOIN subbasins2 ON subbasins.ID = subbasins2.ID2'
extract3Sql = 'SELECT ID, AREA, AREA2 FROM {0}'.format('subbasins3')
dropSql = 'DROP TABLE IF EXISTS subbasins3'

connection = sqlite3.connect(db)
connection.row_factory = sqlite3.Row
with connection as conn:
    time0 = time.process_time()
    conn.execute(dropSql)
    conn.execute(createSql)
    conn.execute(indexSQL)
    for _ in range(100):
        for row in conn.execute(extract3Sql).fetchall():
            result = row['AREA'] + row['AREA2']
    time1 = time.process_time()
    print('Time for create and drop subbasins3 is {0}'.format(int(time1 - time0)))
    time2 = time.process_time()
    for _ in range(100):
        for row in conn.execute(extractJoinSql).fetchall():
            result = row['AREA'] + row['AREA2']
    time3 = time.process_time()
    print('Time for dynamic join is {0}'.format(int(time3 - time2)))
    
    m = hashlib.md5()
    connection.row_factory = lambda x, y: y
    sql = 'SELECT * FROM subbasins' 
    for row in conn.execute(sql).fetchall():
        m.update(row.__repr__())
    result = m.hexdigest()
    print(result)
    
    m2 = hashlib.md5()
    sql = 'SELECT * FROM subbasins' 
    for row in conn.execute(sql).fetchall():
        m2.update(row.__repr__())
    result = m2.hexdigest()
    print(result)