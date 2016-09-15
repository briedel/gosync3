"""libpng build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name, version=None):
    if not os.path.exists(os.path.join(dir_name, 'lib', 'ligpng.so')):
        print('installing freetype version', version)
        name = 'libpng-' + str(version) + '.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://download.sourceforge.net/libpng/', name)
            wget(url, path)
            unpack(path, tmp_dir)
            libpng_dir = os.path.join(tmp_dir, 'libpng-' + version)
            if subprocess.call([os.path.join(libpng_dir, 'configure'),
                                '--prefix=' + dir_name], cwd = libpng_dir):
                raise Exception('freetype failed to configure')
            if subprocess.call(['make'], cwd = libpng_dir):
                raise Exception('freetype failed to make')
            if subprocess.call(['make','install'], cwd = libpng_dir):
                raise Exception('freetype failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
