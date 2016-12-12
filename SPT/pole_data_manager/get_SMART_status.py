#!/usr/bin/env python
import glob
import subprocess
import re

with open(inputfilename, "rt") as f:
    serial_nums = []
    for line in f:
        line = line.rstrip("\n")
        line.split(" ")
    # Looping through the disks in /dev/
    for d in glob.glob("/dev/sd*"):
        # Calls the smartctl
        c = subprocess.Popen("smartctl -a {0}".format(d),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True)
        output, error = c.communicate()
        re_serial_num = re.findall("Serial number:(.*)",
                                   output, re.MULTILINE)
        re_smart_status = re.findall("SMART Health Status:(.*)",
                                     output, re.MULTILINE)
        if re_serial_num[0].lstrip(":").replace(" ", "") in serial_nums:
            smart_status = re_smart_status.replace(" ", "")
            if smart_status != "OK":
                #Tell winterovers