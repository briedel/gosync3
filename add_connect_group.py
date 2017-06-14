#!/usr/bin/env python
from __future__ import print_function
import argparse
import logging as log
from globus_db import globus_db
from connect_db import connect_db_json as connect_db
from util import parse_json_config


def main(args):
    config = parse_json_config(args.config)
    connectdb = connect_db(config=config)
    globusdb = globus_db(config=config, connect_db=connectdb)
    globusdb.add_group(args.projectfile,
                       username="connect", group_parent=args.parent)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count')
    parser.parse_args(['-vvv'])
    parser.add_argument("--projectfile", required=True,
                        help="Project description file")
    parser.add_argument("--parent", help="Parent group for the project",
                        default=None)
    parser.add_argument("--config", help="echo the string you use here",
                        default="gosync3.json")
    args = parser.parse_args()
    log.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level=args.verbose)
    log.debug("Using config file %s", args.config)
    main(args)
