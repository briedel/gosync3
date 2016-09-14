"""binutils build/install"""

import os
import subprocess
import tempfile
import shutil
import copy

from build_util import wget, unpack, version_dict

try:
    import multiprocessing
    cpu_cores = multiprocessing.cpu_count()
except ImportError:
    cpu_cores = 1

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','gcc')):
        print('installing binutils version',version)
        name = 'binutils-' + str(version) + '.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://ftp.gnu.org/gnu/binutils/', name)
            wget(url,path)
            unpack(path,tmp_dir)
            binutils_dir = os.path.join(tmp_dir,'binutils')
            configure_options = [
                '--prefix=' + dir_name,
                '--with-gmp-include=' + os.path.join(dir_name, "include"),
                '--with-gmp-lib=' + os.path.join(dir_name, "lib")
            ]
            if subprocess.call([os.path.join(gcc_dir, 'configure')] + configure_options,
                                cwd = binutils_dir):
                raise Exception('gcc failed to configure')
            if subprocess.call(['make', '-j' + str(cpu_cores)],
                               cwd=binutils_dir):
                raise Exception('binutils failed to configure')
            if subprocess.call(['make','install'],
                               cwd=binutils_dir):
                raise Exception('binutils failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
