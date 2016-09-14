"""libtool build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','libtool')):
        print('installing libtool version',version)
        name = 'libtool-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('ftp://ftp.gnu.org/gnu/libtool',name)
            wget(url,path)
            unpack(path,tmp_dir)
            libtool_dir = os.path.join(tmp_dir,'libtool-'+version)
            if subprocess.call([os.path.join(libtool_dir,'configure'),
                                '--prefix',dir_name],
                               cwd=libtool_dir):
                raise Exception('libtool failed to configure')
            if subprocess.call(['make'],cwd=libtool_dir):
                raise Exception('libtool failed to make')
            if subprocess.call(['make','install'],cwd=libtool_dir):
                raise Exception('libtool failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
