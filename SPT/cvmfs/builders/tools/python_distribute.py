"""Python distribute build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if subprocess.call([os.path.join(dir_name,'bin','python'),
                        '-c','import setuptools']):
        print('installing python_distribute version',version)
        name = 'distribute-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://pypi.python.org/packages/source/d/distribute/',name)
            wget(url,path)
            unpack(path,tmp_dir)
            distribute_dir = os.path.join(tmp_dir,'distribute-'+version)
            if subprocess.call([os.path.join(dir_name,'bin','python'),
                                os.path.join(distribute_dir,'setup.py'),
                                'build'], cwd=distribute_dir):
                raise Exception('python_distribute failed to configure')
            if subprocess.call([os.path.join(dir_name,'bin','python'),
                                os.path.join(distribute_dir,'setup.py'),
                                'install','--prefix',dir_name],
                               cwd=distribute_dir):
                raise Exception('python_distribute failed to make')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
