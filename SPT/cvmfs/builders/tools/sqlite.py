"""SQLite build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

# if version >= key, year = value
years = {'3080300':'2014',
         '3080800':'2015'
        }

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'lib','libsqlite3.so')):
        print('installing sqlite version',version)
        name = 'sqlite-autoconf-'+str(version)+'.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            path = os.path.join(tmp_dir,name)
            y = None
            for v in sorted(years):
                if version >= v:
                    y = years[v]
            if y is None:
                raise Exception('cannot find version')
            url = os.path.join('http://www.sqlite.org',y,name)
            wget(url,path)
            unpack(path,tmp_dir)
            sqlite_dir = os.path.join(tmp_dir,'sqlite-autoconf-'+str(version))

            mod_env = dict(os.environ)
            mod_env['CFLAGS'] = '-I'+os.path.join(dir_name,'include')
            if subprocess.call([os.path.join(sqlite_dir,'configure'),
                                '--prefix='+dir_name],cwd=sqlite_dir,env=mod_env):
                raise Exception('sqlite failed to configure')
            if subprocess.call(['make'],cwd=sqlite_dir,env=mod_env):
                raise Exception('sqlite failed to make')
            if subprocess.call(['make','install'],cwd=sqlite_dir,env=mod_env):
                raise Exception('sqlite failed to install')
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
