#!/usr/bin/env python
from __future__ import print_function
import glob
import os
import re
# from collections import OrderedDict

expected_keys = [
    "Your Name", "Your Email Address", "Project Name",
    "Short Project Name", "Field of Science", "Field of Science (if Other)",
    "PI Name", "PI Email", "Organization", "Department", "Join Date",
    "Sponsor", "OSG Sponsor Contact", "Project Contact",
    "Project Contact Email", "Telephone Number",
    "Project Description"]

mapping_old_new_keys = {
    "PI Organization": "Organization",
    "PI Department": "Department"}

phonePattern = re.compile(r'''
                # don't match beginning of string, number can start anywhere
    (\d{3})     # area code is 3 digits (e.g. '800')
    \D*         # optional separator is any number of non-digits
    (\d{3})     # trunk is 3 digits (e.g. '555')
    \D*         # optional separator
    (\d{4})     # rest of number is 4 digits (e.g. '1212')
    \D*         # optional separator
    (\d*)       # extension is optional and can be any number of digits
    $           # end of string
    ''', re.VERBOSE)


def sanitize_phone_number(tel_num):
    match = phonePattern.match(tel_num)
    if match is None:
        return tel_num
    groups = phonePattern.search(tel_num).groups()
    number = "-".join(["1",
                       str(groups[0]),
                       str(groups[1]),
                       str(groups[2])])
    if groups[-1] != "":
        return number + "x%s" % groups[-1]
    else:
        return number


for file in glob.glob("/usr/local/gosync/descriptions/osg.*"):
    group_info = {}
    split = ["", ""]
    basename = os.path.basename(file)
    with open(file, "rt") as f:
        project_desc_yet = False
        for line in f:
            line = line.rstrip("\n")
            if "=" in line and "http" not in line:
                print(file)
                continue
            if not line and split[0] != "Project Description":
                continue
            if ":" in line:
                if "http" in line:
                    split = line
                else:
                    split = line.split(":")
                if isinstance(split, str):
                    split = ["", split]
                split[1] = split[1].strip()
                if split[0] in mapping_old_new_keys:
                    split[0] = mapping_old_new_keys[split[0]]
                if split[0] in expected_keys and not project_desc_yet:
                    if split[0] == "Telephone Number":
                        split[1] = sanitize_phone_number(split[1])
                    group_info[split[0]] = split[1]
                    if split[0] == "Project Description":
                        project_desc_yet = True
                elif project_desc_yet:
                    split_com = "".join(split)
                    group_info["Project Description"] = (
                        group_info["Project Description"] +
                        "\n" + split_com)
            else:
                if project_desc_yet:
                    group_info["Project Description"] = (group_info["Project Description"] + "\n" +
                                            line)
                else:
                    print(file)
                    print(split[0])
    with open(basename, "wt") as of:
        for key in expected_keys:
            of.write("%s:" % key)
            if key in group_info:
                of.write(" %s\n" % group_info[key])
            else:
                of.write("\n")

