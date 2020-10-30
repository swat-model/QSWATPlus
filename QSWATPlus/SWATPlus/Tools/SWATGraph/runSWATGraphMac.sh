#!/bin/sh

export set OSGEO4W_ROOT=/Applications/QGIS3.10.app/Contents

export set PYTHONHOME=${OSGEO4W_ROOT}/Frameworks/Python.framework/Versions/Current
export set QT_PLUGIN_PATH=${OSGEO4W_ROOT}/PlugIns

${OSGEO4W_ROOT}/MacOS/bin/python3 "${HOME}/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/QSWATPlusMac3_64/swatgraph.py" $1
