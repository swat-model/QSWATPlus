"""Post-process generated ui_*.py files for QGIS compatibility.

Replaces direct PyQt5/PyQt6 imports with qgis.PyQt imports so the
generated files work under both QGIS 3.x (PyQt5) and QGIS 4.x (PyQt6).

Usage:
    python postprocess_ui.py [directory]

If no directory is given, processes the script's own directory.

Author  : Celray James CHAWANDA
Email   : celray.chawanda@outlook.com
Licence : GNU General Public License
Repo    : https://github.com/celray

Date    : 2026-04-07 - 15:51
"""

import os
import re
import sys


def postprocess_file(filepath):
    """Fix PyQt imports in a single generated ui file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    # Replace direct PyQt5 or PyQt6 imports with qgis.PyQt
    content = re.sub(r'from PyQt[56]', 'from qgis.PyQt', content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  Fixed imports in {os.path.basename(filepath)}')


def postprocess_directory(directory):
    """Post-process all ui_*.py files in the given directory."""
    count = 0
    for filename in sorted(os.listdir(directory)):
        if filename.startswith('ui_') and filename.endswith('.py'):
            postprocess_file(os.path.join(directory, filename))
            count += 1
    print(f'Post-processed {count} ui files in {directory}')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = os.path.dirname(os.path.abspath(__file__))
    postprocess_directory(target)
