"""netcdf build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name, version=None):
    if not os.path.exists(os.path.join(dir_name, 'bin', 'ncdump')):
        print('installing netcdf version', version)
        name = 'netcdf-' + str(version) + '.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('ftp://ftp.unidata.ucar.edu/pub/netcdf/', name)
            wget(url, path)
            unpack(path, tmp_dir)
            netcdf_dir = os.path.join(tmp_dir, 'netcdf-' + version)
            if subprocess.call([os.path.join(netcdf_dir,' configure'),
                                '--prefix=' + dir_name], cwd = netcdf_dir):
                raise Exception('netcdf failed to configure')
            if subprocess.call(['make'], cwd = netcdf_dir):
                raise Exception('netcdf failed to make')
            if subprocess.call(['make','install'], cwd = netcdf_dir):
                raise Exception('netcdf failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
