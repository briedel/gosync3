#!/usr/bin/env python
from __future__ import absolute_import, division, print_function
import os
import logging as log
import json

from cax.tasks import transfer, process
from optparse import OptionParser


def main(options, args):
    if not os.path.exists(options.config):
        log.FATAL("Can not find config files")
        raise RuntimeError()
    with open(options.config, "rt") as config_file:
        config = json.load(config_file)
    with open(options.rucio_config, "rt") as config_file:
        rucio_config = json.load(config_file)
    if ("tasks" in config and
       config["tasks"]["upload"] == "raw"):
        if config["tasks"]["transfer_method"] == "rucio":
            transfer.rucio_upload_raw_data(config,
                                           rucio_config)
    elif ("tasks" in config and
          config["tasks"]["download"] == "raw"):
        transfer.download_raw_data(config)
    elif ("tasks" in config and
          config["tasks"]["process"] == "raw"):
        process.process_raw_data(config, rucio_config)
    else:
        log.ERROR("Do not know how to handle data")
        raise RuntimeError()


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("--config", dest="config",
                      default="sample_config.json",
                      help="config file to use")
    parser.add_option("--rucioconfig", dest="rucio_config",
                      default="rucio.json",
                      help="config file to use")
    parser.add_option("--verbosity", dest="verbosity", default=3,
                      help="logging level verbosity",)
    (options, args) = parser.parse_args()
    level = {
        1: log.ERROR,
        2: log.WARNING,
        3: log.INFO,
        4: log.DEBUG
    }.get(options.verbosity, log.DEBUG)
    main(options, args)
