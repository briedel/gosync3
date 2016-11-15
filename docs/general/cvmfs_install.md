To install cvmfs:

For RHEL:

```
yum install gawk fuse fuse-libs autofs attr gdb policycoreutils-python psmisc 
rpm -ivh https://ecsft.cern.ch/dist/cvmfs/cvmfs-config/cvmfs-config-default-1.2-2.noarch.rpm
RHEL6: rpm -ivh https://ecsft.cern.ch/dist/cvmfs/cvmfs-2.3.2/cvmfs-2.3.2-1.el6.x86_64.rpm
RHEL7: rpm -ivh https://ecsft.cern.ch/dist/cvmfs/cvmfs-2.3.2/cvmfs-2.3.2-1.el7.centos.x86_64.rpm
```

Ubuntu 12/14:

```
apt-get install gawk curl autofs attr gdb
curl -k -o cvmfs-keys_1.5-1_all.deb https://ecsft.cern.ch/dist/cvmfs/cvmfs-keys/cvmfs-keys_1.5-1_all.deb
dpkg -i cvmfs-keys_1.5-1_all.deb
curl -k -o cvmfs_2.2.2_amd64.deb https://ecsft.cern.ch/dist/cvmfs/cvmfs-2.2.2/cvmfs_2.2.2_amd64.deb
dpkg -i cvmfs_2.2.2_amd64.deb
usermod -a -G fuse cvmfs
```

In `/etc/cvmfs/default.local`:

```
CVMFS_REPOSITORIES=<your repo>
CVMFS_HTTP_PROXY='DIRECT' or '<address to your HTTP proxy>'
```

In `/etc/cvmfs/config.d/spt.opensciencegrid.org.conf`:

```
CVMFS_SERVER_URL="http://cvmfs.fnal.gov:8000/opt/spt;http://cvmfs.racf.bnl.gov:8000/opt/spt;http://cvmfs-egi.gridpp.rl.ac.uk:8000/cvmfs/spt.opensciencegrid.org;http://klei.nikhef.nl/cvmfs/spt.opensciencegrid.org;http://cvmfs02.grid.sinica.edu.tw/cvmfs/spt.opensciencegrid.org"
# this next line may or may not be necessary
CVMFS_PUBLIC_KEY=/etc/cvmfs/keys/opensciencegrid.org/opensciencegrid.org.pub
```

If you want to use autofs instead of static mounts:

* Ensure that `user_allow_other` is set/uncommented in `/etc/fuse.conf` (if it exists)
* Ensure that `/cvmfs /etc/auto.cvmfs` is added to `/etc/auto.master` 
* Run: `service autofs restart`

To check if thing are running:

* Run: `cvmfs_config chksetup`
* Check:  `/var/log/messages` or `/var/log/syslog`
Also try:
* `cvmfs_config umount`
* `ls /cvmfs/<your repo>`
