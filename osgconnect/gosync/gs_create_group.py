#!/usr/bin/env python
from __future__ import print_function
# import os
import sys
import logging
import random
import json

from optparse import OptionParser

from util import *

def get_group_policy(options, config):
    policy_dir = config["users"]["policy_dir"]
    default_file = config["users"]["default_policy_file"]



def add_globus_groups(options, config):



def main(options, args):
    config = parse_config(options.config)
    client = get_globus_client(config)
    users_work_on = get_users_to_work_on(options, config, client)
    work_on_users(options, config, users_work_on)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("--config", dest="config", default="gosync.conf",
                      help="config file to use",)
    parser.add_option("-v", "--verbosity", dest="verbosity",
                      help="Set logging level", default=3)
    parser.add_option("--format", dest="format", default=['html'],
                      action="callback", callback=callback_optparse,
                      help="Output format to use given as a list")
    parser.add_option("-o", "--outfile", dest="outfile", default=None,
                      help="Output file to write things too")
    parser.add_option("--force", dest="force", action="store_true",
                      default=False, help="Force update information")
    parser.add_option("--baseurl", dest="baseurl", default=None,
                      help="Base URL to use")
    parser.add_option("--portal", dest="portal", default=None,
                      help="Portal to use")
    parser.add_option("--parent", dest="parent", default=None,
                      help="Parent group to use")
    parser.add_option("--top", dest="top", default=None,
                      help="Top group to use")
    parser.add_option("--group", dest="group", default=None,
                      help="Group to use")
    parser.add_option("--onlynew", dest="onlynew", action="store_true",
                      default=False, help="Force update information")
    parser.add_option("--onlyupdated", dest="onlyupdated", action="store_true",
                      default=False, help="Force update information")
    parser.add_option("--onlyuser", dest="onlyuser", default=None,
                      help="Force update information")
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