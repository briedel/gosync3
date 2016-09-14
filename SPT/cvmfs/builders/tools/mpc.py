"""mpc build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libmpc.so')):
        print('installing mpc version',version)
        name = 'mpc-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('https://ftp.gnu.org/gnu/mpc',name)
            wget(url,path)
            unpack(path,tmp_dir)
            if version[-1] == 'a':
                mpc_dir = os.path.join(tmp_dir,'mpc-'+version[0:-1])
            else:
                mpc_dir = os.path.join(tmp_dir,'mpc-'+version)
            if subprocess.call([os.path.join(mpc_dir,'configure'),
                                '--prefix='+dir_name,'--with-mpfr='+dir_name],cwd=mpc_dir):
                raise Exception('mpc failed to configure')
            if subprocess.call(['make'],cwd=mpc_dir):
                raise Exception('mpc failed to make')
            if subprocess.call(['make','install'],cwd=mpc_dir):
                raise Exception('mpc failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
