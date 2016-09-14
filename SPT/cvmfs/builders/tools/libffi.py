"""libffi build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libffi.so')):
        print('installing libffi version',version)
        name = 'libffi-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('ftp://sourceware.org/pub/libffi/',name)
            wget(url,path)
            unpack(path,tmp_dir)
            libffi_dir = os.path.join(tmp_dir,'libffi-'+version)
            if subprocess.call([os.path.join(libffi_dir,'configure'),
                                '--prefix',dir_name],
                               cwd=libffi_dir):
                raise Exception('libffi failed to configure')
            if subprocess.call(['make'],cwd=libffi_dir):
                raise Exception('libffi failed to make')
            if subprocess.call(['make','install'],cwd=libffi_dir):
                raise Exception('libffi failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
