#!/bin/bash

LD_LIBRARY_PATH=/usr/lib/grass78/lib
export LD_LIBRARY_PATH

PYTHONPATH=/usr/share/qgis/python/plugins
export PYTHONPATH

python3 -m unittest test_qswatplus
python3 -m unittest test_dbutils
python3 -m unittest test_polygonizeInC2