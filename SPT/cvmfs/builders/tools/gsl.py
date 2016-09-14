"""gsl build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libgsl.so')):
        print('installing gsl version',version)
        name = 'gsl-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('ftp://ftp.gnu.org/gnu/gsl',name)
            wget(url,path)
            unpack(path,tmp_dir)
            gsl_dir = os.path.join(tmp_dir,'gsl-'+version)
            if subprocess.call([os.path.join(gsl_dir,'configure'),
                                '--prefix',dir_name],cwd=gsl_dir):
                raise Exception('gsl failed to configure')
            if subprocess.call(['make'],cwd=gsl_dir):
                raise Exception('gsl failed to make')
            if subprocess.call(['make','install'],cwd=gsl_dir):
                raise Exception('gsl failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
