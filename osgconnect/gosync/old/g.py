#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import os
import sys
import ConfigParser
import shelve
import getopt
import time
import glob
import json
import re
import fnmatch
import errno
import random
import socket
import grp
import pwd

# Comment this to NOT profile
#import cProfile

try:
    from IPython import embed as ipython
except ImportError:
    ipython = None

class LockError(Exception): pass

from nexus import GlobusOnlineRestClient

#config = {
#   'client': 'dgctest1',
#   'client_secret': 'REDACTED',
#   'verify_ssl': False,
#   'cache': {'class': 'nexus.token_utils.InMemoryCache'},
#   'server': 'nexus.api.globusonline.org',
#}
#gc = GlobusOnlineRestClient(config=config)


class config(ConfigParser.RawConfigParser):
    def _groupget(self, group, option, method=None):
        for section in self.sections():
            if not section.startswith('group:'):
                continue
            filter = self.get(section, 'filter')
            matcher = Matcher([filter])
            if group not in matcher:
                continue
            if self.has_option(section, option):
                return method(section, option)
        return method('group', option)

    def groupget(self, group, option):
        return self._groupget(group, option, method=self.get)

    def groupgetint(self, group, option):
        return self._groupget(group, option, method=self.getint)

    def groupgetfloat(self, group, option):
        return self._groupget(group, option, method=self.getfloat)

    def groupgetbool(self, group, option):
        return self._groupget(group, option, method=self.getbool)

    def groupgetlist(self, group, option):
        return self._groupget(group, option, method=self.getlist)

    def getlist(self, section, option):
        strval = self.get(section, option).strip()
        if not strval:
            return []
        return [x.strip() for x in strval.split(',')]

    def nexusconfig(self, user):
        c = {}
        section = self.get('clients', user)
        if '&' in section:
            section = section.replace('&', user)
        serverid, user = section.split('.')

        c['server'] = self.get('servers', serverid)
        c['client'] = user
        c['client_secret'] = self.get(section, 'secret')

        return c


class Matcher(list):
    OR = 1
    AND = 2
    NOT = 3

    @staticmethod
    def matchfunc(expr):
        negate = False
        negstr = ['!', '']

        if expr.startswith('!'):
            negate = True
            expr = expr[1:].strip()

        if expr.startswith('/') and expr.endswith('/'):
            expr = expr[1:-1]
            rx = re.compile(expr, re.I)
            f = lambda x: negate ^ rx.search(x)
            f.desc = negstr[negate] + 're(' + expr + ')'
        elif '*' in expr or '?' in expr or '[' in expr:
            f = lambda x: negate ^ fnmatch.fnmatch(x, expr)
            f.desc = negstr[negate] + 'fnmatch(' + expr + ')'
        else:
            f = lambda x: negate ^ (x.lower() == expr.lower())
            f.desc = negstr[negate] + 'str(' + expr + ')'

        return f


    def _selector(self, expr):
        expr = expr.strip()
        if expr.lower() == 'or':
            yield self.OR
            return
        if expr.lower() == 'and':
            yield self.AND
            return
        if expr.lower() == 'not':
            yield self.NOT
            return

        yield self.matchfunc(expr)
        return


    def __init__(self, exprs, **kwargs):
        selectors = []
        for expr in exprs:
            for sel in self._selector(expr):
                selectors.append(sel)
        list.__init__(self, selectors)

    def describe(self):
        desc = ''
        for item in self:
            if item == self.OR:
                desc += ' or'
            elif item == self.AND:
                desc += ' and'
            elif item == self.NOT:
                desc += ' not'
            else:
                desc += ' ' + item.desc
        return desc.strip()

    def _run(self, key):
        match = []
        for selector in self:
            if selector == self.AND:
                r = match[-2] and match[-1]
                match = match[:-2] + [r]
            elif selector == self.OR:
                r = match[-2] or match[-1]
                match = match[:-2] + [r]
            elif selector == self.NOT:
                match[-1] = not match[-1]
            else:
                match.append(selector(key))
        return match[-1]

    def __call__(self, args, key=lambda x: x):
        stack = []
        return [arg for arg in args if self._run(key(arg))]

    def __contains__(self, other):
        return self._run(other)


def ts2epoch(ts):
    if '.' in ts:
        ts, mantissa = ts.split('.', 1)
        mantissa = float('0.' + mantissa)
    else:
        mantissa = 0

    st = time.strptime(ts, '%Y-%m-%d %H:%M:%S')
    return time.mktime(st) + mantissa


class allgroups(dict):
    def __init__(self, refresh=False):
        for gr in grp.getgrall():
            self[gr.gr_name] = gr.gr_mem


