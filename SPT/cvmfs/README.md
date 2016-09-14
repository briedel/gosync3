# cvmfs
Scripts to build the CVMFS repository for SPT.

## Build

To build all variants at once:

`cd builders;./build.py --dest /cvmfs/spt.opensciencegrid.org --src ../spt.opensciencegrid.org`

Or you can select a variant to build:

`cd builders;./build.py --dest /cvmfs/spt.opensciencegrid.org --src ../spt.opensciencegrid.org --variant py2_v1`