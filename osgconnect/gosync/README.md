gosync
------

This is a replacement for gosync. It splits the monolithic gosync script into several smaller scripts that perform the specific functions required. There is a general set of utility functions that allow access to the data in Globus Nexus API and transformation of the data retrieved from the API.

`gs_dump_osg_connect_groups.py`
===============================

This script allows the user to retrieve the information about each individual group connect with the `connect` user in the Globus Nexus API. It replaces `./gosync -q --nw group list`. 

The code an simply be run using the `gosync.conf` configuration file, which will cause it dump the entire information for all groups connect to the `connect` in Globus Nexus, including duke-connect and atlas-connect. 

There are additional code specific options:

* `--config`: Configuration file to be used. Default is `gosync.conf`
* `-v/--verbosity`: Set the logging verbosity. Currently not fully implemented
* `--format`: What format the output file should have. Can be a list of formats, or a single format. The supported formats are `html`, `json`, `xml`, `csv`, and `text`. Default is `html`.
* `-o/--outfile`: Output file name. Default is `None`. 
* `--baseurl`: URL to be used to see osg connect groups. Default is `None`. If not given it will default to what is in the configuration file.
* `--group`: Single group to retrieve. Default is `None`.
* `--filters`: Filter for the group prefixes. For example `osg.` and `project.osg.` are the filters to get groups only associated with osg connect. Default is `None`. If `None`, the filters from the configuration file will be used, i.e. `project.osg.`, `osg.`, `duke.`, `atlas.`.

`gs_dump_users.py`
==================

This script produces a `/etc/passwd`-style file from users in Globus that are associated with osg connect and provisions the users, including home and stash dir, ssh keys, and email forwarding. 

To ensure no duplicate usernames and user ids. The script parses the currently present `/etc/passwd`-style file and extracts the usernames and user ids. It will fail in case a duplicate username is supposed to be provisioned. New user ids are chosen at random between 10000 and 65001. In case an already used user ids is chosen, a new one will be selected.

TODOs: Check about atlas-connect users about stash. 

* `--config`: Configuration file to be used. Default is `gosync.conf`
* `-v/--verbosity`: Set the logging verbosity. Currently not fully implemented
* `--onlynew`: Only consider new users
* `--onlyupdate`: Only update exsisting users
* `--onlyuser`: Only consider a single user. Use username.
* `--forceupdate`: Force the update.
* `--filters`: Filter for the group prefixes. For example `osg.` and `project.osg.` are the filters to get groups only associated with osg connect. Default is `None`. If `None`, the filters from the configuration file will be used, i.e. `project.osg.`, `osg.`, `duke.`, `atlas.`.

`gs_dump_groups.py`
==================

This script produces a `/etc/group`-style file from groups in Globus that are associated with osg connect and provisions the group. 

The script parses the currently present `/etc/group`-style file and extracts the group name and group ids. It will generate the group id has a hash of the group name. 

TODOs: Check about atlas-connect users about stash. 

* `--config`: Configuration file to be used. Default is `gosync.conf`
* `-v/--verbosity`: Set the logging verbosity. Currently not fully implemented
* `--onlynew`: Only consider new users
* `--onlyupdate`: Only update exsisting users
* `--onlyuser`: Only consider a single user. Use username.
* `--forceupdate`: Force the update.
* `--filters`: Filter for the group prefixes. For example `osg.` and `project.osg.` are the filters to get groups only associated with osg connect. Default is `None`. If `None`, the filters from the configuration file will be used, i.e. `project.osg.`, `osg.`, `duke.`, `atlas.`.

Config
======