class userdb(object):
    '''At present the user object is a bland dictionary, and lacks methods
    of its own.  Actions on or under a user are contained in the userdb class,
    which is terrible layering but will do for rapid development.  We'll
    straighten this out later.'''

    def __init__(self, name, notice=None, error=None):
        self.db = shelve.open(name + '.db')
        self._notice = notice
        self._error = None

    def __getitem__(self, key):
        return self.db.get(key)

    def __setitem__(self, key, value):
        self.db[key] = value

    def __contains__(self, key):
        return key in self.db

    def __len__(self):
        return len(self.db)

    def __delitem__(self, key):
        del self.db[key]

    def __iter__(self):
        for k in self.db:
            yield k

    def keys(self):
        return self.db.keys()

    def notice(self, *args, **kwargs):
        if self._notice:
            self._notice(*args, **kwargs)

    def error(self, *args, **kwargs):
        if self._error:
            self._error(*args, **kwargs)

    def close(self):
        self.db.close()

    def sync(self):
        self.db.sync()

    def _changed(self, new, old):
        if new['last_changed'] > old['last_changed']:
            return True
        if new['status'] != old['status']:
            return True
        if new['email'] != old['email']:
            return True
        if new['name'] != old['name']:
            return True
        if ''.join(new['ssh']) != ''.join(old['ssh']):
            return True
        return False

    def _update(self, member):
        username = member['username']

        # the .update() method doesn't work on dicts that are values in
        # a shelve object.  The entire value must be replaced.
        # self[username].update(member)

        for k, v in self[username].items():
            if k not in member:
                member[k] = v

        member['pw_gecos'] = member['name']
        member['pw_dir'] = '/home/' + username

        self[username] = member

    @staticmethod
    def genuid(name):
        # This needs to be a little stronger but is OK for now.
        # It needs to check for duplication, etc. but for the moment
        # we'll just deal with unlikely collisions manually.

        # 55001 is a prime close to 65536-10000
        #uid = (hash(name) % 55001) + 10000
        while True:
            uid = random.randint(10000, 65001)

            # Check whether in use
            try:
                # if yes, keep searching
                pw = pwd.getpwuid(uid)
            except KeyError:
                break

        return uid

    @staticmethod
    def gengid(name):
        # This needs to be a little stronger but is OK for now.
        # It needs to check for duplication, etc. but for the moment
        # we'll just deal with unlikely collisions manually.

        # This also simply shouldn't be here.  We need a proper separation
        # of group and user objects.

        # 4999 is a prime close to 10000 - 5000
        gid = (hash(name) % 4999) + 5000
        return gid

    def adduser(self, member):
        username = member['username']

        self.notice('adding %s' % username)
        uid = userdb.genuid(username)
        member['pw_name'] = username
        member['pw_passwd'] = 'x'
        member['pw_uid'] = uid
        member['pw_gid'] = uid
        member['pw_gecos'] = member['name']
        member['pw_dir'] = '/home/' + username
        member['pw_shell'] = '/bin/bash'

        self[username] = member
        return True

    def upduser(self, member, force=False):
        username = member['username']

        if self._changed(member, self[username]) or force:
            self.notice('updating %s' % username)
            self._update(member)
            return True
        else:
            self.notice('no changes to %s' % username)
            return False

    @classmethod
    def clean(cls, member):
        new = uniclean(member)
        for key in ('invite_time', 'last_changed'):
            if key in new and new[key]:
                new[key] = ts2epoch(new[key])
        return new

    @staticmethod
    def mkpasswd(cfg, member):
        if 'pw_name' not in member:
            return None
        return '%s:%s:%d:%d:%s:%s:%s' % (
            member['pw_name'],
            member['pw_passwd'],
            member['pw_uid'],
            cfg.getint('user', 'defaultgid'),
            member['pw_gecos'],
            member['pw_dir'],
            member['pw_shell'])

    @staticmethod
    def mkgroup(cfg, member):
        return '%s:x:%d:%s' % (
            member['gr_name'],
            member['gr_gid'],
            member['gr_mem'])


def uniclean(o):
    if type(o) == type(''):
        return o

    if type(o) == type(u''):
        return o.encode('latin-1', 'replace')

    if type(o) == type([]):
        return [uniclean(x) for x in o]

    if type(o) == type({}):
        new = {}
        for k, v in o.items():
            new[str(k)] = uniclean(v)
        return new

    return None


