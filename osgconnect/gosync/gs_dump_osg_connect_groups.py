#!/usr/bin/env python
from __future__ import print_function
import os
import sys
import logging
# import getopt
# import time
# import glob
import json
import re
# import fnmatch
# import errno
# import random
# import socket
# import grp
# import pwd

from optparse import OptionParser

from util import *


def list_html(groups, baseurl, filters):
    print('<link rel="stylesheet" href="projects.css" />')
    print('<link rel="stylesheet" href="projects.css" />')
    print('<link rel="stylesheet" href="projects.css" />')
    print('<table id="grouplist" cellpadding="0" cellspacing="0">')
    print('<tr><th>Project Name</th><th>Description</th></tr>')
    for g in groups:
        url = baseurl + g['id']
        name = strip_filters(g['name'], filters)
        print('<tr>')
        print(('<td><a name="%s" href="%s">%s</a></td>') % (name,
                                                            url,
                                                            name))
        print('<td>' + g['description'].encode('utf-8') + '</td>')
        print('</tr>')
    print('</table>')


def list_text(groups, baseurl, dehtml):
    for g in groups:
        textdesc = dehtml.sub('',
                              g['description'].encode('ascii',
                                                      'ignore'))
        textdesc = textdesc.replace('\n', '\\n')
        textdesc = textdesc.replace('\r', '\\r')
        print('%s %s %s' % (
              g['name'],
              baseurl + g['id'],
              textdesc))


def list_csv(groups, baseurl, dehtml):
    print('groupname,url,description')
    for g in groups:
        textdesc = dehtml.sub('',
                              g['description'].encode('ascii',
                                                      'ignore'))
        textdesc = textdesc.replace(',', '\,')
        textdesc = textdesc.replace('\n', '\\n')
        textdesc = textdesc.replace('\r', '\\r')
        print('%s,%s,%s' % (
              g['name'],
              baseurl + g['id'],
              textdesc))


def list_xml(groups, baseurl, dehtml):
    print('<?xml version="1.0" encoding="utf-8"?>')
    print('<groups>')
    for g in groups:
        htmldesc = g['description']
        htmldesc = htmldesc.replace('&', '&amp;')
        htmldesc = htmldesc.replace('<', '&lt;')
        htmldesc = htmldesc.replace('>', '&gt;')
        textdesc = dehtml.sub('',
                              g['description'].encode('ascii',
                                                      'ignore'))
        textdesc = textdesc.replace('&', '&amp;')
        textdesc = textdesc.replace('<', '&lt;')
        textdesc = textdesc.replace('>', '&gt;')
        print('  <group>')
        print('    <name>' + g['name'].encode('utf-8') + '</name>')
        print('    <url>' + baseurl + g['id'] + '</url>')
        print('    <description>')
        print('      <html>' + htmldesc.encode('utf-8') + '</html>')
        print('      <text>' + textdesc.encode('utf-8') + '</text>')
        print('    </description>')
        print('  </group>')
    print('</groups>')


def list_json(groups, baseurl, dehtml):
    o = {'groups': []}
    for g in groups:
        htmldesc = g['description']
        textdesc = dehtml.sub('',
                              g['description'].encode('ascii',
                                                      'ignore'))
        g = {
            'name': g['name'].encode('utf-8'),
            'url': baseurl + g['id'],
            'description': {
                'html': htmldesc.encode('utf-8'),
                'text': textdesc.encode('utf-8'),
            },
        }
        o['groups'].append(g)
    print(json.dumps(o, indent=4))


def get_groups(options, group_cache):
    group_cache = uniclean(group_cache)
    groups = [g for g in group_cache
              if g['name'].startswith(tuple(options.filters))]
    groups.sort(key=lambda k: k['name'])
    return groups


def list_groups(options, config, client):
    group_cache = get_groups_globus(client, ['admin', 'manager'])
    groups = get_groups(options, group_cache)
    if options.baseurl is None:
        options.baseurl = os.path.join('https://',
                                       config['gosync']['server'],
                                       'Groups#id=')
    dehtml = re.compile('<[^>]+>')
    for frmt in options.format:
        if options.outfile is not None:
            sys.stdout = open(options.outfile + ".%s" % frmt, "wt")
        if frmt.lower() == "html":
            list_html(groups, options.baseurl, options.filters)
        elif frmt.lower() == 'text':
            list_text(groups, options.baseurl, dehtml)
        elif frmt.lower() == 'csv':
            list_csv(groups, options.baseurl, dehtml)
        elif frmt.lower() == 'xml':
            list_xml(groups, options.baseurl, dehtml)
        elif frmt.lower() == 'json':
            list_json(groups, options.baseurl, dehtml)
        else:
            logging.fatal(("Provided format (%s) not support. "
                           "Please choose a supported format: "
                           "html, text, csv, xml, json") % options.format)
            raise RuntimeError()
        if options.outfile is not None:
            sys.stdout.close()


def main(options, args):
    config = parse_config(options.config)
    client = get_globus_client(config)
    list_groups(options, config, client)


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
    parser.add_option("--user", dest="user", default=None,
                      help="User to use")
    parser.add_option("--selector", dest="selector", default="or",
                      help="Selection flag")
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
    main(options, args)
