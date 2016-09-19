"""tcl/tk build/install"""

import os
import subprocess
import tempfile
import shutil

from build_util import wget, unpack, version_dict

def install(dir_name,version=None):
    if not os.path.exists(os.path.join(dir_name,'bin','tclsh')):
        print('installing tcl/tk version',version)
        tcl_name = 'tcl'+version+'-src.tar.gz'
        tk_name = 'tk'+version+'-src.tar.gz'
        try:
            tmp_dir = tempfile.mkdtemp()
            tcl_path = os.path.join(tmp_dir,tcl_name)
            tcl_url = os.path.join('http://downloads.sourceforge.net/project/tcl/Tcl/',version,tcl_name)
            tk_path = os.path.join(tmp_dir,tk_name)
            tk_url = os.path.join('http://downloads.sourceforge.net/project/tcl/Tcl/',version,tk_name)
            wget(tcl_url,tcl_path)
            wget(tk_url,tk_path)
            unpack(tcl_path,tmp_dir)
            unpack(tk_path,tmp_dir)
            tcl_dir = os.path.join(tmp_dir,'tcl'+str(version),'unix')
            if subprocess.call([os.path.join(tcl_dir,'configure'),'--prefix',
                                dir_name,'--disable-shared'],cwd=tcl_dir):
                raise Exception('tcl failed to configure')
            if subprocess.call(['make'],cwd=tcl_dir):
                raise Exception('tcl failed to make')
            if subprocess.call(['make','install','install-libraries'],cwd=tcl_dir):
                raise Exception('tcl failed to install')
            tk_dir = os.path.join(tmp_dir,'tk'+str(version),'unix')
            if not subprocess.call([os.path.join(tk_dir,'configure'),'--prefix',
                                    dir_name],cwd=tk_dir):
                if not subprocess.call(['make'],cwd=tk_dir):
                    subprocess.call(['make','install'],cwd=tk_dir)
            os.symlink(os.path.expandvars('$SROOT/bin/tclsh'+'.'.join(version.split('.')[:2])),
                       os.path.expandvars('$SROOT/bin/tclsh'))
        finally:
            shutil.rmtree(tmp_dir)

def versions():
    return version_dict(install)
