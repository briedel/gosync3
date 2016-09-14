"""isl build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack_bz2, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libisl.so')):
        print('installing isl version',version)
        name = 'isl-'+str(version)+'.tar.bz2'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://ftp.vim.org/languages/gcc/infrastructure',name)
            wget(url,path)
            unpack_bz2(path,tmp_dir)
            if version[-1] == 'a':
                isl_dir = os.path.join(tmp_dir,'isl-'+version[0:-1])
            else:
                isl_dir = os.path.join(tmp_dir,'isl-'+version)
            if subprocess.call([os.path.join(isl_dir,'configure'),
                                '--prefix='+dir_name,'--with-gmp-prefix='+dir_name],cwd=isl_dir):
                raise Exception('isl failed to configure')
            if subprocess.call(['make'],cwd=isl_dir):
                raise Exception('isl failed to make')
            if subprocess.call(['make','install'],cwd=isl_dir):
                raise Exception('isl failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
