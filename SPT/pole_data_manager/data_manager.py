#!/usr/bin/env python
from __future__ import print_function

import os
import sys
import logging
import sqlite3
import hashlib
import shutil
import ast
import glob
import subprocess
import ConfigParser as configparser

from optparse import OptionParser

parser = OptionParser()
parser.add_option("--config", dest="config_file", default="data_manager.conf",
                  help="Scripts config file", metavar="FILE")
(options, args) = parser.parse_args()

logging.basicConfig(level=logging.DEBUG,
                    format=('%(asctime)s %(name)-12s '
                            '%(levelname)-8s %(message)s'),
                    datefmt='%Y-%m-%d %H:%M:%S')


def check_new_files(db, path_to_new_files):
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
    logging.debug("Found files {0}".format(files))
    new_files = []
    if files:
        files.sort()
        for file in files:
            file_basename = os.path.basename(file)
            logging.debug("Checking for file: {0}".format(file))
            cursor.execute("""SELECT * FROM files
                              WHERE filename = '{0}'""".format(file_basename))
            results = cursor.fetchall()
            if results:
                filesize, hash = get_file_info(file)
                if hash != results[0][2] and filesize != results[0][3]:
                    logging.critical(("File %s has the same basename as a "
                                      "previously copied file, but a "
                                      "different checksum and size. "
                                      "Please have a look."),
                                     file)
                    ping_winterovers()
                    raise RuntimeError("Issue with finding new files")
                elif hash != results[0][2]:
                    logging.critical(("File %s has the same basename as a "
                                      "previously copied file, but a "
                                      "different checksum. "
                                      "Please have a look."), file)
                    ping_winterovers()
                    sys.exit()
                    raise RuntimeError("Issue with finding new files")
                elif filesize != results[0][3]:
                    logging.critical(("File %s has the same basename as a "
                                      "previously copied file, but a "
                                      "different filesize. Please have a "
                                      "look."), file)
                    ping_winterovers()
                    raise RuntimeError("Issue with finding new files")
                else:
                    logging.info(("File {0} has the same basename, checksum, "
                                  "and filesize as a previously copied file. "
                                  "Ignoring file."), file)
                    continue
            else:
                new_files.append(file)
    logging.debug("Found new files: %s", new_files)
    return new_files


def copy_file_to_disks(config, db, filename, primary_disk, copy_disk):
    """
    Copies files to the primary and copy disk array,
    gathers all information needed to add the file to
    the DB, and add files to file file catalog

    :param config: Config parameters dict()
    :param db: sqlite3 database object
    :param filename: Absolute path of file to be copied
    :param primary_disk: Identifier for primary disk to be used
    :param copy_disk: Identifier for copy disk to be used
    """
    # Gathering file and disk info
    filesize, hash = get_file_info(filename)
    mountpoint = config["Data"]["diskmountpoints"]

    # Need that trailing /
    primary_disk_abspath = os.path.join(mountpoint, primary_disk, "")
    copy_disk_abspath = os.path.join(mountpoint, copy_disk, "")
    # Copying with metadata intact
    logging.debug("Copying to %s", primary_disk_abspath)
    shutil.copy2(filename, primary_disk_abspath)
    logging.debug("Copying to %s", copy_disk_abspath)
    shutil.copy2(filename, copy_disk_abspath)
    # Making sure the files have been copied successfully
    primary_disk_path = os.path.join(primary_disk_abspath,
                                     os.path.basename(filename))
    filesize_primary, hash_primary = get_file_info(primary_disk_path)
    copy_disk_path = os.path.join(copy_disk_abspath,
                                  os.path.basename(filename))
    filesize_copy, hash_copy = get_file_info(copy_disk_path)
    # Raising hell if they haven't
    if filesize != filesize_primary or hash != hash_primary:
        logging.fatal(("Copying to primary disk failed.\nDifference in "
                       "filesize is %d bytes. The hash of the file was %s.\n"
                       "The hash on the primary disk is %s. The hash on the "
                       "copy is %s."), filesize - filesize_primary, hash,
                      hash_primary,
                      hash_copy)
        raise RuntimeError()
    elif filesize != filesize_copy or hash != hash_copy:
        logging.fatal(("Copying to copy disk failed.\nDifference in "
                       "filesize is %d bytes. The hash of the file was %s.\n"
                       "The hash on the primary disk is %s. The hash on the "
                       "copy is %s."), filesize - filesize_copy, hash,
                      hash_primary,
                      hash_copy)
        raise RuntimeError()
    else:
        # If file copied successfully. Add info to DB
        cursor = db.cursor()
        cursor.execute("""
                       INSERT INTO files (filename, checksum, filesize,
                       disk_primary, disk_copy) VALUES ('{name}', '{checksum}',
                       '{filesize}','{disk_primary}', '{disk_copy}')
                       """.format(name=os.path.basename(filename),
                                  checksum=hash, filesize=filesize,
                                  disk_primary=primary_disk,
                                  disk_copy=copy_disk))


