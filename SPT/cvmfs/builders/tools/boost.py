"""boost build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

try:
    import multiprocessing
    cpu_cores = multiprocessing.cpu_count()
except ImportError:
    cpu_cores = 1

def install(dir_name,version=None,for_clang=False):
    if not os.path.exists(os.path.join(dir_name,'lib','libboost_python.so')):
        if for_clang:
            print('installing boost version',version,' (for clang/c++14)')
        else:
            print('installing boost version',version)
        name = 'boost_'+version.replace('.','_')+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            url = os.path.join('http://downloads.sourceforge.net/project/boost/boost',version,name)
            wget(url,path)
            unpack(path,tmp_dir)
            boost_dir = os.path.join(tmp_dir,'boost_'+version.replace('.','_'))
            if version == "1.61.0":
                wget("https://github.com/scopeInfinity/iostreams/commit/61a91325d936b0a9e6baaed6c974d0808e166822.patch",
                      os.path.join(boost_dir,"61a91325d936b0a9e6baaed6c974d0808e166822.patch"))
                subprocess.call(["patch", "-p2", "<", "61a91325d936b0a9e6baaed6c974d0808e166822.patch"], cwd=boost_dir)
            print(os.environ["PYTHONPATH"], os.environ["LD_LIBRARY_PATH"])
            if for_clang:
                if subprocess.call([os.path.join(boost_dir,'bootstrap.sh'),
                                    '--prefix='+dir_name,'--with-toolset=clang'],cwd=boost_dir):
                    raise Exception('boost failed to bootstrap')
                if subprocess.call([os.path.join(boost_dir,'b2'),'install','-j'+str(cpu_cores),'toolset=clang','cxxflags="-std=c++14"'],cwd=boost_dir):
                    raise Exception('boost failed to b2 install')
            else:
                if subprocess.call([os.path.join(boost_dir,'bootstrap.sh'),
                                    '--prefix='+dir_name],cwd=boost_dir):
                    raise Exception('boost failed to bootstrap')
                if subprocess.call([os.path.join(boost_dir,'b2'),'install','-j'+str(cpu_cores), 'cxxflags="-std=c++11"'],cwd=boost_dir):
                    raise Exception('boost failed to b2 install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
