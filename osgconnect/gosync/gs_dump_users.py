#!/usr/bin/env python
from __future__ import print_function
import logging as log
import random
from globus_db import globus_db_nexus as globus_db
from connect_users import connect_users
from collections import defaultdict
from optparse import OptionParser

from util import *


def gen_new_passwd(config, globus_user, current_users):
    """
    Generate new passwd style list for a new user.

    A passwd style list:
    [<username>, <password>, <user id>,
     <default group (always 1000, i.e users)>, <Comment, i.e. user's name>,
     <home directory path>, <shell, defaults to bash>]

    Args:
        globus_user: Globus users to generate a passwd list for
        used_usernames: List of usernames that have already been provisioned

    Returns:
        passwd_new_user: List with user information. Every entry
                         corresponds to position  of the information in
                         the users passwd file.
    """
    if str(globus_user[0]) in current_users.usernames:
        log.warn("Trying to provision user %s again. Duplicate user",
                 str(globus_user[0]))
        return None
    while True:
        new_user_id = random.randint(10000, 65001)
        if new_user_id not in current_users.user_ids:
            break
    name = str(globus_user[1]["user_profile"][1]["full_name"])
    home_dir = get_home_dir(config, globus_user)
    passwd_new_user = [globus_user[0],
                       "x",
                       str(new_user_id),
                       "1000",
                       name,
                       home_dir,
                       "/bin/bash"]
    return passwd_new_user


def merge_two_dicts(x, y):
    """
    Given two dicts, merge them into a new dict as a shallow copy.

    Args:
        x: Dict() 1 to merge
        y: Dict() 2 to merge

    Returns:
        z: Dict() that is combination of x and y
    """
    z = x.copy()
    z.update(y)
    return z


def get_users_to_work_on(options, config, globus_users, current_users):
    """
    Determining which users we should work on.

    Args:
        options: CLI options
        config: Configuration parameters dict()
        globus_users: Dict mapping member to group
        current_users: connects_users object that holds the
                       information about already provisioned users

    Returns:
        :selected: Dict() mapping username to globus member object
    """
    if options.onlyuser is not None:
        selected = dict(member for member in member_group.iteritems()
                        if member[0] == options.onlyuser)
    else:
        # separate new and old users
        new_users, old_users = defaultdict(dict), defaultdict(dict)
        for username, info in globus_users.iteritems():
            if '@' in username:
                log.error(("username has @ in it, "
                           "skipping user %s"), username)
                continue
            if username in current_users.usernames:
                old_users[username] = info
            else:
                new_users[username] = info
        if options.onlycurrent:
            selected = old_users
        elif options.onlynew:
            selected = new_users
        else:
            selected = merge_two_dicts(old_users, new_users)
    return selected


def work_on_users(options, config, globus_users, current_users):
    """
    Doing work on the dicts of users

    Args:
        options: Command line options
        config: Configuration parameters dict()
        globus_users: Dict mapping member to group to work on
        current_users: connects_users object that holds the
                       information about already provisioned users
    """
    log.debug("Provisioning or updating users")
    for member in globus_users.iteritems():
        username = member[0]
        if (options.onlyuser is not None and
           options.onlyuser != username):
            continue
        log.debug("Provisioning or updating user %s", username)
        if options.onlynew:
            create_new_user(config, member, current_users)
        elif options.onlycurrent:
            update_user(member, passwd_line, current_users)
        else:
            create_new_user(config, member, current_users)


def update_user(config, member, current_users):
    """
    Only update information for existing users.
    At the moment only updated ssh key and email forwarding

    Args:
        config: Configuration parameters dict()
        member: Globus Nexus member
        current_users: connects_users object that holds the
                       information about already provisioned users
    """
    # passwd_line = gen_new_passwd(config, member,
    #                              current_users)
    # if passwd_line is not None:
    #     print(passwd_line)
    #     log.debug("Passwd line for user %s = %s",
    #               passwd_line[0],
    #               ":".join(passwd_line))
    #     if member[0] not in current_users.usernames:
    #         edit_passwd_file(config, passwd_line, "append")
    #     home_dir = get_home_dir(config, member)
    #     if not os.path.exists(home_dir):
    #         create_user_dirs(config, member, passwd_line)
    if member[1]["user_profile"][1]["ssh_pubkeys"]:
        add_ssh_key(config, member)
    if member[1]["user_profile"][1]["email"]:
        add_email_forwarding(config, member)


def create_new_user(config, member, current_users):
    """
    Create new user. Create entry in /etc/passwd file, create
    home directory and user storage directory, add ssh key,
    and email forwarding

    Args:
        config: Configuration parameters dict()
        member: Globus Nexus member
        connect_usernames: connects_users object that holds the
                           information about already provisioned users
    """
    passwd_line = gen_new_passwd(config, member,
                                 current_users)
    if passwd_line is not None:
        print(passwd_line)
        log.debug("Passwd line for user %s = %s",
                  passwd_line[0],
                  ":".join(passwd_line))
        if member[0] not in current_users.usernames:
            edit_passwd_file(config, passwd_line, "append")
        home_dir = get_home_dir(config, member)
        if not os.path.exists(home_dir):
            create_user_dirs(config, member, passwd_line)
    if member[1]["user_profile"][1]["ssh_pubkeys"]:
        add_ssh_key(config, member)
    if member[1]["user_profile"][1]["email"]:
        add_email_forwarding(config, member)


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
        1: logging.ERROR,
        2: logging.WARNING,
        3: logging.INFO,
        4: logging.DEBUG
    }.get(options.verbosity, logging.DEBUG)
    logging.basicConfig(level=level)
    main(options, args)
