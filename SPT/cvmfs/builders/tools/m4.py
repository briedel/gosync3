"""m4 build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','m4')):
        print('installing m4 version',version)
        name = 'm4-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('https://ftp.gnu.org/gnu/m4',name)
            wget(url,path)
            unpack(path,tmp_dir)
            m4_dir = os.path.join(tmp_dir,'m4-'+version)
            if subprocess.call([os.path.join(m4_dir,'configure'),
                                '--prefix',dir_name],cwd=m4_dir):
                raise Exception('m4 failed to configure')
            if subprocess.call(['make'],cwd=m4_dir):
                raise Exception('m4 failed to make')
            if subprocess.call(['make','install'],cwd=m4_dir):
                raise Exception('m4 failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
