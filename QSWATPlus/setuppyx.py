from distutils.core import setup
    
from Cython.Build import cythonize  # @UnresolvedImport
import os
import numpy
if 'QSWAT_PROJECT' in os.environ and 'Linux' in os.environ['QSWAT_PROJECT']:
    includePath = '/usr/include/python3.'
    numpyInclude = numpy.get_include()
    sep = ':'
    is32 = '_32' in os.environ['QSWAT_PROJECT']
elif 'QSWAT_PROJECT' in os.environ and 'Mac' in os.environ['QSWAT_PROJECT']:
    includePath = '/usr/local/opt/python@3.9/Frameworks/Python.framework/Versions/3.9/include/python3.9'
    numpyInclude = '/usr/local/lib/python3.9/site-packages/numpy/core/include'
    sep = ':'
    is32 = '_32' in os.environ['QSWAT_PROJECT']
else:
    includePath = os.environ['OSGEO4W_ROOT'] + r'/apps/Python37/include'
    numpyInclude = numpy.get_include()
    sep = ';'
    is32 = False
if 'INCLUDE' in os.environ:
    os.environ['INCLUDE'] = os.environ['INCLUDE'] + sep + includePath + sep + numpyInclude 
else:
    os.environ['INCLUDE'] = includePath + sep + numpyInclude
    
print('include path is {0}'.format(os.environ['INCLUDE']))

# NB for Linux also had to 
#sudo ln -s  /usr/lib/python3/dist-packages/numpy/core/include/numpy /usr/include/numpy
# for it to find numpy/arrayobject.h

if is32:
    # only run cythonize to get .c files from .pyx
    cythonize('*.pyx', include_path = [os.environ['INCLUDE']])
else:
    setup(
        name = "pyxes",
        package_dir = {'QSWATPlus': ''}, 
        ext_modules = cythonize('*.pyx', include_path = [os.environ['INCLUDE']]),
    )
