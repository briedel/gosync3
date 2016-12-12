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

## `generate_db.py`

<!-- This script should only be used if you need to generate a new database. It needs to be run as root -->

## `get_SMART_status.py`

## `get_drive_IDs.py`

