#!/usr/bin/env python
from __future__ import print_function

import os
import sys
import logging
import sqlite3
import hashlib
import shutil
import ConfigParser as configparser

from collections import namedtuple
from optparse import OptionParser

parser = OptionParser()
parser.add_option("--config", dest="config_file", default="data_manager.conf",
                  help="Scripts config file", metavar="FILE")
(options, args) = parser.parse_args()

def check_new_files(, path_to_new_files, ):
    """
    Runs glob on a data buffer directory and checks with 
    the data base whether a file has already been copied
    or not

    :param db: sqlite3 database object
    :param path_to_new_files: Path to data buffer dir
    :return: List of files that need to be copied to 
             disk and added to file catalog
    """
    cursor = db.cursor()
    files = glob.glob(path_to_new_files)
    new_files = []
    if files:
        for file in files.sort():
            file = os.path.basename(file)
            cursor.execute("SELECT * FROM files WHERE filename = '{0}'".format(file))
            if cursor.fetchall():
                continue
            else:
                new_files.append(file)
    return new_files

def copy_files(db, filename, primary_disk, copy_disk):
    """
    Copies files to the primary and copy disk array,
    gathers all information needed to add the file to
    the DB, and add files to file file catalog

    :param db: sqlite3 database object
    :param filename: Absolute path of file to be copied
    :param primary_disk: Identifier for primary disk to be used
    :param copy_disk: 
    """
    # Gathering file info
    filesize, hash = get_file_info(filename)
    # Copying with metadata intact
    shutil.copy2(file, "/spt_disks/{0}".format(primary_disk))
    shutil.copy2(file, "/spt_disks/{0}".format(copy_disk))
    # Making sure the files have been copied successfully
    filesize_primary, hash_primary = get_file_info(os.path.join("/spt_disks/{0}".format(primary_disk), file))
    filesize_copy, hash_copy = get_file_info(os.path.join("/spt_disks/{0}".format(copy_disk), file))
    # Raising hell if they haven't
    if filesize != filesize_primary or hash != hash_primary:
        logging.fatal("Copying to primary disk failed. " +\
                      "Difference in filesize is {filesize}. ".format(filesize=filesize - filesize_primary) +\
                      "The hash of the file was {hash}. ".format(hash=hash) +\
                      "The hash on the primary is {hash_primary}. ".format(hash_primary=hash_primary) +\
                      "The hash on the copy is {hash_copy}.".format(hash_copy=hash_copy))
        raise RuntimeError("Copying to primary disk failed")
    elif filesize != filesize_copy or hash != hash_copy:
        logging.fatal("Copying to copy disk failed. " +\
                      "Difference in filesize is {filesize}. ".format(filesize=filesize - filesize_primary) +\
                      "The hash of the file was {hash}. ".format(hash=hash) +\
                      "The hash on the primary is {hash_primary}. ".format(hash_primary=hash_primary) +\
                      "The hash on the copy is {hash_copy}.".format(hash_copy=hash_copy))
        raise RuntimeError("Copying to copy disk failed")
    else:
        # If file copied successfully. Add info to DB
        db.cursor()
        cursor.execute("""
                       INSERT INTO FILE (filename, checksum, filesize, disk_primary, disk_copy) 
                       VALUES ('{name}', '{checksum}', '{filesize}','{disk_primary}', '{disk_copy}')
                       """.format(name=os.path.basename(), checksum=hash,filesize=filesize,
                                  ))


def get_file_info(file):
    """
    Getting the info for DB

    :return: Tuple of the filesize and sha512 hash
    """
    filesize = os.stat(file)
    sha512hash = sha512sum(file)
    return filesize, sha512hash

def sha512sum(file, blocksize=65536):
    """
    Calculating the sha512 checksum of a file
    bit-by-bit

    :param file: File path
    :param blocksize: How much of the file should 
                      read in at a time
    :return: Sting representing the hex digest of the hash
    """
    hasher = hashlib.sha512()
    with open(file, "rb") as file:
        for block in iter(lambda: file.read(blocksize), ""):
            hash.update(block)
    return hash.hexdigest()

def get_useable_disk(db):
    """
    Get disks that should be used

    :param db: sqlite3 database object
    :return: List with the primary and copy disk label
    """
    cursor = db.cursor()
    cursor.execute("SELECT label FROM disks WHERE previously_used = 'True'") 
    results = cursor.fetchall()
    if results:
        if len(results) == 2:
            results.sort()
            # We should be on the same disk number for primary and copy
            if results[0][1:] == results[1][1:]
                return results
            else:
                logging.fatal("The disk number for primary and copy don't match. " +\
                              "That should not be possible. Something went wrong in the DB.")
                raise RuntimeError()
        elif len(results) > 2:
            logging.fatal("Too many active disks.")
            raise RuntimeError()
        else:
            logging.fatal("Not enough disks.")
            raise RuntimeError()
    else:
        logging.fatal("Cannot find usable disk.")
        raise RuntimeError()

def mark_disk_full(db, primary_disk, copy_disk):
    cursor = db.cursor()
    cursor.execute("SELECT label FROM disks WHERE previously_used = 'True'") 

def get_new_disk():

def run():
    with sqlite3.connect("spt_data_management.db") as db:
        primary_disk, copy_disk = get_useable_disk(db)
        new_files = check_new_files()
        if new_files:
            logging.info("No new files. Exiting")
            sys.exit()
        disk_stats_primary = os.statvfs("/spt_disks/{0}".format(primary_disk))
        disk_stats_copy = os.statvfs("/spt_disks/{0}".format(copy_disk))
        freespace_primary = disk_stats_primary.f_bavail * disk_stats_primary.f_frsize
        freespace_copy = disk_stats_copy.f_bavail * disk_stats_copy.f_frsize
        for file in new_files:
            if freespace < os.stat(file).st_size:
                # mark_disk_full(db, primary_disk, copy_disk)
                disk_serial_no, disk_logical_id = get_new_disk(db)
            else:
                copy_file_to_disks(file)
        update_disk(db, primary_disk, copy_disk)



# class DataManager(object):
#     def __init__(self, config = None):
#         if config:
#             self.config = config
#         else:
#             raise RuntimeError("No config object provided")
#         self.db = 
#         self.disk
#         self.

#     def get_useable_disk(self):



#     def check_new_files(self):


def main():
    # if not os.path.exists(options.config_file):
    #     raise RuntimeError("Config file {} does not exist".format(options.config_file))
    # config = configparser.ConfigParser()
    # config.read(options.config_file)
    run()

if __name__ == "__main__":
    main()