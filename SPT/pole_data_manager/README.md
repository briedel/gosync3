# Pole Data Manager for SPT

These scripts copy data from a directory (a mountpoint would be better) on the storage control node to a free space on both the primary and copy storage array and register the files in a SQLite database. 

## `data_manager.py`

Main script that does the copying and registering of the data that should be run as a cron job. All inputs are defined in a config file, which can be defined through the CLI option `--config`. The script requires that the the following configuration parameters are set:

* `FilenameDB`: File name of the SQLite DB
* `BufferLocation`: Location where the files should be copied from
* `Extension`: File extension to look for in the buffer location
* `DiskMountPoints`: Mountpoint of disks

A sample working configuration is present in the repository, see `basic_data_manager.config`. 

The script works as follows. It will check the database which disks are currently in use, i.e. which ones still have sufficient space on them to have new data copied to them. The database keeps tracks of disk statistics (space available, space used, etc.) and which disks have been previously used. Once a primary and back up disk have been designed, the script `glob`s the `BufferLocation` for any files with the given `Extension`. The script then checks the database whether the file has already been copied and registered or not. If it hasn't been copied and/or registered, the file will be copied again. To ensure that the copy was successful, the SHA512 will be calculated before and after the copy. If the file has been successfully copied, it will be registered into the database and deleted from the buffer. 

Possible Additions:

* Ping winterovers that a file was not successfully copied
* Ping winterovers if no new file in some time frame has been copied or added to the DB

## `generate_db.py`

This is an auxliary script that may be needed to build the database. It will generate a database with only the information about the drives. The drive information should be stored in a text file with a format similar to `disk-map` or `disk-map-test`. These two files have three columns `P01 ZA12JCHM 0x5000c500858bfea7`, where `P01` is the SPT drive identifier, `ZA12JCHM` is the drive serial number, `0x5000c500858bfea7` is the logical drive ID. The first two columns are on the drive, the second and third column are provided by `smartctl`.

## `get_SMART_status.py`

NOTE: This script is incomplete. It still needs code to notify the winterovers of a disk failure. 

This script will check the SMART status of the drives. It requires root privileges to run. 

## `get_drive_IDs.py`

This script generates the mapping from drive serial number to logical drive ID through calls to `smartctl`.  It requires root privileges to run. 