class gosync(object):

    def __init__(self):
        self.program = os.path.basename(sys.argv[0])
        self.lockfile = None
        self.waitlock = True    # wait for lock to be released
        self.quiet = False      # do not talk about non-errors
        self.files = []
        self.user = None
        self.client = None
        self.topgroup = None
        self.cfg = None
        self.commands = []
        self.forceupdate = False
        self.groupcache = None


    def _msg(self, fp, prefix, *args):
        print >>fp, self.program, prefix, ' '.join([str(x) for x in args])


    def notice(self, *args):
        if self.quiet:
            return
        return self._msg(sys.stdout, 'NOTICE:', *args)


    def error(self, *args):
        return self._msg(sys.stderr, 'ERROR:', *args)


    def lock(self, wait=None, quiet=None):
        if wait is None:
            wait = self.waitlock
        if quiet is None:
            quiet = self.quiet
        self.lockfile = os.path.join('/var/run', self.program) + '.lock'
        do = True
        while do:
            if not wait:
                do = False
            try:
                os.symlink('%d' % os.getpid(), self.lockfile)
                return True
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise
            except:
                raise

            if wait:
                self.notice('lock file exists: pid = %s [waiting]' % os.readlink(self.lockfile))
                time.sleep(2)
            else:
                self.error('lock file exists: pid = %s' % os.readlink(self.lockfile))
                raise LockError


    def unlock(self):
        if not self.lockfile:
            return
        try:
            os.unlink(self.lockfile)
        except:
            pass


    @staticmethod
    def mkenv(dict):
        env = {}
        for k in dict.keys():
            if k.startswith('pw_') or k.startswith('gr_') or k.startswith('posix_'):
                env[k.upper()] = str(dict[k])
        return env

    def provisionuser(self, db, member, updated=False):
        os.environ.update(self.mkenv(member))
        pwline = userdb.mkpasswd(self.cfg, member)
        if pwline:
            os.environ['POSIX_ETC_PASSWD'] = pwline
        os.environ['EMAIL'] = member['email']
        os.environ['SSH_KEYS'] = '\n'.join(member['ssh'])

        scriptkeys = self.cfg.options('provisioners.user')
        for key in scriptkeys:
            pattern = self.cfg.get('provisioners.user', key)
            for script in sorted(glob.iglob(pattern)):
                self.notice('provisioning %s [%s] %s...' % (member['username'], key, script))
                if updated:
                    script += ' -update'
                os.system(script)


    def provisiongroup(self, group, updated=False):
        os.environ.update(self.mkenv(group))
        os.environ['POSIX_ETC_GROUP'] = userdb.mkgroup(self.cfg, group)

        scriptkeys = self.cfg.options('provisioners.group')
        for key in scriptkeys:
            pattern = self.cfg.get('provisioners.group', key)
            for script in sorted(glob.iglob(pattern)):
                self.notice('provisioning %s [%s] %s...' % (group['gr_name'], key, script))
                if updated:
                    script += ' -update'
                os.system(script)


    def provisionmembership(self, roster):
        pre = post = None
        scripts = []

        if self.cfg.has_option('group', 'bygroup.pre'):
            pre = self.cfg.get('group', 'bygroup.pre') % {'group': roster['name']}
            if not os.path.exists(pre):
                pre = None
        if self.cfg.has_option('group', 'bygroup.post'):
            post = self.cfg.get('group', 'bygroup.post') % {'group': roster['name']}
            if not os.path.exists(post):
                post = None

        scriptkeys = self.cfg.options('provisioners.bygroup')
        for key in scriptkeys:
            pattern = self.cfg.get('provisioners.bygroup', key) % {'group': roster['name']}
            for script in sorted(glob.iglob(pattern)):
                scripts.append(script)

        if not pre and not post and not scripts:
            return

        os.environ.update(self.mkenv(roster['group']))
        os.environ['POSIX_ETC_GROUP'] = userdb.mkgroup(self.cfg, roster['group'])

        def restore_env(restoreto):
            delete = [k for k in os.environ if k not in restoreto]
            for k in restoreto:
                os.environ[k] = restoreto[k]
            for k in delete:
                del os.environ[k]

        if pre:
            # feed member names, one per line, on stdin
            fp = os.popen(pre, 'w')
            for name in roster['members']:
                print >>fp, str(name)
            fp.close()

        if scripts:
            savedenv = dict(os.environ)
            for name in roster['members']:
                name = str(name)
                member = self.db[name]
                if not member:
                    continue
                os.environ.update(self.mkenv(member))
                pwline = userdb.mkpasswd(self.cfg, member)
                if pwline:
                    os.environ['POSIX_ETC_PASSWD'] = pwline
                os.environ['EMAIL'] = member['email']
                os.environ['SSH_KEYS'] = '\n'.join(member['ssh'])
                for script in scripts:
                    os.system(script)
                restore_env(savedenv)

        if post:
            # feed member names, one per line, on stdin
            fp = os.popen(post, 'w')
            for name in roster['members']:
                print >>fp, str(name)
            fp.close()


    def groupnamemap(self, name):
        print name
        for matcher, xform in self.mapper:
            if matcher(name):
                return xform(name)
        return name


    def opendesc(self, group):
        dir = self.cfg.get('group', 'descriptiondir')
        for ext in ['', '.txt']:
            fn = os.path.join(dir, group + ext)
            try:
                fp = open(fn, 'r')
                return group, fn, fp
            except:
                pass
        return group, None, None


    def syncdesc(self, group):
        group = os.path.basename(group)
        group, fn, fp = self.opendesc(group)
        if fp is None:
            raise IOError, 'cannot open group description file'

        desc = fp.read()
        fp.close()
        desc = desc.split('\n')
        desc = [line.strip() for line in desc]
        desc = filter(lambda line: not line.startswith('Your'), desc)
        desc = [line + '<br/>' for line in desc]
        desc = '\n'.join(desc)
        g = self.lookupgroups([group])
        g = g[0]
        self.client.put_group_summary(g['id'], name=g['name'], description=desc)


    def syncpolicy(self, group, guuid=None):
        pol = self.findpolicy(group)
        if guuid is None:
            g = self.lookupgroups([group])[0]
            guuid = g['id']
        self.client.put_group_policies(guuid, pol)


    def lookupgroups(self, groupnames):
        return [g for g in self.mygroups() if g['name'] in groupnames]


    def mygroups(self):
        if self.groupcache is None:
            self.groupcache = self.client.get_group_list(my_roles=['admin'])[1]
            self.groupcache += self.client.get_group_list(my_roles=['manager'])[1]
        return self.groupcache


    def groupid(self, name):
        return self.lookupgroups([name])[0]['id']


    def optparse(self, args):
        try:
            opts, args = getopt.getopt(args, 'u:f:g:q', ['user=', 'file=', 'group=', 'nowait', 'nw', 'force', 'quiet'])
        except getopt.GetoptError, e:
            self.error(e)
            return None

        for opt, arg in opts:
            if opt in ('-f', '--file'):
                self.files.append(arg)

            if opt in ('-u', '--user'):
                self.user = arg

            if opt in ('-g', '--group'):
                self.topgroup = arg

            if opt in ('--nowait', '--nw'):
                self.waitlock = False

            if opt in ('--quiet', '-q'):
                self.quiet = True

            if opt in ('--force',):
                self.forceupdate = True

        return args


    def dispatch(self, command, args):
        self.commands.append(command)
        cstr = ' '.join(self.commands)
        attr = '_'.join(['cmd'] + self.commands)
        try:
            driver = getattr(self, attr)
        except AttributeError:
            self.error('invalid command: %s' % cstr)
            self.usage()
            return 2
        print driver
        return driver(args)


    def usage(self):
        # XXX need to fabricate this from cmd drivers
        arg0 = self.program
        print >>sys.stderr, 'usage: %s [-u|--user=api-user] [-g|--group=top-group] [-f|--file=configfile] [--nw|--nowait] [-q|--quiet] [--force] ...' % arg0
        lines = []
        for attr in dir(self):
            if not attr.startswith('cmd_'):
                continue
            f = getattr(self, attr)
            doc = getattr(f, '__doc__', None)
            if not doc:
                continue
            lines.extend(doc.split('\n'))
        lines.sort()
        for line in lines:
            print line.replace('@', '       ' + arg0 + ' [opts]')
        #print >>sys.stderr, allsyntax % locals()


    def findpolicy(self, group):
        policydir = self.cfg.get('group', 'policydir')

        path = group.split('.')
        search = []
        for i in xrange(len(path), 0, -1):
            search.append('policy.' + '.'.join(path[:i]) + '.json')
        search.append('policy.json')
        for fn in search:
            fn = os.path.join(policydir, fn)
            if os.path.exists(fn):
                fp = open(fn)
                pol = json.loads(fp.read())
                fp.close()
                return pol
        return None


    def main(self, args):
        args = self.optparse(args)
        if args is None:
            self.usage()
            return 2
        print args
        self.cfg = config()

        if not self.files:
            self.files = [sys.argv[0] + '.ini']
        self.cfg.read(self.files)

        if not self.user:
            self.user = self.cfg.get('gosync', 'client')
        if not self.topgroup:
            self.topgroup = self.cfg.get('group', 'root')

        if not args:
            # args is empty list
            self.usage()
            return 2

        # create group name mappings
        map = {}
        for expr, xform in self.cfg.items('groupnamemaps'):
            print expr, xform
            map[expr] = (Matcher.matchfunc(expr), eval(xform))
        self.mapper = []
        for mapping in self.cfg.getlist('group', 'namemaps'):
            self.mapper.append(map[mapping])

        nexusconfig = self.cfg.nexusconfig(self.user)
        self.client = GlobusOnlineRestClient(config=nexusconfig)

        command = args.pop(0)
        print command
        return self.dispatch(command, args)


    def cmd_shell(self, args):
        '''@ shell'''
        if not ipython:
            self.notice('install IPython for shell capability')
            return 10

        nx = self.client
        return ipython()


    def cmd_group_get(self, args):
        '''@ group get <groupname>'''
        r = self.lookupgroups(args)
        for group in r:
            print group['name'], group['id']
        return 0

    def cmd_group_new(self, args):
        '''@ group new [-top] [-parent groupname] <groupname> [<groupname> ...] [: <user> ...]'''
        #self.lock()
        if args[0] == '-top':
            subgroup = False
            fparent = None
            args.pop(0)
        elif args[0] == '-parent':
            subgroup = True
            fparent = args[1]
            args = args[2:]
        else:
            subgroup = True
            fparent = None

        fp = open(self.cfg.get('group', 'descriptionfile'), 'r')
        desc = fp.read()
        fp.close()

        if ':' in args:
            off = args.index(':')
            groups = args[:off]
            members = args[off+1:]
        else:
            groups = args
            members = []

        for group in groups:
            if fparent:
                parent = fparent
                puuid = self.groupid(fparent)
                name = group
                g = self.client.post_group(group, parent=puuid)[1]
            elif '.' in group:
                parent, name = group.split('.', 1)
                puuid = self.groupid(parent)
                g = self.client.post_group(group, parent=puuid)[1]
            else:
                name = group
                g = self.client.post_group(group)[1]

            if subgroup:
                print 'Creating child group %s of %s' % (group, parent)
            else:
                print 'Creating root group %s' % group

            try:
                uuid = g['id']
            except KeyError:
                if 'message' in g:
                    print >>sys.stderr, 'Error creating group:', g['message']
                else:
                    print >>sys.stderr, 'Error creating group. Please try again - this happens sometimes.'
                return 20

            # set policy
            print '... setting group policy'
            self.syncpolicy(group, guuid=uuid)

            # set description
            d = {'projname': name, 'date': time.strftime('%B %d, %Y')}
            print '... setting default group description'
            self.client.put_group_summary(uuid, name=g['name'], description=(desc % d))

            # set admins
            users = self.cfg.groupgetlist(g['name'], 'autoadmins')
            if users:
                self.client.post_membership(uuid, usernames=users)
            for arg in users:
                print '... adding %s as default admin' % arg
                self.client.put_group_membership_role(uuid, arg, 'admin')

            # Try to push local description
            try:
                self.syncdesc(g['name'])
                print '... set custom group description'
            except:
                pass

            # add requested members to parent group
            if subgroup and members:
                self.client.post_membership(puuid, usernames=members)
                for arg in members:
                    print '... adding member %s to %s' % (arg, parent)
                    self.client.put_group_membership_role(puuid, arg, 'member')

            # add requested members to target group
            if members:
                self.client.post_membership(uuid, usernames=members)
            for arg in members:
                print '... adding member %s to %s' % (arg, group)
                self.client.put_group_membership_role(uuid, arg, 'member')

        return 0

    def cmd_group_syncdesc(self, args):
        '''@ group syncdesc <groupname> [<groupname> ...]'''
        #self.lock()
        for group in args:
            try:
                self.syncdesc(group)
            except:
                self.error('Error setting description for %s' % group)
        return 0

    def cmd_group_syncpolicy(self, args):
        '''@ group syncpolicy <groupname> [<groupname> ...]'''
        #self.lock()
        for group in args:
            self.syncpolicy(group)
        return 0

    def cmd_group_members(self, args):
        '''@ group members <groupname> [<groupname> ...]'''
        #self.lock()
        for group in args:
            uuid = self.groupid(group)
            headers, response = self.client.get_group_members(uuid)
            members = response['members']
            members = [member for member in members if member and member['username']]
            members.sort(lambda a, b: cmp(a['status'], b['status']) or cmp(a['username'], b['username']))
            for member in members:
                print '%s (%s) %s' % (group, member['status'], member['username'])
        return 0

    def cmd_group_member(self, args):
        '''@ group member <groupname> <user> [<user> ...]'''
        #self.lock()
        group = args.pop(0)
        uuid = self.groupid(group)
        # add them first
        self.client.post_membership(uuid, usernames=args)
        for arg in args:
            self.client.put_group_membership_role(uuid, arg, 'member')
        return 0

    def cmd_group_manager(self, args):
        '''@ group manager <groupname> <user> [<user> ...]'''
        #self.lock()
        group = args.pop(0)
        uuid = self.groupid(group)
        # add them first
        self.client.post_membership(uuid, usernames=args)
        for arg in args:
            self.client.put_group_membership_role(uuid, arg, 'manager')
        return 0

    def cmd_group_admin(self, args):
        '''@ group admin <groupname> <user> [<user> ...]'''
        #self.lock()
        group = args.pop(0)
        uuid = self.groupid(group)
        # add them first
        self.client.post_membership(uuid, usernames=args)
        for arg in args:
            self.client.put_group_membership_role(uuid, arg, 'admin')
        return 0

    def cmd_group_delmember(self, args):
        '''@ group delmember <groupname> <user> [<user> ...]'''
        #self.lock()
        group = args.pop(0)
        uuid = self.groupid(group)
        for user in args:
            self.client.put_group_membership(uuid, user, '', 'member', 'rejected', '')
        return 0

    def cmd_group_list(self, args):
        '''@ group list [-baseurl url | -portal hostname] [-format {html|csv|xml|json|text}] [filters ...]'''
        #self.lock()
        groups = self.mygroups()

        format = 'html'
        portal = self.cfg.get('gosync', 'portal')
        baseurl = None

        if args and args[0] == '-format':
            args.pop(0)
            format = args.pop(0)

        if args and args[0] == '-baseurl':
            args.pop(0)
            baseurl = args.pop(0)

        if args and args[0] == '-portal':
            args.pop(0)
            portal = args.pop(0)

        if baseurl is None:
            baseurl = 'https://%s/Groups#id=' % portal

        base = self.cfg.getlist('group', 'catalog.filters')
        filter = []
        if len(args) == 0:
            args = ['*']
        for arg in args:
            if arg == '*':
                filter += base
            else:
                filter.append(arg)
        print filter
        matcher = Matcher(filter)
        print groups[1]
        groups = matcher(groups, key=lambda g: g['name'])
        print groups[1]
        groups.sort(lambda a, b: cmp(a['name'], b['name']))

        dehtml = re.compile('<[^>]+>')

        if format == 'html':
            print '<link rel="stylesheet" href="projects.css" />'
            print '<table id="grouplist" cellpadding="0" cellspacing="0">'
            print '<tr><th>Project Name</th><th>Description</th></tr>'
            for grp in groups:
                url = baseurl + grp['id']
                name = grp['name']
                name = self.groupnamemap(name)
                print '<tr>'
                print '<td><a name="' + name + '" href="' + url + '">' + name + '</a></td>'
                print '<td>' + grp['description'].encode('utf-8') + '</td>'
                print '</tr>'
            print '</table>'

        if format == 'text':
            for grp in groups:
                textdesc = dehtml.sub('', grp['description'].encode('ascii', 'ignore'))
                textdesc = textdesc.replace('\n', '\\n')
                textdesc = textdesc.replace('\r', '\\r')
                print '%s %s %s' % (
                      grp['name'],
                      baseurl + g['id'],
                      textdesc)

        if format == 'csv':
            print 'groupname,url,description'
            for grp in groups:
                textdesc = dehtml.sub('', grp['description'].encode('ascii', 'ignore'))
                textdesc = textdesc.replace(',', '\,')
                textdesc = textdesc.replace('\n', '\\n')
                textdesc = textdesc.replace('\r', '\\r')
                print '%s,%s,%s' % (
                      grp['name'],
                      baseurl + grp['id'],
                      textdesc)

        if format == 'xml':
            print '<?xml version="1.0" encoding="utf-8"?>'
            print '<groups>'
            for grp in groups:
                htmldesc = grp['description']
                htmldesc = htmldesc.replace('&', '&amp;')
                htmldesc = htmldesc.replace('<', '&lt;')
                htmldesc = htmldesc.replace('>', '&gt;')
                textdesc = dehtml.sub('', grp['description'].encode('ascii', 'ignore'))
                textdesc = textdesc.replace('&', '&amp;')
                textdesc = textdesc.replace('<', '&lt;')
                textdesc = textdesc.replace('>', '&gt;')
                print '  <group>'
                print '    <name>' + grp['name'].encode('utf-8') + '</name>'
                print '    <url>' + baseurl + grp['id'] + '</url>'
                print '    <description>'
                print '      <html>' + htmldesc.encode('utf-8') + '</html>'
                print '      <text>' + textdesc.encode('utf-8') + '</text>'
                print '    </description>'
                print '  </group>'
            print '</groups>'

        o = {'groups': []}
        if format == 'json':
            for grp in groups:
                htmldesc = grp['description']
                textdesc = dehtml.sub('', grp['description'].encode('ascii', 'ignore'))
                g = {
                    'name': grp['name'].encode('utf-8'),
                    'url': baseurl + grp['id'],
                    'description': {
                        'html': htmldesc.encode('utf-8'),
                        'text': textdesc.encode('utf-8'),
                    },
                }
                o['groups'].append(g)
            print json.dumps(o, indent=4)

        return 255


    def cmd_group_accept(self, args):
        '''@ group accept <groupname> <user> <email>'''
        #self.lock()
        group = args.pop(0)
        uuid = self.groupid(group)
        self.client.put_group_membership(uuid, args[0], args[1], 'member', 'active', 'active')
        return 0


    def cmd_group_accept2(self, args):
        '''@ group accept <groupname> <user> [<...>]'''
        #self.lock()
        group = args.pop(0)
        uuid = self.groupid(group)
        for arg in args:
            self.client.approve_join(uuid, arg)
        return 0


    def cmd_user_dump(self, args):
        '''@ user dump [--all] [--details] [-t|--type {json,csv}]'''
        groups = allgroups()

        getdetails = False
        wanted = ['active']
        format = 'json'

        try:
            opts, args = getopt.getopt(args, 't:', ['all', 'details', 'type='])
        except getopt.GetoptError, e:
            self.error(e)
            return 2

        for opt, arg in opts:
            if opt in ('--all',):
                wanted = []
            if opt in ('--details'):
                wantdetails = True
            if opt in ('-t', '--type'):
                format = arg

        headers, response = self.client.get_group_members(self.groupid(self.topgroup))
        members = response['members']
        selected = []
        for member in members:
            if not member:
                continue
            if len(wanted) and member['status'] not in wanted:
                continue
            selected.append(member)

        selected.sort(lambda a, b: cmp(a['username'], b['username']))

        if getdetails:
            members = selected
            selected = []
            for member in members:
                try:
                    prof = self.client.get_user_profile(member['username'])[1]
                except socket.timeout:
                    # if we time out, pause and resume, skipping current
                    self.error('TIMEOUT - PAUSE 5s')
                    time.sleep(5)
                    continue

                if prof.has_key('credentials'):
                    member['ssh'] = sorted([cred['ssh_key'] for cred in prof['credentials'] if cred['credential_type'] == 'ssh2'])
                else:
                    member['ssh'] = []

                selected.append(member)
                time.sleep(0.5)

        for i in xrange(len(selected)):
            selected[i] = userdb.clean(selected[i])
            selected[i]['projects'] = []
            for gr, mem in groups.items():
                if not gr.startswith('@'):
                    continue
                gr = gr.lstrip('@')
                if gr == 'connect':
                    continue
                if selected[i]['username'] in mem:
                    selected[i]['projects'].append(gr)

        if format == 'json':
            print json.dumps(selected)
        elif format == 'csv':
            print 'username,status,fullname,role,email,projects'
            for member in selected:
                x = [member.get(x) for x in 'username status name role email'.split()]
                x.append(' '.join(member['projects']))
                print ','.join([str(uniclean(_)) for _ in x])


    def _cmd_cmd(self, args):
        subcmd = args.pop(0)
        return self.dispatch(subcmd, args)
    cmd_user = _cmd_cmd
    cmd_group = _cmd_cmd


    def cmd_sync(self, args):
        self.db = userdb(self.cfg.get('user', 'db'), error=self.error, notice=self.notice)

        subcmd = args.pop(0)
        rc = self.dispatch(subcmd, args)
        self.commands.pop()    # remove last subcmd
        self.unlock()          # unlock if needed
        return rc


    def cmd_deluser(self, args):
        '''@ deluser <user> [<user> ...]'''
        self.db = userdb(self.cfg.get('user', 'db'), error=self.error, notice=self.notice)
        self.lock()
        for u in args:
            if u in self.db:
                del self.db[u]
        self.db.sync()
        self.unlock()
        return 0


    def cmd_sync_users(self, args):
        '''@ sync users
@ sync users [--new] [--updated] [--only <user> [...]]'''
        self.lock()
        out = []
        pending = []
        selected = []
        didselect = False

        headers, response = self.client.get_group_members(self.groupid(self.topgroup))
        members = response['members']
        members = [member for member in members if member]

        # separate new and old users
        newusers = []
        oldusers = []
        for member in members:
            if member['status'] != 'active':
                continue
            username = str(member['username'])
            if '@' in username:
                sys.stderr.write("username has @ in it, skipping\n")
                continue
            if username in self.db:
                oldusers.append(member)
            else:
                newusers.append(member)

        # shuffle member list so that if we break down and die,
        # we'll still get a different set each time
        random.shuffle(oldusers)

        try:
            opts, args = getopt.getopt(args, '', ['new', 'updated', 'only'])
        except getopt.GetoptError, e:
            self.error(e)
            return None

        for opt, arg in opts:
            if opt in ('--new',):
                selected += newusers
                didselect = True

            if opt in ('--updated',):
                selected += oldusers
                didselect = True

            if opt in ('--only',):
                selected += [member for member in members if member['username'] in args]
                didselect = True

        if not didselect:
            selected += newusers + oldusers

        if not selected:
            return 10

        for member in selected:
            username = str(member['username'])
            if member['status'] != 'active':
                continue
            try:
                prof = self.client.get_user_profile(username)[1]
            except socket.timeout:
                # if we time out, pause and resume, skipping current
                print 'TIMEOUT PAUSE 5s'
                time.sleep(5)
                continue
            if prof.has_key('credentials'):
                member['ssh'] = sorted([cred['ssh_key'] for cred in prof['credentials'] if cred['credential_type'] == 'ssh2'])
            else:
                member['ssh'] = []
            member = userdb.clean(member)
            added = updated = False
            if username in self.db:
                updated = self.db.upduser(member, force=self.forceupdate)
            else:
                added = self.db.adduser(member)
            if added or updated:
                pending.append((member, updated))
            time.sleep(0.5)

        pre = post = None
        if self.cfg.has_option('user', 'pre'):
            pre = self.cfg.get('user', 'pre')
        if self.cfg.has_option('user', 'post'):
            post = self.cfg.get('user', 'post')

        if pending:
            if pre:
                os.system(pre)
            for member, updated in pending:
                self.provisionuser(self.db, member, updated=updated)
            if post:
                os.system(post)

        self.db.sync()
        for line in out:
            print line


    def cmd_sync_groups(self, args):
        '''@ sync groups
@ sync groups [<group> ...]'''
        if args:
            # Sync only named groups and their parents. E.g., if
            # given 'duke uchicago osg.test' as arguments, we will
            # sync the groups 'duke', 'uchicago', 'osg', and 'osg.test'.
            group_names = set()
            for arg in args:
                grp = []
                for w in arg.split('.'):
                    grp.append(w)
                    group_names.add('.'.join(grp))
            full_groups = self.mygroups()
            groups = []
            for group in full_groups:
                if group['name'] in group_names:
                    groups.append(group)
        else:
            groups = self.mygroups()
        self.lock()
        pending = []
        memberships = []
        for grp in groups:
            name = self.groupnamemap(grp['name'])
            try:
                members = self.client.get_group_members(grp['id'])[1]
            except socket.timeout:
                # if we time out, pause and resume, skipping current
                print 'TIMEOUT PAUSE 5s'
                time.sleep(5)
                continue
            members = members.get('members', [])
            members = [u['username'] for u in members if u['username'] and u['status'] == 'active']
            members.sort()
            pgrp = {'gr_name': '@' + name, 'gr_gid': userdb.gengid(name), 'gr_mem': ','.join(members)}
            pending.append((pgrp, True))

            roster = {
                'name': name,
                'group': pgrp,
                'members': members,
            }
            memberships.append(roster)


        # do groups
        pre = post = None
        if self.cfg.has_option('group', 'pre'):
            pre = self.cfg.get('group', 'pre')
        if self.cfg.has_option('group', 'post'):
            post = self.cfg.get('group', 'post')

        if pre:
            os.system(pre)
        if pending:
            for group, updated in pending:
                self.provisiongroup(group, updated=updated)
        if post:
            os.system(post)

        # do group memberships
        for roster in memberships:
            self.provisionmembership(roster)


    def cmd_waitlock(self, args):
        '''@ waitlock'''
        self.lock()

    __call__ = main


if __name__ == '__main__':
    main = gosync()
    try:
        if 'cProfile' in globals():
            cProfile.run('rc = main(sys.argv[1:])')
        else:
            rc = main(sys.argv[1:])
    except LockError:
        sys.exit(1)
    except:
        main.unlock()
        raise

    main.unlock()
    sys.exit(rc)
