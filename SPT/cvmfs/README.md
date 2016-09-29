# Using an installed toolset


If software is installed at /path/to/software (i.e. you are reading this README
at /path/to/software/README), then run the following:

eval `/path/to/software/setup.sh`

This will set up your PATH, PYTHONPATH, LD_LIBRARY_PATH, and a few other things
appropriately. To have this occur on login, add the above line to your .profile,
.bash_profile, or .csh_profile, depending on which shell you use.

The setup.sh script will point your environment at the standard toolset, which
is currently py2-v1.

Current defined toolsets:

- py2-v1: Python 2.7.11-based tools
- py3-v1: Python 3.5.2-based tools


# cvmfs
Scripts to build the CVMFS repository for SPT.

## Build

To build all variants at once:

`cd builders;./build.py --dest /cvmfs/spt.opensciencegrid.org --src ../spt.opensciencegrid.org`

Or you can select a variant to build:

`cd builders;./build.py --dest /cvmfs/spt.opensciencegrid.org --src ../spt.opensciencegrid.org --variant py2_v1`
