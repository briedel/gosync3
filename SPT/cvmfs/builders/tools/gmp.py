"""gmp build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack_bz2, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libgmp.so')):
        print('installing gmp version',version)
        name = 'gmp-'+str(version)+'.tar.bz2'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('https://ftp.gnu.org/gnu/gmp',name)
            wget(url,path)
            unpack_bz2(path,tmp_dir)
            if version[-1] == 'a':
                gmp_dir = os.path.join(tmp_dir,'gmp-'+version[0:-1])
            else:
                gmp_dir = os.path.join(tmp_dir,'gmp-'+version)
            if subprocess.call([os.path.join(gmp_dir,'configure'),
                                '--prefix',dir_name],cwd=gmp_dir):
                raise Exception('gmp failed to configure')
            if subprocess.call(['make'],cwd=gmp_dir):
                raise Exception('gmp failed to make')
            if subprocess.call(['make','install'],cwd=gmp_dir):
                raise Exception('gmp failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
