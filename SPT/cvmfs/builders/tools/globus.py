"""globus build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def get_url(v):
    if v[0] == '5':
        return os.path.join('http://toolkit.globus.org/ftppub/gt5/',v[:3],v,'installers','src','gt'+v+'-all-source-installer.tar.gz')
    elif v[0] == '6':
        return os.path.join('http://toolkit.globus.org/ftppub/gt6/installers/src/','globus_toolkit-'+v+'.tar.gz')
    else:
        raise Exception('unknown version')

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','globus-url-copy')):
        print('installing globus version',version)
        url = get_url(version)
        name = os.path.basename(url)
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            wget(url,path)
            unpack(path,tmp_dir)
            globus_dir = os.path.join(tmp_dir,name.rsplit('.',2)[0])
            if int(version[0]) <= 5:
#                if subprocess.call(['cpanm','--local-lib',dir_name,
#                                    'Archive::Tar','Compress::Zlib','Digest::MD5',
#                                    'File::Spec','IO::Zlib','Pod::Parser',
#                                    'Test::Simple','XML::Parser']):
#                    raise Exception('failed to install globus perl modules')
                if subprocess.call([os.path.join(globus_dir,'configure'),
                                    '--prefix',dir_name],cwd=globus_dir):
                    raise Exception('globus failed to configure')
                if subprocess.call(['make','gpt','globus-data-management-client'],cwd=globus_dir):
                    raise Exception('globus failed to make')
            elif int(version[0]) >= 6:
                if subprocess.call([os.path.join(globus_dir,'configure'),
                                    '--disable-gram5','--disable-myproxy',
                                    '--prefix',dir_name],cwd=globus_dir):
                    raise Exception('globus failed to configure')
                if subprocess.call(['make'],cwd=globus_dir):
                    raise Exception('globus failed to make')
            if subprocess.call(['make','install'],cwd=globus_dir):
                raise Exception('globus failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
