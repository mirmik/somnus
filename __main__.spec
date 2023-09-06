# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

datas = []
for (p, d, f) in os.walk("./assets/"):
  datas.extend([(os.path.join(p,a), os.path.relpath(p, start=".")) for a in f])

path = os.getcwd()

a = Analysis(['src/__main__.py'],
             pathex=[path],
             binaries=[],
             datas=datas,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=True)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='Somnus.exe' if sys.platform == "win32" else 'Somnus',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='Somnus')