def get_file_info(file):
    """
    Getting the info for DB

    :return: Tuple of the filesize and sha512 hash
    """
    filesize = os.stat(file).st_size
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
    logging.debug("Hashing file %s", file)
    with open(file, "rb") as file:
        for block in iter(lambda: file.read(blocksize), ""):
            hasher.update(block)
    return hasher.hexdigest()


def get_useable_disk(db):
    """
    Get disks that should be used

    :param db: sqlite3 database object
    :return: List with the primary and copy disk label
    """
    cursor = db.cursor()
    cursor.execute("""SELECT label FROM disks
                      WHERE previously_used = 'True' AND full='False'""")
    results = cursor.fetchall()
    if results:
        if len(results) == 2:
            results.sort()
            # We should be on the same disk number for primary and copy
            if results[0][1:] == results[1][1:]:
                return results[0][0], results[1][0]
            else:
                logging.fatal(("The disk number for primary and copy don't "
                               "match. That should not be possible. Something "
                               "went wrong in the DB."))
                raise RuntimeError()
        elif len(results) > 2:
            logging.fatal("Too many active disks: %s", results)
            raise RuntimeError()
        else:
            logging.fatal("Not enough disks.")
            raise RuntimeError()
    else:
        logging.fatal("Cannot find usable disk.")
        raise RuntimeError()


def mark_disks_full(db, primary_disk, copy_disk):
    """
    Run two SQL commands to mark a disk as full

    :param db: sqlite3 database object
    :param primary_disk: Label for primary disk
    :param copy_disk: Label for copy disk
    """
    mark_disk_full(db, primary_disk)
    mark_disk_full(db, copy_disk)


def mark_disk_full(db, disk):
    cursor = db.cursor()
    cursor.execute("""UPDATE disks SET full='True', previously_used='False'
                      WHERE label = '{0}'""".format(disk))


def get_new_disks(db, primary_disk, copy_disk):
    """
    Simply increment the disk numbers by one. If the disk number is over the
    expected number of disks, check the DB and see if disks have been added.

    :param db: sqlite3 database object
    :param primary_disk: Label for primary disk
    :param copy_disk: Label for copy disk
    :return: Tuple with new disk labels to be used
    """
    new_primary_disk = get_new_disk(db, primary_disk)
    new_copy_disk = get_new_disk(db, copy_disk)
    return new_primary_disk, new_copy_disk


def get_new_disk(db, disk):
    """
    Simply increment the disk numbers by one. If the disk number is over the
    expected number of disks, check the DB and see if disks have been added.

    :param db: sqlite3 database object
    :param disk: Disk ID to be incremented
    :return: New Disk ID
    """
    cursor = db.cursor()
    new_disk = "%s%02d" % (disk[0], int(disk[1:]) + 1)
    # Sanity check that the disk exists in the DB
    cursor.execute("SELECT * FROM disks WHERE label = '{0}'".format(new_disk))
    if cursor.fetchall() is None:
            logging.fatal(("The disk %s is not available. Please update the "
                           "DB or check out what happened here."), new_disk)
            raise RuntimeError()
    cursor.execute("""UPDATE disks SET previously_used='True'
                      WHERE label = '{0}'""".format(new_disk))
    return new_disk


def get_current_disk_space(config, primary_disk, copy_disk):
    """
    Calculate the free disk space

    :param config: Config parameters dict()
    :param primary_disk: Label for primary disk
    :param copy_disk: Label for copy disk
    :return: Tuple of the free space of the two disks
    """
    mountpoint = config["Data"]["diskmountpoints"]
    primary_disk_abspath = os.path.join(mountpoint, primary_disk, "")
    copy_disk_abspath = os.path.join(mountpoint, copy_disk, "")
    disk_stats_primary = os.statvfs(primary_disk_abspath)
    disk_stats_copy = os.statvfs(copy_disk_abspath)
    freespace_primary = (disk_stats_primary.f_bavail *
                         disk_stats_primary.f_frsize)
    freespace_copy = disk_stats_copy.f_bavail * disk_stats_copy.f_frsize
    return freespace_primary, freespace_copy


