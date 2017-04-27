from __future__ import print_function
import logging as log

from collections import defaultdict


class connect_groups(object):
    def __init__(self, config, options=None):
        self.config = config
        if self.config is None:
            log.fatal("Config required")
            raise RuntimeError()
        self.options = options
        self.groups = defaultdict(dict)
        self.get_group_info()

    def reshape_group_name(self, group_name):
        # TODO: needs to be part of config
        top_level_groups = self.config["globus"]["top_level_groups"]
        top_level_groups += self.config["globus"]["root_group"]
        group_name = group_name.lstrip("@")
        if group_name in top_level_groups:
            return group_name
        split_name = group_name.split("-")
        if split_name and split_name[0] in top_level_groups:
            group_name = group_name.replace("-", ".")
        else:
            group_name = "osg." + group_name
        return group_name

    def get_group_info(self, config=None):
        if config is None:
            config = self.config
        with open(config["groups"]["group_file"], "rt") as f:
            for line in f:
                group_line = line.rstrip("\n").split(":")
                group_line[0] = self.reshape_group_name(group_line[0])
                self.groups[group_line[0]] = {
                    "passwd": group_line[1],
                    "guid": group_line[2],
                    "members": group_line[3].split(",")
                }

    # def write_group_file(self, config):
        
