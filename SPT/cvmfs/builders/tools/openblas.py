"""openblas build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libopenblas.so')):
        print('installing openblas version',version)
        name = 'v'+version+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('https://github.com/xianyi/OpenBLAS/archive',name)
            wget(url,path)
            unpack(path,tmp_dir)
            openblas_dir = os.path.join(tmp_dir,'OpenBLAS-'+version)
            makefile = os.path.join(openblas_dir,'Makefile.rule')
            data = open(makefile).read()
            f = open(makefile,'w')
            try:
                for line in data.split('\n'):
                    if 'DYNAMIC_ARCH' in line and line[0] == '#':
                        line = line[1:]
                    elif 'NO_AVX2' in line and line[0] == '#':
                        line = line[1:]
                    elif 'PREFIX' in line:
                        line = 'PREFIX = '+dir_name
                    elif 'NUM_THREADS' in line:
                        line = 'NUM_THREADS = 24'
                    f.write(line+'\n')
            finally:
                f.close()
            if subprocess.call(['make'],cwd=openblas_dir):
                raise Exception('openblas failed to make')
            if subprocess.call(['make','install'],cwd=openblas_dir):
                raise Exception('openblas failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
