#!/usr/bin/env
import subprocess
import re
import glob
import operator

"""
REQUIRES ROOT TO RUN
"""


def get_sn_logical_ids_map(outfilename="disk_sn_to_logical_id.txt"):
    """
    Getting the mapping between disk serial number and logical id

    :param outfilename: Where the output should be written
    :return: dict() with {<serial number>: <logical id>}
    """
    sn_to_lid = {}
    with open(outfilename, "wt") as f:
        # Looping through the disks in /dev/
        for d in glob.glob("/dev/sd*"):
            # Calls the smartctl
            c = subprocess.Popen("smartctl -a {0}".format(d),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)
            output, error = c.communicate()
            # Finding the Serial and logical id
            re_serial_num = re.findall("Serial number(.*)",
                                       output,
                                       re.MULTILINE)
            if re_serial_num:
                serial_num = re_serial_num[0].lstrip(":").replace(" ", "")
            else:
                continue
            re_logical_id = re.findall("Logical Unit id(.*)",
                                       output,
                                       re.MULTILINE)
            if re_logical_id:
                logical_id = re_logical_id[0].lstrip(":").replace(" ", "")
            else:
                continue
            f.write("{0} {1}\n".format(serial_num, logical_id))
            sn_to_lid[serial_num] = logical_id
    return sn_to_lid


def get_sn_label_map(infilename="disk-map-v3"):
    """
    Reading in mapping file

    :param infilename: File name of mapping
                       between label and drive serial number
    :return: dict with {<serial number>: <label>}
    """
    sn_to_label = {}
    with open(infilename, "rt") as infile:
        for line in infile:
            line = line.strip("\n")
            label, sn, mount_point = line.split(" ")
            sn_to_label[sn] = label
    return sn_to_label


def write_sn_label_logical_id_map(sn_to_label,
                                  sn_to_lid,
                                  outfilename="disk-map-v4"):
    """
    Writing out mapping

    :param sn_to_label: dict with {<serial number>: <label>}
    :param sn_to_lid: dict() with {<serial number>: <logical id>}
    :param outfilename: Filename to write to
    """
    with open("disk-map-v4", "wt") as outfile:
        for sn, label in sorted(sn_to_label.items(),
                                key=operator.itemgetter(1)):
            outfile.write("{0} {1} {2}\n".format(label, sn, sn_to_lid[sn]))


def main():
    sn_to_lid = get_sn_logical_ids_map()
    sn_to_label = get_sn_label_map()
    write_sn_label_logical_id_map(sn_to_label, sn_to_lid)


if __name__ == "__main__":
    main()