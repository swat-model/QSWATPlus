"""Build script for QSWATPlus generated/compiled artefacts.

Handles:
  1. .ui -> ui_*.py  (pyuic6, falls back to pyuic5, then qgis.PyQt post-processing)
  2. .pyx -> .so/.pyd (Cython compilation of dataInC.pyx)

Usage:
    python make_uis.py [directory]   — build everything
    python make_uis.py --ui          — UI files only
    python make_uis.py --cython      — Cython modules only

If no directory is given, uses the script's own directory.
"""

import os
import subprocess
import sys


# ---------------------------------------------------------------------------
# UI compilation
# ---------------------------------------------------------------------------

def find_ui_compiler():
    """Return the pyuic command available on this system."""
    for cmd in ('pyuic6', 'pyuic5'):
        try:
            subprocess.run([cmd, '--version'], capture_output=True, check=True)
            return cmd
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    raise RuntimeError('Neither pyuic6 nor pyuic5 found on PATH')


def compile_ui(compiler, ui_file, py_file):
    """Compile a single .ui file to .py."""
    print(f'  {compiler} {os.path.basename(ui_file)} -> {os.path.basename(py_file)}')
    subprocess.run([compiler, '-o', py_file, ui_file], check=True)


def compile_all_ui(directory):
    """Compile all .ui files in directory and post-process the results."""
    compiler = find_ui_compiler()
    print(f'Using {compiler}')

    for filename in sorted(os.listdir(directory)):
        if filename.startswith('ui_') and filename.endswith('.ui'):
            ui_path = os.path.join(directory, filename)
            py_path = os.path.join(directory, filename[:-3] + '.py')
            compile_ui(compiler, ui_path, py_path)

    # Special case: ui_graph.ui -> ui_graph1.py
    graph_ui = os.path.join(directory, 'ui_graph.ui')
    graph1_py = os.path.join(directory, 'ui_graph1.py')
    if os.path.exists(graph_ui):
        compile_ui(compiler, graph_ui, graph1_py)

    # Post-process imports: PyQt5/PyQt6 -> qgis.PyQt
    from postprocess_ui import postprocess_directory
    postprocess_directory(directory)


# ---------------------------------------------------------------------------
# Cython compilation
# ---------------------------------------------------------------------------

def compile_cython(directory):
    """Compile .pyx files that need Cython (dataInC and jenks)."""
    try:
        from Cython.Build import cythonize
    except ImportError:
        print('Cython not installed — skipping .pyx compilation')
        print('  Install with: pip install cython')
        return

    import numpy
    from distutils.core import setup, Extension

    pyx_modules = ['dataInC', 'jenks', 'polygonizeInC2']
    extensions = []
    for name in pyx_modules:
        pyx_file = os.path.join(directory, name + '.pyx')
        if os.path.exists(pyx_file):
            extensions.append(Extension(name, [pyx_file],
                                        include_dirs=[numpy.get_include()]))
        else:
            print(f'  {name}.pyx not found — skipping')

    if not extensions:
        return

    for ext in extensions:
        print(f'  Compiling {os.path.basename(ext.sources[0])} ...')

    orig_dir = os.getcwd()
    orig_argv = sys.argv[:]
    try:
        os.chdir(directory)
        sys.argv = ['setup.py', 'build_ext', '--inplace']
        setup(ext_modules=cythonize(extensions, language_level=3))
    finally:
        os.chdir(orig_dir)
        sys.argv = orig_argv
    print('  done')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    args = sys.argv[1:]
    ui_only = '--ui' in args
    cython_only = '--cython' in args
    args = [a for a in args if not a.startswith('--')]

    target = args[0] if args else os.path.dirname(os.path.abspath(__file__))

    if not ui_only and not cython_only:
        ui_only = cython_only = True

    if ui_only:
        compile_all_ui(target)
    if cython_only:
        compile_cython(target)
