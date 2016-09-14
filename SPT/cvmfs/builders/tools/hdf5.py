"""hdf5 build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','h5ls')):
        print('installing hdf5 version',version)
        name = 'hdf5-'+str(version)+'.tar.bz2'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://www.hdfgroup.org/ftp/HDF5/releases/hdf5-'+version,'src',name)
            wget(url,path)
            unpack(path,tmp_dir,flags=['-xj'])
            hdf5_dir = os.path.join(tmp_dir,'hdf5-'+version)
            if subprocess.call([os.path.join(hdf5_dir,'configure'),
                                '--prefix',dir_name,'--disable-debug',
                                '--enable-cxx','--enable-production',
                                '--enable-strict-format-checks',
                                '--with-zlib=/usr'],cwd=hdf5_dir):
                raise Exception('hdf5 failed to configure')
            if subprocess.call(['make'],cwd=hdf5_dir):
                raise Exception('hdf5 failed to make')
            if subprocess.call(['make','install'],cwd=hdf5_dir):
                raise Exception('hdf5 failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
