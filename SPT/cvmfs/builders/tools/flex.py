"""flex build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','flex')):
        print('installing flex version',version)
        name = 'flex-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://downloads.sourceforge.net/project/flex/',name)
            wget(url,path)
            unpack(path,tmp_dir)
            flex_dir = os.path.join(tmp_dir,'flex-'+version)
            if subprocess.call([os.path.join(flex_dir,'configure'),
                                '--prefix='+dir_name],cwd=flex_dir):
                raise Exception('flex failed to configure')
            if subprocess.call(['make'],cwd=flex_dir):
                raise Exception('flex failed to make')
            if subprocess.call(['make','install'],cwd=flex_dir):
                raise Exception('flex failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
