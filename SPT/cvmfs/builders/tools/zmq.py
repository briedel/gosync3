"""zmq build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libzmq.so')):
        print('installing zmq version',version)
        name = 'zeromq-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://download.zeromq.org',name)
            wget(url,path)
            unpack(path,tmp_dir)
            zmq_dir = os.path.join(tmp_dir,'zeromq-'+version)
            if subprocess.call([os.path.join(zmq_dir,'configure'),
                                '--prefix',dir_name,'--without-libsodium'],cwd=zmq_dir):
                raise Exception('zmq failed to configure')
            if subprocess.call(['make'],cwd=zmq_dir):
                raise Exception('zmq failed to make')
            if subprocess.call(['make','install'],cwd=zmq_dir):
                raise Exception('zmq failed to install')
            
            # the c++ bindings
            url = 'https://raw.githubusercontent.com/zeromq/cppzmq/master/zmq.hpp'
            path = os.path.join(dir_name,'include','zmq.hpp')
            wget(url,path)
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
