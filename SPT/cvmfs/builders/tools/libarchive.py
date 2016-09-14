"""libarchive build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libarchive.so')):
        print('installing libarchive version',version)
        name = 'libarchive-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://www.libarchive.org/downloads',name)
            wget(url,path)
            unpack(path,tmp_dir)
            libarchive_dir = os.path.join(tmp_dir,'libarchive-'+version)
            if subprocess.call([os.path.join(libarchive_dir,'configure'),
                                '--prefix',dir_name,'--disable-bsdtar',
                                '--disable-bsdcpio','--without-xml2',
                                '--without-expat'],cwd=libarchive_dir):
                raise Exception('libarchive failed to configure')
            if subprocess.call(['make'],cwd=libarchive_dir):
                raise Exception('libarchive failed to make')
            if subprocess.call(['make','install'],cwd=libarchive_dir):
                raise Exception('libarchive failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
