#!/usr/bin/env python
from __future__ import print_function
import os
import logging
import sqlite3

from optparse import OptionParser

logging.basicConfig(level=logging.DEBUG,
                    format=('%(asctime)s %(name)-12s '
                            '%(levelname)-8s %(message)s'),
                    datefmt='%m-%d %H:%M')


def main(options, args):
    if os.path.exists(options.db_filename) and not options.new_DB:
        logging.info('Database exists, assume schema does, too. Doing nothing')
    else:
        if os.path.exists(options.db_filename):
            logging.info("Deleting old DB.")
            os.remove(options.db_filename)
        with sqlite3.connect(options.db_filename) as conn:
            logging.info("New DB")
            with open(options.db_schema_filename, 'rt') as f:
                schema = f.read()
            conn.executescript(schema)
            with open(options.disk_filename, "rt") as f:
                disk_status_prim = False
                disk_status_copy = False
                for line in f:
                    line = line.rstrip("\n")
                    label, serial_number, logical_id = line.split(" ")
                    if not os.path.exists("/spt_disks/{0}".format(label)):
                        raise RuntimeError("Mountpoint {0} does not exist".format("/spt_disks/{0}".format(label)))
                    st = os.statvfs("/spt_disks/{0}".format(label))
                    free = st.f_bavail * st.f_frsize
                    total = st.f_blocks * st.f_frsize
                    used = (st.f_blocks - st.f_bfree) * st.f_frsize
                    previously_used = False
                    if options.pole:
                        ####
                        # TODO: Numbers for free, used edge cases need adjusting according 
                        #       to expected filesizes
                        #       35028992 is the default used space
                        #       7999426224128 is the default disk size
                        #       7999391195136 is the free space in a formated disk
                        ####
                        if total < 7999426224128:
                            # Are the drives below 8 TB..... Odd! Sad!
                            logging.fatal(("Disk /spt_disks/{0} is smaller "
                                           "than expected. Something "
                                           "is weird").format(label))
                            raise RuntimeError(("Exiting because disk mount "
                                                "appears corrupted. Check "
                                                "mount on "
                                                "/spt_disks/{0}").format(label))
                        if not disk_status_prim or not disk_status_copy:
                            if ((label == "P01" or label == "S01") and
                               options.new_DB and free > 35028992):
                                previously_used = True
                                if label[0] == "P":
                                    disk_status_prim = True
                                if label[0] == "S":
                                    disk_status_copy = True
                            elif (options.new_DB and
                                  free > 35028992 and
                                  used > 35028992):
                                previously_used = True
                                if label[0] == "P":
                                    disk_status_prim = True
                                if label[0] == "S":
                                    disk_status_copy = True
                    else:
                        previously_used = True
                    conn.execute("""
                        insert into disks (label, serialno,
                        logical_device_id, alive, full,
                        max_space, space_used, previously_used)
                        values ('{name}', '{sn}', '{logical_device_id}',
                        '{alive}', '{full}', '{max_space}',
                        '{space_used}', '{previously_used}')
                        """.format(name=label, sn=serial_number, logical_device_id=logical_id, 
                                   alive=True, full=False, max_space=total, space_used=used,
                                   previously_used=previously_used))

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("--dbfile",
                      dest="db_filename", default="spt_data_management.db",
                      help="Filename for sqlite3 DB",
                      metavar="FILE")
    parser.add_option("--schemafile",
                      dest="db_schema_filename",
                      default="spt_data_management_schema.sql",
                      help="Filename for DB schema file")
    parser.add_option("--diskfile", dest="disk_filename", default="disk-map",
                      help=("File with relationship between labels, "
                            "disk serial number, and partition uuid"))
    parser.add_option("--newDB", action="store_true", dest="new_DB", default=False,
                      help="Completely new DB")
    parser.add_option("--pole", action="store_true", dest="pole", default=False,
                      help=("Assuming we are using the pole setup. "
                            "More checks: Disk size, disk space, etc."))
    (options, args) = parser.parse_args()
    main(options, args)
