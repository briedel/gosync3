#!/usr/bin/env python
from __future__ import print_function
import logging
import random

from optparse import OptionParser

from util import *


def get_connect_userinfo(config, options):
    """
    Parse passwd file to see what users were already provisioned

    :param config: Configuration parameters dict()
    :param options: Command line options
    :return: Tuple if lists, where every list is the user information
    """
    with open(config["users"]["passwd_file"], "rt") as f:
        user_info = [tuple(line.lstrip("\n").split(":")) for line in f]
    return tuple(user_info)


def get_connect_usernames(config=None, options=None, users=None):
    """
    Get tuple of already provisioned usernames. Works either by
    getting the output of get_connect_userinfo() or by getting
    the configuration and options to call get_connect_userinfo()
    internally.

    :param config: (optional requires options) Configuration parameters dict()
    :param options: (optional requires config) Command line options
    :param users: (optional) list of user information
    :return: Tuple of already provisioned usernames
    """
    def do_work(usrs):
        return tuple(u[0] for u in usrs)
    if users is not None:
        return do_work(users)
    elif config is not None and options is not None:
        user_info = get_connect_userinfo(config, options)
        return do_work(user_info)
    else:
        logging.error("Cannot retrieve connect usernames")
        raise RuntimeError()


def get_connect_user_ids(config=None, options=None, users=None):
    """
    Get tuple of already used user ids. Works either by
    getting the output of get_connect_userinfo() or by getting
    the configuration and options to call get_connect_userinfo()
    internally.

    :param config: (optional requires options) Configuration parameters dict()
    :param options: (optional requires config) Command line options
    :param users: (optional) list of user information
    :return: Tuple of already used user ids
    """
    def do_work(usrs):
        return tuple(u[2] for u in usrs)
    if users is not None:
        return do_work(users)
    elif config is not None and options is not None:
        user_info = get_connect_userinfo(config, options)
        return do_work(user_info)
    else:
        logging.error("Cannot retrieve connect user ids")
        raise RuntimeError()


def gen_new_passwd(globus_user, used_usernames, used_user_ids):
    """
    Generate new passwd style list for a new user.

    A passwd style list:
    [<username>, <password>, <user id>,
     <default group (always 1000, i.e users)>, <Comment, i.e. user's name>,
     <home directory path>, <shell, defaults to bash>]

    :param globus_user: Globus users to generate a passwd list for
    :param used_usernames: List of usernames that have already been provisioned
    :param used_user_ids: List of user ids that have already been used
    :return: List with user information. Every entry corresponds to position of
             of the information in the users passwd file.
    """
    if str(globus_user['username']) in used_usernames:
        logging.error("Trying to provision user %s again. Duplicate user",
                      str(globus_user['username']))
        raise RuntimeError()
    while True:
        new_user_id = random.randint(10000, 65001)
        if new_user_id not in used_user_ids:
            break
    passwd_new_user = [str(globus_user["username"]),
                       "x",
                       str(new_user_id),
                       "1000",
                       str(globus_user['name']),
                       os.path.join("/home", str(globus_user["username"])),
                       "/bin/bash"]
    return passwd_new_user


def get_users_to_work_on(options, config, client):
    """
    Determining which users we should work on.

    :param config: (optional requires options) Configuration parameters dict()
    :param options: (optional requires config) Command line options
    :param client: Globus Nexus RESTful client
    :return: Tuple of users to work on
    """
    globus_members = get_globus_group_members(options, config, client)
    connect_usernames = get_connect_usernames(config, options)
    # separate new and old users
    new_users = []
    old_users = []
    for member in globus_members:
        username = str(member['username'])
        if '@' in username:
            logging.error(("username has @ in it, "
                           "skipping user %s"), username)
            continue
        if username in connect_usernames:
            old_users.append(member)
        else:
            new_users.append(member)

    if options.onlyuser is not None:
        selected = tuple(member for member in globus_members
                         if str(member['username']) == options.onlyuser)
    elif options.onlyupdated:
        selected = old_users
    elif options.onlynew:
        selected = new_users
    else:
        selected = old_users + new_users
    return selected


def work_on_users(options, config, client, globus_users):
    """
    Doing work on the list of users

    :param config: (optional requires options) Configuration parameters dict()
    :param options: (optional requires config) Command line options
    :param globus_users: List of users from Globus that we need to work on
    """
    connect_usernames = get_connect_usernames(config, options)
    connect_userids = get_connect_user_ids(config, options)
    for member in globus_users:
        username = str(member['username'])
        if (options.onlyuser is not None and
           options.onlyuser != username):
            continue
        try:
            passwd_line = gen_new_passwd(member,
                                         connect_usernames,
                                         connect_userids)

            go_user_profile = client.get_user_profile(username)[1]        
        except socket.timeout:
            # if we time out, pause and resume, skipping current
            logging.error(("Socket timed out. Waiting for 5 seconds. "
                           "User %s was skipped") % username)
            time.sleep(5)
            continue
        except:
            continue
        if 'credentials' in go_user_profile:
            member['ssh'] = sorted([cred['ssh_key']
                                    for cred in go_user_profile['credentials']
                                    if cred['credential_type'] == 'ssh2'])
        else:
            member['ssh'] = []
        if options.onlynew:
            create_new_user(config, member, passwd_line)
        elif options.onlyupdated:
            update_user(member, passwd_line, connect_usernames)
        else:
            create_new_user(config, member, passwd_line)


