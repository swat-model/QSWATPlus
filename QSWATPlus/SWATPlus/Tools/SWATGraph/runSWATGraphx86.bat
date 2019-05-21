@echo off
set OSGEO4W_ROOT="C:\Program Files\QGIS 3.4"
SET QGISNAME=qgis-ltr
SET QGIS=%OSGEO4W_ROOT%\apps\%QGISNAME%
set QGIS_PREFIX_PATH=%QGIS%

CALL %OSGEO4W_ROOT%\bin\o4w_env.bat
call %OSGEO4W_ROOT%\bin\qt5_env.bat
call %OSGEO4W_ROOT%\bin\py3_env.bat

REM note second entry: essential to find qgis.core, qgis.gui, etc
SET PATH=%OSGEO4W_ROOT%\bin;%OSGEO4W_ROOT%\apps\%QGISNAME%\bin;%OSGEO4W_ROOT%\apps\%QGISNAME%\python;%PATH%
SET PYTHONHOME=%OSGEO4W_ROOT%\apps\Python37
SET PYTHONPATH=%QGIS%\python;%QGIS%\python\plugins
rem SET QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\Qt5\plugins
SET GDAL_DATA=%OSGEO4W_ROOT%\share\gdal
SET GDAL_DRIVER_PATH=%OSGEO4W_ROOT%\bin\gdalplugins

python3 "%USERPROFILE%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\QSWATPlus3_32\swatgraph.py" %1






