"""readline build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libreadline.so')):
        print('installing readline version',version)
        name = 'readline-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://ftp.gnu.org/gnu/readline',name)
            wget(url,path)
            unpack(path,tmp_dir)
            readline_dir = os.path.join(tmp_dir,'readline-'+version)
            if subprocess.call([os.path.join(readline_dir,'configure'),
                                '--prefix',dir_name],cwd=readline_dir):
                raise Exception('readline failed to configure')
            if subprocess.call(['make'],cwd=readline_dir):
                raise Exception('readline failed to make')
            if subprocess.call(['make','install'],cwd=readline_dir):
                raise Exception('readline failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
