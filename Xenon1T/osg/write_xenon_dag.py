#!/usr/bin/env python
from __future__ import print_function
import sys
import os

raw_data_dir = sys.argv[1]

gridftp_uri = "gsiftp://gridftp.grid.uchicago.edu:2811/cephfs/srm"


def get_out_name(filename):
    return filename.split(".")[0] + ".root"


def get_out_dir(dir_name, run_number):
    return os.path.join("/".join(dir_name.split("/")[:3]),
                        "output",
                        str(run_number),
                        "")


def get_run_number(dir_name):
    return dir_name.split("/")[-1]


i = 0
with open("xenon_test.dag", "wt") as dag_file:
    for dir_name, subdir_list, file_list in os.walk(raw_data_dir):
        if "MV" in dir_name:
            continue
        run_number = get_run_number(dir_name)
        # if run_number != "161021_0841":
        #     continue
        if "1606" in run_number or "1603" in run_number or "1607" in run_number:
            continue
        for infile in file_list:
            if "XENON1T-" not in infile:
                continue
            run_number = get_run_number(dir_name)
            outfile = get_out_name(infile)
            outdir = get_out_dir(dir_name, run_number)
            outfile = gridftp_uri + os.path.join(outdir, outfile)
            infile = gridftp_uri + os.path.join(dir_name, infile)
            dag_file.write("JOB XENON.%d xenon.submit\n" % i)
            dag_file.write("VARS XENON.%d input_file=\"%s\" out_location=\"%s\" name=\"%s\" ncpus=\"1\" disable_updates=\"True\" host=\"login\" pax_version=\"5.5.1\" pax_hash=\"n/a\"\n" % (i, infile, outfile, run_number))
            dag_file.write("Retry XENON.%d 3\n" % i)
            i += 1