def update_user(config, member, passwd_line, connect_usernames):
    """
    Only update information for existing users.

    :param member: Globus Nexus member
    :param passwd_line: Passwd list
    :param connect_usernames: Tuple of connect user names
    """
    if passwd_line[0] not in connect_usernames:
        edit_passwd_file(config, passwd_line, "append")
    if not os.path.exists(passwd_line[-2]):
        create_home_dir(passwd_line)
    add_ssh_key(member, passwd_line)
    add_email_forwarding(member, passwd_line)


def create_new_user(config, member, passwd_line):
    """
    Create new user.

    :param member: Globus Nexus member
    :param passwd_line: Passwd list
    :param connect_usernames: Tuple of connect user names
    """
    edit_passwd_file(config, passwd_line, "append")
    create_home_dir(passwd_line)
    if member['ssh']:
        add_ssh_key(member, passwd_line)
    if member["email"]:
        add_email_forwarding(member, passwd_line)


def main(options, args):
    config = parse_config(options.config)
    client = get_globus_client(config)
    users_work_on = get_users_to_work_on(options, config, client)
    work_on_users(options, config, client, users_work_on)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("--config", dest="config", default="gosync.conf",
                      help="config file to use",)
    parser.add_option("-v", "--verbosity", dest="verbosity",
                      help="Set logging level", default=3)
    parser.add_option("--onlynew", dest="onlynew", action="store_true",
                      default=False, help="Force update information")
    parser.add_option("--onlyupdated", dest="onlyupdated", action="store_true",
                      default=False, help="Force update information")
    parser.add_option("--onlyuser", dest="onlyuser", default=None,
                      help="Force update information")
    parser.add_option("--forceupdate", dest="forceupdate", action="store_true",
                      default=False, help="Force update information")
    (options, args) = parser.parse_args()
    level = {
        1: logging.ERROR,
        2: logging.WARNING,
        3: logging.INFO,
        4: logging.DEBUG
    }.get(options.verbosity, logging.DEBUG)
    main(options, args)


#*/10 * * * * ( cd /usr/local/gosync && ./gosync -q --nw sync users --new && ./gosync -q --nw sync groups ) > /tmp/gosync_newuser.dat 2>&1
#*/15 * * * * ( cd /usr/local/gosync && ./gosync -q --nw sync users --updated; ./gosync -q --nw sync groups ) > /tmp/gosync_user_update.dat 2>&1


#     def cmd_sync_users(self, args):
#         '''@ sync users
# @ sync users [--new] [--updated] [--only <user> [...]]'''
#         self.lock()
#         out = []
#         pending = []
#         selected = []
#         didselect = False

#         headers, response = self.client.get_group_members(self.groupid(self.topgroup))
#         members = response['members']
#         members = [member for member in members if member]

#         # separate new and old users
#         newusers = []
#         oldusers = []
#         for member in members:
#             if member['status'] != 'active':
#                 continue
#             username = str(member['username'])
#             if '@' in username:
#                 sys.stderr.write("username has @ in it, skipping\n")
#                 continue
#             if username in self.db:
#                 oldusers.append(member)
#             else:
#                 newusers.append(member)

#         # shuffle member list so that if we break down and die,
#         # we'll still get a different set each time
#         random.shuffle(oldusers)

#         try:
#             opts, args = getopt.getopt(args, '', ['new', 'updated', 'only'])
#         except getopt.GetoptError, e:
#             self.error(e)
#             return None

#         for opt, arg in opts:
#             if opt in ('--new',):
#                 selected += newusers
#                 didselect = True

#             if opt in ('--updated',):
#                 selected += oldusers
#                 didselect = True

#             if opt in ('--only',):
#                 selected += [member for member in members if member['username'] in args]
#                 didselect = True

#         if not didselect:
#             selected += newusers + oldusers

#         if not selected:
#             return 10

#         for member in selected:
#             username = str(member['username'])
#             if member['status'] != 'active':
#                 continue
#             try:
#                 prof = self.client.get_user_profile(username)[1]
#             except socket.timeout:
#                 # if we time out, pause and resume, skipping current
#                 print 'TIMEOUT PAUSE 5s'
#                 time.sleep(5)
#                 continue
#             if prof.has_key('credentials'):
#                 member['ssh'] = sorted([cred['ssh_key'] for cred in prof['credentials'] if cred['credential_type'] == 'ssh2'])
#             else:
#                 member['ssh'] = []
#             member = userdb.clean(member)
#             added = updated = False
#             if username in self.db:
#                 updated = self.db.upduser(member, force=self.forceupdate)
#             else:
#                 added = self.db.adduser(member)
#             if added or updated:
#                 pending.append((member, updated))
#             time.sleep(0.5)

#         pre = post = None
#         if self.cfg.has_option('user', 'pre'):
#             pre = self.cfg.get('user', 'pre')
#         if self.cfg.has_option('user', 'post'):
#             post = self.cfg.get('user', 'post')

#         if pending:
#             if pre:
#                 os.system(pre)
#             for member, updated in pending:
#                 self.provisionuser(self.db, member, updated=updated)
#             if post:
#                 os.system(post)

#         self.db.sync()
#         for line in out:
#             print line