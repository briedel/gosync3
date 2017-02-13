from __future__ import print_function

import globus_sdk
from nexus import GlobusOnlineRestClient
import psycopg2

from globus_db import globus_db_nexus as globus_db


# conn = psycopg2.connect(dbname = "connect", user="connect", password="YvbnZ2{ChxfPDUzD9uXvAE3+xa?BaLzr", host="127.0.0.1")

# with conn:
#     with

def convert_group_json_to_psql(group_info):

    return group_info_dict


def main(options, args):
    config = parse_config(options.config)
    log.debug("Config is %s", config)
    if options.filters is not None:
        config["groups"]["filter_prefix"] = options.filters
    go_db = globus_db(config)
    group_members, member_group = go_db.get_globus_group_members(
        no_top_level=True)
    current_users = connect_users(config, options)
    users_work_on = get_users_to_work_on(options, config,
                                         member_group, current_users)
    work_on_users(options, config, users_work_on, current_users)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("--config", dest="config", default="gosync.conf",
                      help="config file to use",)
    parser.add_option("-v", "--verbosity", dest="verbosity",
                      help="Set log level", default=4)
    parser.add_option("--onlynew", dest="onlynew", action="store_true",
                      default=False, help="Force update information")
    parser.add_option("--onlycurrent", dest="onlycurrent", action="store_true",
                      default=False, help="Force update information")
    parser.add_option("--onlyuser", dest="onlyuser", default=None,
                      help="Force update information")
    parser.add_option("--forceupdate", dest="forceupdate", action="store_true",
                      default=False, help="Force update information")
    parser.add_option("--filters", dest="filters", default=None,
                      action="callback", callback=callback_optparse,
                      help="Output format to use given as a list")
    (options, args) = parser.parse_args()
    level = {
        1: log.ERROR,
        2: log.WARNING,
        3: log.INFO,
        4: log.DEBUG
    }.get(options.verbosity, log.DEBUG)
    log.basicConfig(level=level)
    main(options, args)

