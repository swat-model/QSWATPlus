@echo off
pushd C:\Program Files\QGIS 3.10
call .\bin\o4w_env.bat
call .\bin\qt5_env.bat
call .\bin\py3_env.bat

set GISNAME=qgis-ltr

path %OSGEO4W_ROOT%\apps\%GISNAME%\bin;%PATH%
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT:\=/%/apps/%GISNAME%
set GDAL_FILENAME_IS_UTF8=YES
rem Set VSI cache to be used as buffer, see #6448
set VSI_CACHE=TRUE
set VSI_CACHE_SIZE=1000000
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\%GISNAME%\qtplugins;%OSGEO4W_ROOT%\apps\qt5\plugins
set PYTHONPATH=%OSGEO4W_ROOT%\apps\%GISNAME%\python;%OSGEO4W_ROOT%\apps\%GISNAME%\python\plugins;%PYTHONPATH%
"%PYTHONHOME%\python" "%USERPROFILE%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\QSWATPlus3_64\convertFromArc.py" %~dp0
popd