def ping_winterovers():
    pass


def config_options_dict(config):
    """
    Parsing config file

    :param config: Python config parser object
    :return: dict with the different sections of the config file
             and the literal values of the configuraton objects
    """
    config_dict = {}
    for section in config.sections():
        config_dict[section] = {}
        for option in config.options(section):
            val = config.get(section, option)
            try:
                val = ast.literal_eval(val)
            except Exception:
                pass
            config_dict[section][option.lower()] = val
    return config_dict


def check_config(config):
    """
    Check whether configured parameters exist

    :param: Config dict
    """
    if not os.path.exists(config["DB"]["filenamedb"]):
        logging.fatal("Cannot find DB file")
        raise RuntimeError()
    if not os.path.exists(config["Data"]["bufferlocation"]):
        logging.fatal("Buffer location does nost exist")
        raise RuntimeError()
    if not os.path.exists(config["Data"]["diskmountpoints"]):
        logging.fatal("Disk mount does not exist")
        raise RuntimeError()


def run(config):
    with sqlite3.connect(os.path.expandvars(config["DB"]["filenamedb"])) as db:
        primary_disk, copy_disk = get_useable_disk(db)
        logging.debug("Primary Disk is %s. Copy disk is %s",
                      primary_disk,
                      copy_disk)
        new_files = check_new_files(db, (config["Data"]["bufferlocation"] +
                                         "*." + config["Data"]["extension"]))
        if not new_files:
            logging.info("No new files. Exiting")
            sys.exit()
        freespace_prim, freespace_copy = get_current_disk_space(primary_disk,
                                                                copy_disk)
        logging.debug(("Primary Disk is %s and has %d GB free. "
                       "Copy disk is %s and has %d GB free"),
                      primary_disk,
                      freespace_prim / (1024. * 1024.),
                      copy_disk,
                      freespace_copy / (1024. * 1024.))
        for file in new_files:
            filesize = os.stat(file).st_size
            if (freespace_prim < filesize and
               freespace_copy < filesize):
                logging.info(("Getting new disks. Primary Disk %s and copy "
                              "disk%s are full."), primary_disk, copy_disk)
                mark_disks_full(db, primary_disk, copy_disk)
                primary_disk, copy_disk = get_new_disks(db,
                                                        primary_disk,
                                                        copy_disk)
                logging.debug("New Primary Disk is %s. New Copy disk is %s",
                              primary_disk,
                              copy_disk)
                if config["General"]["testing"]:
                    logging.fatal("Done testing")
                    raise RuntimeWarning()
            elif freespace_prim < filesize:
                logging.info("Primary Disk %s is full.", primary_disk)
                mark_disk_full(db, primary_disk)
                primary_disk = get_new_disk(db, primary_disk)
                logging.info("New Primary Disk is %s.", primary_disk)
            elif freespace_copy < filesize:
                logging.info("Copy Disk %s is full", primary_disk)
                mark_disk_full(db, copy_disk)
                copy_disk = get_new_disk(db, copy_disk)
                logging.info("New Copy Disk is %s.", copy_disk)
            copy_file_to_disks(config, db, file, primary_disk, copy_disk)


def testing(config):
    i = 3
    while True:
        buffer_file = os.path.join(config["Data"]["bufferlocation"],
                                   "file_testing_{0}.txt".format(i))
        logging.debug("Creating file %s", buffer_file)
        command = "dd if=/dev/urandom of={0} ".format(buffer_file) +\
                  "count=1048576 bs=4096"
        c = subprocess.Popen(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True)
        output, error = c.communicate()
        print(output, error)
        try:
            run(config)
            logging.debug("Removing test file")
            os.remove(buffer_file)
        except:
            break
        i += 1


def main():
    if not os.path.exists(options.config_file):
        logging.log_fatal("Config file %s does not exist", options.config_file)
        raise RuntimeError()
    config = configparser.ConfigParser()
    config.read(options.config_file)
    config_dict = config_options_dict(config)
    if config_dict["General"]["testing"]:
        testing(config_dict)
    else:
        run(config_dict)


if __name__ == "__main__":
    main()