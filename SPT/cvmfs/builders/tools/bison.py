"""bison build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','bison')):
        print('installing bison version',version)
        name = 'bison-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('https://ftp.gnu.org/gnu/bison',name)
            wget(url,path)
            unpack(path,tmp_dir)
            bison_dir = os.path.join(tmp_dir,'bison-'+version)
            if subprocess.call([os.path.join(bison_dir,'configure'),
                                '--prefix',dir_name],cwd=bison_dir):
                raise Exception('bison failed to configure')
            if subprocess.call(['make'],cwd=bison_dir):
                raise Exception('bison failed to make')
            if subprocess.call(['make','install'],cwd=bison_dir):
                raise Exception('bison failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
