"""pkg-config build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','pkg-config')):
        print('installing pkg-config version',version)
        name = 'pkg-config-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('https://pkg-config.freedesktop.org/releases',name)
            wget(url,path)
            unpack(path,tmp_dir)
            pkg_config_dir = os.path.join(tmp_dir,'pkg-config-'+version)
            if subprocess.call([os.path.join(pkg_config_dir,'configure'),
                                '--prefix',dir_name,'--with-internal-glib'],cwd=pkg_config_dir):
                raise Exception('pkg-config failed to configure')
            if subprocess.call(['make'],cwd=pkg_config_dir):
                raise Exception('pkg-config failed to make')
            if subprocess.call(['make','install'],cwd=pkg_config_dir):
                raise Exception('pkg-config failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
