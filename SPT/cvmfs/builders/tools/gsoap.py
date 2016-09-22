"""gsoap build/install"""

import os
import subprocess
import tempfile
import shutil

from distutils.version import LooseVersion
from build_util import wget, unzip, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','wsdl2h')):
        print('installing gsoap version',version)
        name = 'gsoap_'+str(version)+'.zip'
        try:
            tmp_dir = tempfile.mkdtemp()
            v = LooseVersion(version)
            version_short = ".".join(map(str, v.version[:2]))
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://downloads.sourceforge.net/project/gsoap2',
                               'gsoap-%s' % version_short,
                               name)
            wget(url,path)
            unzip(path,tmp_dir)
            gsoap_dir = os.path.join(tmp_dir,'gsoap-'+'.'.join(version.split('.')[:2]))
            if subprocess.call([os.path.join(gsoap_dir,'configure'),
                                '--prefix',dir_name,'--disable-static'],cwd=gsoap_dir):
                raise Exception('gsoap failed to configure')
            if subprocess.call(['make'],cwd=gsoap_dir):
                raise Exception('gsoap failed to make')
            if subprocess.call(['make','install'],cwd=gsoap_dir):
                raise Exception('gsoap failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
