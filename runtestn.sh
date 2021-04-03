#!/bin/bash

LD_LIBRARY_PATH=/usr/lib/grass78/lib
export LD_LIBRARY_PATH

PYTHONPATH=/usr/share/qgis/python/plugins
export PYTHONPATH

python3 -m unittest -v test_qswatplus.TestQswat.test$1
