from distutils.core import setup
    
from Cython.Build import cythonize 
import os
import numpy
if 'QSWAT_PROJECT' in os.environ and 'Linux' in os.environ['QSWAT_PROJECT']:
    includePath = '/usr/include/python3.6'
    sep = ':'
    is32 = '_32' in os.environ['QSWAT_PROJECT']
else:
    includePath = os.environ['OSGEO4W_ROOT'] + r'/apps/Python37/include'
    sep = ';'
    is32 = False
if 'INCLUDE' in os.environ:
    os.environ['INCLUDE'] = os.environ['INCLUDE'] + sep + includePath + sep + numpy.get_include()
else:
    os.environ['INCLUDE'] = includePath + sep + numpy.get_include()

if is32:
    # only run cythonize to get .c files from .pyx
    cythonize('*.pyx', include_path = [os.environ['INCLUDE']])
else:
    setup(
        name = "pyxes",
        package_dir = {'QSWATPlus': ''}, 
        ext_modules = cythonize('*.pyx', include_path = [os.environ['INCLUDE']]),
    )
 