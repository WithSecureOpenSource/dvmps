"""
use: python.exe setup.py py2exe

from distutils.core import setup
import py2exe

setup(console=['kvm_ui.py'])
"""

"""
Copyright (c) 2012-2013 F-Secure
See LICENSE for details
"""

from distutils.core import setup
import py2exe, sys, os

sys.argv.append('py2exe')

setup(
    data_files=[('.', ['mainwindow.ui', 'dialog.ui'])],
    options = {'py2exe': {'bundle_files': 1}},
    windows = [{'script': "kvm_ui.py"}],
    zipfile = None,
)

