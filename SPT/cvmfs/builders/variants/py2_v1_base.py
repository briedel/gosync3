# build the /py2-v1 directory, for this OS

import os
from build_util import *

tools = get_tools()


def python_packages(dir_name):
    packages = ['setuptools==24.0.3', 'numpy==1.11.1', 'scipy==0.16.1',
                'readline==6.2.4.1',
                'ipython==5.0.0', 'jupyter==1.0.0', 'pyfits==3.0.7',
                'astropy==1.1.2', 'numexpr==2.5.2', 'Cython==0.24',
                'matplotlib==1.5.0', 'Sphinx==1.4.1', 
                'urwid==1.3.1', 'healpy==1.9.1', 'spectrum==0.6.1',
                'SQLAlchemy==1.0.13', 'PyYAML==3.11', 'ephem==3.7.6.0',
                'idlsave==1.0.0', 'ipdb==0.10.0', 'jsonschema==2.5.1'
                ]

    if os.environ['OS_ARCH'] == 'RHEL_5_x86_64':
        packages += ['pyOpenSSL==0.12']
    else:
        packages += ['pyOpenSSL==0.15.1']

    packages += ['pyzmq==15.2.0', 'tornado==4.3']

    for pkg in packages:
        tools['pip']['install'](pkg)

    # fails to install:
    # # gnuplot-py is special
    # tools['pip']['install']('http://downloads.sourceforge.net/project/gnuplot-py/Gnuplot-py/1.8/gnuplot-py-1.8.tar.gz')

    # fails to install:
    # # pyMinuit2 is special
    # tools['pip']['install']('https://github.com/jpivarski/pyminuit2/archive/1.1.0.tar.gz')

    # tables is special
    os.environ['HDF5_DIR'] = os.environ['SROOT']
    tools['pip']['install']('h5py==2.6.0')
    tools['pip']['install']('tables==3.2.3.1')
    del os.environ['HDF5_DIR']

    # pyfftw is special
    if 'CFLAGS' in os.environ:
        old_cflags = os.environ['CFLAGS']
    else:
        old_cflags = None
    os.environ['CFLAGS'] = '-I ' + os.path.join(os.environ['SROOT'], 'include')
    tools['pip']['install']('pyfftw==0.10.1')
    if old_cflags:
        os.environ['CFLAGS'] = old_cflags
    else:
        del os.environ['CFLAGS']


def create_os_specific_dirs(dir_name):
    # fill OS-specific directory with dirs
    for d in ('bin', 'etc', 'include', 'lib', 'libexec', 'man',
              'software', 'share', 'tools'):
        d = os.path.join(dir_name, d)
        if not os.path.exists(d):
            os.makedirs(d)
    # do symlinks
    for src, dest in (('lib', 'lib64'), ('bin', 'sbin')):
        dest = os.path.join(dir_name, dest)
        if not os.path.exists(dest):
            os.symlink(os.path.join(dir_name, src), dest)


def build(src, dest, **build_kwargs):
    """The main builder"""
    # first, make sure the base dir is there
    dir_name = os.path.join(dest, 'py2-v1')
    copy_src(os.path.join(src, 'py2-v1'), dir_name)

    # now, do the OS-specific stuff
    load_env(dir_name)
    if 'SROOT' not in os.environ:
        raise Exception('$SROOT not defined')
    dir_name = os.environ['SROOT']

    # fill OS-specific directory with dirs
    create_os_specific_dirs(dir_name)


    # install a temporary gcc in order to bootstrap clang
    if not os.path.exists(os.path.join(dir_name, 'bin', 'gcc')):
        del os.environ['CC']
        del os.environ['CXX']
        tools['gmp']['6.1.0'](dir_name)
        tools['mpfr']['3.1.4'](dir_name)
        tools['mpc']['1.0.3'](dir_name)
        tools['isl']['0.14'](dir_name)
        tools['m4']['1.4.17'](dir_name)
        tools['bison']['3.0.4'](dir_name)
        tools['flex']['2.6.0'](dir_name)
        tools['binutil']['2.26'](dir_name)
        tools['gcc']['5.3.0'](dir_name)
    
    tools['m4']['1.4.17'](dir_name)
    tools['xz']['5.2.2'](dir_name)
    tools['libtool']['2.4.6'](dir_name)
    tools['pkg-config']['0.29.1'](dir_name)
    tools['libffi']['3.2.1'](dir_name)
    tools['libarchive']['3.1.2'](dir_name)
    tools['libxml2']['2.9.2'](dir_name)
    tools['readline']['6.3'](dir_name)
    tools['sqlite']['3081002'](dir_name)
    tools['tcl_tk']['8.6.5'](dir_name)
    tools['python']['2.7.11'](dir_name)
    tools['cmake']['3.5.2'](dir_name)
    tools['zmq']['4.1.4'](dir_name)
    tools['bzip2']['1.0.6'](dir_name)
    tools['python']['2.7.11'](dir_name)
    tools['pip']['latest'](dir_name)
    tools['gsl']['2.1'](dir_name)
    tools['boost']['1.57.0'](dir_name)
    tools['openblas']['0.2.18'](dir_name)
    tools['cfitsio']['3.390'](dir_name)
    tools['fftw']['3.3.4'](dir_name)
    tools['healpix']['3.20'](dir_name)
    tools['hdf5']['1.8.17'](dir_name)
    tools['gsoap']['2.8.22'](dir_name)
    # tools['globus']['6.0.1470089956'](dir_name)
    tools['globus']['5.2.5'](dir_name)
    tools['png']['1.6.25'](dir_name)
    tools['freetype']['2.6.3'](dir_name)
    tools['netcdf']['4.4.0'](dir_name)
    tools['flac']['1.3.1'](dir_name)

    python_packages(dir_name)
