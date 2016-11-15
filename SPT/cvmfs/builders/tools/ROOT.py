"""ROOT build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','root.exe')):
        print('installing ROOT version',version)
        name = 'root_v'+str(version)+'.source.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('https://root.cern.ch/download',name)
            wget(url,path)
            unpack(path,tmp_dir)
            root_dir = os.path.join(tmp_dir,'root-'+version)
            if subprocess.call([os.path.join(root_dir,'configure'),
                                '--prefix',dir_name],cwd=root_dir):
                raise Exception('gsl failed to configure')
            if subprocess.call(['make'],cwd=root_dir):
                raise Exception('gsl failed to make')
            if subprocess.call(['make','install'],cwd=root_dir):
                raise Exception('gsl failed to install')
        finally:
            shutil.rmtree(tmp_dir)