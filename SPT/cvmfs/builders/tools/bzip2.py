"""bzip2 build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name, version=None):
    if not os.path.exists(os.path.join(dir_name, 'bin', 'bzip2')):
        print('installing bzip2 version', version)
        name = 'bzip2-' + str(version) + '.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://www.bzip.org/', version, name)
            wget(url, path)
            unpack(path, tmp_dir)
            bzip2_dir = os.path.join(tmp_dir, 'bzip2-' + version)
            if subprocess.call(['make', 'install', 'PREFIX=%s' % dir_name], cwd = bzip2_dir):
                raise Exception('bzip2 failed to make')
            if subprocess.call(['make','clean'], cwd = bzip2_dir):
                raise Exception('bzip2 failed to install')
            if subprocess.call(['make', '-f', 'Makefile-libbz2_so','PREFIX=%s' % dir_name], cwd = bzip2_dir):
                raise Exception('bzip2 failed to install')

            shutil.copy2(os.path.join(bzip2_dir, "libbz2.so.1.0.6"), 
                         os.path.join(dir_name, "lib"))
            shutil.copy2(os.path.join(bzip2_dir, "libbz2.so.1.0"), 
                         os.path.join(dir_name, "lib"))
            os.symlink(os.path.join(dir_name, "lib", "libbz2.so.1.0"), os.path.join(dir_name, "lib", "libbz2.so"))
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
