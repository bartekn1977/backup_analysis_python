# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for backup_analysis
# For maximum compatibility across RHEL 7-10, build on RHEL 7

import os

a = Analysis(
    ['backup_analysis.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates/*.j2', 'templates'),  # Bundle Jinja2 templates
        ('lib/*.py', 'lib'),              # Bundle lib modules
        ('lib/sql/*.sql', 'lib/sql'),     # Bundle SQL files
        ('etc/config.ini', 'etc'),        # Bundle config file
    ],
    hiddenimports=[
        'oracledb',
        'jinja2',
        'texttable',
        'cryptography',
        'cffi',
        'secrets',
        'getpass',
        'ssl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='backup_analysis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
