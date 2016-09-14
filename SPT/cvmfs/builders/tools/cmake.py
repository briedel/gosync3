"""cmake build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','cmake')):
        print('installing cmake version',version)
        name = 'cmake-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://www.cmake.org/files/v'+'.'.join(version.split('.')[:2]),name)
            wget(url,path)
            unpack(path,tmp_dir)
            cmake_dir = os.path.join(tmp_dir,'cmake-'+version)
            if subprocess.call([os.path.join(cmake_dir,'configure'),
                                '--prefix='+dir_name],cwd=cmake_dir):
                raise Exception('cmake failed to configure')
            if subprocess.call(['make'],cwd=cmake_dir):
                raise Exception('cmake failed to make')
            if subprocess.call(['make','install'],cwd=cmake_dir):
                raise Exception('cmake failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
