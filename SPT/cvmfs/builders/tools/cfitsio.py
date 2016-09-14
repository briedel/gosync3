"""cfitsio build/install"""

import os
import subprocess
import tempfile
import shutil
import copy

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libcfitsio.so')):
        print('installing cfitsio version',version)
        name = 'cfitsio'+version.replace('.','')+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('ftp://heasarc.gsfc.nasa.gov/software/fitsio/c',name)
            wget(url,path)
            unpack(path,tmp_dir)
            cfitsio_dir = os.path.join(tmp_dir,'cfitsio')
            mod_env = copy.deepcopy(os.environ)
            mod_env['CFLAGS'] = '-fPIC'
            if subprocess.call([os.path.join(cfitsio_dir,'configure'),
                                '--prefix',dir_name,'--enable-sse2'],
                               env=mod_env, cwd=cfitsio_dir):
                raise Exception('cfitsio failed to configure')
            if subprocess.call(['make','shared'], env=mod_env,
                               cwd=cfitsio_dir):
                raise Exception('cfitsio failed to make')
            if subprocess.call(['make','install'], env=mod_env,
                               cwd=cfitsio_dir):
                raise Exception('cfitsio failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
