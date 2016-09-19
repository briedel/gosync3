"""openssl build/install"""

import os
import subprocess
import tempfile
import shutil
from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','openssl')):
        print('installing openssl version',version)
        name = 'openssl-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('https://www.openssl.org/source/',name)
            wget(url,path)
            unpack(path,tmp_dir)
            openssl_dir = os.path.join(tmp_dir,'openssl-'+version)
            if subprocess.call([os.path.join(openssl_dir,'config'),
                                '--prefix=%s' % dir_name, '--openssldir=%s' % dir_name, 'shared'],cwd=openssl_dir):
                raise Exception('openssl failed to configure')
            if subprocess.call(['make'],cwd=openssl_dir):
                raise Exception('openssl failed to make')
            if subprocess.call(['make','install'],cwd=openssl_dir):
                raise Exception('openssl failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
