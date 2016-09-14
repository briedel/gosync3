"""libxml2 build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libxml2.so')):
        print('installing libxml2 version',version)
        name = 'libxml2-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('ftp://xmlsoft.org/libxml2',name)
            wget(url,path)
            unpack(path,tmp_dir)
            libxml2_dir = os.path.join(tmp_dir,'libxml2-'+version)
            if subprocess.call([os.path.join(libxml2_dir,'configure'),
                                '--prefix',dir_name,'--without-python'],
                               cwd=libxml2_dir):
                raise Exception('libxml2 failed to configure')
            if subprocess.call(['make'],cwd=libxml2_dir):
                raise Exception('libxml2 failed to make')
            if subprocess.call(['make','install'],cwd=libxml2_dir):
                raise Exception('libxml2 failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
