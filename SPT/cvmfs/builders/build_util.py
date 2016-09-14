# build utilities

import os
import subprocess
import shutil
from functools import partial

def get_module(name, class_name='build'):
    """Import module"""
    x = __import__(name,globals(),locals(),[class_name])
    return (getattr(x,class_name))

def get_tools():
    """Get all tools, calling the `versions` function"""
    root_dir = os.path.join(os.path.dirname(__file__),'tools')
    tools = {}
    for module in os.listdir(root_dir):
        if module.startswith('.'):
            continue
        if module.endswith('.py') and module != '__init__.py':
            tmp = os.path.splitext(module)[0]
            tools[tmp] = get_module('tools.'+tmp,'versions')()
        elif os.path.isdir(os.path.join(root_dir,module)):
            tools[module] = get_module('tools.'+module,'versions')()
    return tools

def wget(src, dest, retry=1):
    for i in range(1,retry+1):
        if not subprocess.call(['wget','-nv','-t','5','-O',dest,src]):
            return
        if i >= retry:
            raise Exception('wget failed: %s %s'%(src,dest))

def wget_recursive(src, dest):
    if subprocess.call(['wget','-nv','-N','-t','5','-P',dest,'-r','-l','1','-A','*.i3*','-nd',src]):
        raise Exception('wget_recursive failed: %s %s'%(src,dest))

def rsync(src,dest,flags='-a'):
    cmd = ['rsync']
    if flags:
        cmd += flags
    cmd += [src,dest]
    if subprocess.call(cmd):
        raise Exception('rsync failed: %s'%' '.join(cmd))

def unpack(src,dest,flags=['-zx']):
    cmd = ['tar']
    if flags:
        cmd += flags
    cmd += ['-f',src,'-C',dest]
    if subprocess.call(cmd):
        raise Exception('unpack failed: %s'%' '.join(cmd))

def unpack_bz2(src,dest,flags=['-jx']):
    cmd = ['tar']
    if flags:
        cmd += flags
    cmd += ['-f',src,'-C',dest]
    if subprocess.call(cmd):
        raise Exception('unpack failed: %s'%' '.join(cmd))

def unpack_xz(src,dest,flags=['-Jx']):
    cmd = ['tar']
    if flags:
        cmd += flags
    cmd += ['-f',src,'-C',dest]
    if subprocess.call(cmd):
        raise Exception('unpack failed: %s'%' '.join(cmd))

def unzip(src,dest,flags=['-oq']):
    cmd = ['unzip']
    if flags:
        cmd += flags
    cmd += [src,'-d',dest]
    if subprocess.call(cmd):
        raise Exception('unzip failed: %s'%' '.join(cmd))

def get_md5sum(path):
    try:
        import hashlib
        digest = hashlib.md5()
    except ImportError:
        import md5
        digest = md5.new()

    filed = open(path)
    buffer = filed.read(16384)
    while buffer:
        digest.update(buffer)
        buffer = filed.read(16384)
    filed.close()
    return digest.hexdigest()

def check_md5sum(path,md5sum=''):
    name = os.path.basename(path)
    cur_sum = get_md5sum(path)
    if cur_sum == md5sum:
        return
    if os.path.exists(md5sum):
        for line in open(md5sum):
            line = line.strip()
            if line:
                parts = line.split(' ')
                if name == parts[-1] and cur_sum == parts[0]:
                    return
    raise Exception('md5sum doesn\'t match')

def copy_src(src,dest):
    """Copy anything from src to dest"""
    try:
        os.makedirs(dest)
    except Exception:
        pass
    for p in os.listdir(src):
        if p.startswith('.'):
            continue
        path = os.path.join(src,p)
        if os.path.isdir(path):
            copy_src(path,os.path.join(dest,p))
        else:
            shutil.copy2(path,dest)

def load_env(dir_name):
    """Load the environment from dir/setup.sh"""
    p = subprocess.Popen(os.path.join(dir_name,'setup.sh'),
                         shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    output = p.communicate()[0]
    new_env = {}
    for line in output.split(';'):
        line = line.strip()
        if line:
            parts = line.split('=',1)
            name = parts[0].replace('export ','').strip()
            value = parts[1].strip(' "')
            os.environ[name] = value

class version_dict(dict):
    def __init__(self, handler, *args, **kwargs):
        self.handler = handler
        dict.__init__(self, *args, **kwargs)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self,key)
        except Exception:
            return partial(self.handler,version=key)

def get_fortran_compiler(version=77):
    """Get the best fortran compiler available."""
    if version == 77:
        for c in ('pgf77','g77','f77','gfortran'):
            if not subprocess.call(['which',c]):
                return c
    elif version == 90:
        for c in ('pgf90','gfortran'):
            if not subprocess.call(['which',c]):
                return c
    elif version == 95:
        for c in ('pgf95','gfortran'):
            if not subprocess.call(['which',c]):
                return c
    raise Exception('fortran compiler for version %s not found'%version)
