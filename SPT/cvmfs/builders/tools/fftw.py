"""fftw build/install"""

import os
import subprocess
import tempfile
import shutil
import copy

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libfftw3l.so')):
        print('installing fftw version',version)
        name = 'fftw-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://www.fftw.org',name)
            wget(url,path)
            fftw_dir = os.path.join(tmp_dir,'fftw-'+version)
            mod_env = copy.deepcopy(os.environ)
            mod_env['CC'] = 'cc -mtune=generic'
            for options in ('--enable-float','--enable-long-double',None):
                if os.path.exists(fftw_dir):
                    shutil.rmtree(fftw_dir)
                unpack(path,tmp_dir)
                cmd = [os.path.join(fftw_dir,'configure'),'--prefix',
                       dir_name,'--enable-shared','--enable-threads']
                if options:
                    cmd += options.split(' ')
                if subprocess.call(cmd, env=mod_env, cwd=fftw_dir):
                    raise Exception('fftw failed to configure')
                if subprocess.call(['make'],cwd=fftw_dir):
                    raise Exception('fftw failed to make')
                if subprocess.call(['make','install'],cwd=fftw_dir):
                    raise Exception('fftw failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
