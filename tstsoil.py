# -*- coding: utf-8 -*-

import sqlite3
import time
import random

from QSWATPlus.parameters import Parameters
from QSWATPlus.QSWATUtils import QSWATUtils

SSURGO1 = QSWATUtils.join(Parameters._DBDIR, 'SWAT_US_SSURGO_Soils.sqlite')
SSURGO2 = QSWATUtils.join(Parameters._DBDIR, 'swatplus_soils.sqlite')

def getCols(table, cursor):
    row = cursor.execute('SELECT * FROM {0}'.format(table)).fetchone()
    return list(row.keys())

def countCols(table, cursor):
    sql = cursor.execute('SELECT sql FROM sqlite_master WHERE name = "{0}" AND type = "table"'.format(table)).fetchone()[0]
    count = len(sql.split(','))
    return count

conn = sqlite3.connect(SSURGO1)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
random.seed(0)
time1 = time.process_time()
for _ in range(1):
    sid = random.randint(1, 303985)
    soil = cur.execute('SELECT * FROM SSURGO_Soils WHERE OBJECTID=?', (sid,)).fetchone()
    numLayers = int(soil[6])
    result = float(soil[8])
    for i in range(numLayers):
        result += float(soil[12 + i * 12])
time2 = time.process_time()
print('Time to process SSURGO1: {0} seconds'.format(int(time2 - time1)))
print('Column count is {0}'.format(countCols('SSURGO_Soils', cur)))
print('Columns in SSURGO_Soils: {0}'.format(str(getCols('SSURGO_Soils', cur))))
conn.close()

conn = sqlite3.connect(SSURGO2)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
random.seed(0)
time1 = time.process_time()
for _ in range(1):
    sid = random.randint(1, 303985)
    soil = cur.execute('SELECT * FROM ssurgo WHERE id=?', (sid,)).fetchone()
    result = float(soil[7])
    layers = cur.execute('SELECT * FROM ssurgo_layer WHERE soil_id=?', (sid,)).fetchall()
    for layer in layers:
        result += float(layer[3])
time2 = time.process_time()
print('Time to process SSURGO2: {0} seconds'.format(int(time2 - time1)))
print('Column count is {0}'.format(countCols('ssurgo', cur)))
print('Columns in ssurgo: {0}'.format(str(getCols('ssurgo', cur))))
print('Columns in ssurgo_layer: {0}'.format(str(getCols('ssurgo_layer', cur))))
conn.close()

