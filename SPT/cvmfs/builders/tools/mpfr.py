"""mpfr build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack_bz2, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libmpfr.so')):
        print('installing mpfr version',version)
        name = 'mpfr-'+str(version)+'.tar.bz2'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://www.mpfr.org/mpfr-'+str(version),name)
            wget(url,path)
            unpack_bz2(path,tmp_dir)
            if version[-1] == 'a':
                mpfr_dir = os.path.join(tmp_dir,'mpfr-'+version[0:-1])
            else:
                mpfr_dir = os.path.join(tmp_dir,'mpfr-'+version)
            if subprocess.call([os.path.join(mpfr_dir,'configure'),
                                '--prefix='+dir_name,'--with-gmp='+dir_name],cwd=mpfr_dir):
                raise Exception('mpfr failed to configure')
            if subprocess.call(['make'],cwd=mpfr_dir):
                raise Exception('mpfr failed to make')
            if subprocess.call(['make','install'],cwd=mpfr_dir):
                raise Exception('mpfr failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
