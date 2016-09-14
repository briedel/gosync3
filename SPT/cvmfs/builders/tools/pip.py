"""pip build/install, and python packages with pip"""

import os
import subprocess
import tempfile
import shutil
import glob

from build_util import wget, version_dict

def install_pkg(package,prefix=None,upgrade=False):
    print('installing python package',package)
    options = ['--no-cache-dir', package,
              ]
    if prefix:
        options.extend(['--prefix',prefix])
    if upgrade:
        options.append('--upgrade')
    if subprocess.call(['pip','install']+options+[package]):
        raise Exception(package+' failed to install')

def install_pip(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','pip')):
        print('installing pip')
        name = 'get-pip.py'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            wget('https://bootstrap.pypa.io/get-pip.py',path)
            if subprocess.call([os.path.join(dir_name,'bin','python'),path,'--quiet']):
                raise Exception('pip failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install_pip,{'install':install_pkg})
