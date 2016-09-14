"""flac build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name, version=None):
    if not os.path.exists(os.path.join(dir_name, 'bin', 'flac')):
        print('installing flac version', version)
        name = 'flac-' + str(version) + '.tar.xz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://downloads.xiph.org/releases/flac/', name)
            wget(url, path)
            unpack_xz(path, tmp_dir)
            flac_dir = os.path.join(tmp_dir, 'flac-' + version)
            if subprocess.call([os.path.join(flac_dir,' configure'),
                                '--prefix=' + dir_name], cwd = flac_dir):
                raise Exception('flac failed to configure')
            if subprocess.call(['make'], cwd = flac_dir):
                raise Exception('flac failed to make')
            if subprocess.call(['make','install'], cwd = flac_dir):
                raise Exception('flac failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
