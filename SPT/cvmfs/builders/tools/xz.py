"""xz build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','xz')):
        print('installing xz version',version)
        name = 'xz-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://tukaani.org/xz',name)
            wget(url,path)
            unpack(path,tmp_dir)
            xz_dir = os.path.join(tmp_dir,'xz-'+version)
            if subprocess.call([os.path.join(xz_dir,'configure'),
                                '--prefix',dir_name],cwd=xz_dir):
                raise Exception('xz failed to configure')
            if subprocess.call(['make'],cwd=xz_dir):
                raise Exception('xz failed to make')
            if subprocess.call(['make','install'],cwd=xz_dir):
                raise Exception('xz failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
