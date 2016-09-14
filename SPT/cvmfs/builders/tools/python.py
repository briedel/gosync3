"""Python build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','python')):
        print('installing python version',version)
        name = 'Python-'+str(version)+'.tgz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://www.python.org/ftp/python',version,name)
            wget(url,path)
            unpack(path,tmp_dir)
            python_dir = os.path.join(tmp_dir,'Python-'+version)
            if subprocess.call([os.path.join(python_dir,'configure'),
                                '--prefix',dir_name,'--enable-shared']
                               ,cwd=python_dir):
                raise Exception('python failed to configure')
            if subprocess.call(['make'],cwd=python_dir):
                raise Exception('python failed to make')
            if subprocess.call(['make','install'],cwd=python_dir):
                raise Exception('python failed to install')
            
            # check for modules
            for m in ('sqlite3','zlib','bz2','_ssl','_curses','readline'):
                if subprocess.call([os.path.join(dir_name,'bin','python'),
                                    '-c','import '+m]):
                    if os.path.exists(os.path.join(dir_name,'bin','python')):
                        os.remove(os.path.join(dir_name,'bin','python'))
                    raise Exception('failed to build with '+m+' support')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
