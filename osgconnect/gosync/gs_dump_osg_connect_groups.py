#!/usr/bin/env python
from __future__ import print_function
import os
import sys
import logging as log
import json
import re
import util as gs_util

from optparse import OptionParser
from globus_db import globus_db_nexus as globus_db


def list_html(groups, baseurl, filters):
    print('<link rel="stylesheet" href="projects.css" />')
    print('<link rel="stylesheet" href="projects.css" />')
    print('<link rel="stylesheet" href="projects.css" />')
    print('<table id="grouplist" cellpadding="0" cellspacing="0">')
    print('<tr><th>Project Name</th><th>Description</th></tr>')
    for g in groups:
        url = baseurl + g['id']
        name = gs_util.strip_filters(g['name'], filters)
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


def list_groups(options, go_db=None, config=None, client=None):
    if go_db is None:
        log.info(("No globus_db object provided. Checking if config "
                  "and Globus Nexus client are provided"))
        if config is None and client is None:
            log.fatal("No config paramaters or Globus Nexus client provided.")
            raise RuntimeError()
        elif config is None:
            log.fatal("No config paramaters provided.")
            raise RuntimeError()
        elif client is None:
            log.fatal("No Globus Nexus client provided.")
            raise RuntimeError()
        elif config is not None and client is None:
            go_db = globus_db(config)
        elif config is not None and client is not None:
            raise NotImplementedError()
    if go_db is not None and options.group is not None:
        groups = go_db.get_groups(filters_name=options.group,
                                  dump_root_group=False)
    elif go_db is not None and options.group is None:
        groups = go_db.get_groups(dump_root_group=False)
    if config is None:
        config = go_db.config
    if options.baseurl is None:
        options.baseurl = os.path.join('https://',
                                       config['gosync']['server'],
                                       'Groups#id=')
    dehtml = re.compile('<[^>]+>')
    if options.filters is not None:
        filters = options.filters
    else:
        if config is not None:
            filters = config["groups"]["filter_prefix"]
        else:
            filters = go_db.config["groups"]["filter_prefix"]
    print(groups)
    for frmt in options.format:
        if options.outfile is not None:
            sys.stdout = open(options.outfile + ".%s" % frmt, "wt")
        if frmt.lower() == "html":
            list_html(groups, options.baseurl, filters)
        elif frmt.lower() == 'text':
            list_text(groups, options.baseurl, dehtml)
        elif frmt.lower() == 'csv':
            list_csv(groups, options.baseurl, dehtml)
        elif frmt.lower() == 'xml':
            list_xml(groups, options.baseurl, dehtml)
        elif frmt.lower() == 'json':
            list_json(groups, options.baseurl, dehtml)
        else:
            log.fatal(("Provided format (%s) not support. "
                       "Please choose a supported format: "
                       "html, text, csv, xml, json") % options.format)
            raise RuntimeError()
        if options.outfile is not None:
            sys.stdout.close()


def main(options, args):
    if options.format is None:
        log.fatal(("Please select a single or set of formats to "
                   "write data out as. Choose a supported format: "
                   "html, text, csv, xml, json"))
        raise RuntimeError()
    if len([f for f in options.format
            if f in ["html", "text", "csv", "xml", "json"]]) == 0:
                log.fatal(("Please choose a supported format: "
                           "html, text, csv, xml, json"))
                raise RuntimeError()
    config = gs_util.parse_config(options.config)
    g_db = globus_db(config, get_members=False)
    # client = get_globus_client(config)
    list_groups(options, go_db=g_db)
    # list_groups(options, config, client)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("--config", dest="config", default="gosync.conf",
                      help="config file to use",)
    parser.add_option("-v", "--verbosity", dest="verbosity",
                      help="Set logging level", default=3)
    parser.add_option("--format", dest="format", default=None,
                      action="callback", callback=gs_util.callback_optparse,
                      help="Output format to use given as a list")
    parser.add_option("-o", "--outfile", dest="outfile", default=None,
                      help="Output file to write things too")
    parser.add_option("--force", dest="force", action="store_true",
                      default=False, help="Force update information")
    parser.add_option("--baseurl", dest="baseurl", default=None,
                      help="Base URL to use")
    # parser.add_option("--portal", dest="portal", default=None,
    #                   help="Portal to use")
    # parser.add_option("--parent", dest="parent", default=None,
    #                   help="Parent group to use")
    # parser.add_option("--top", dest="top", default=None,
    #                   help="Top group to use")
    parser.add_option("--group", dest="group", default=None,
                      help="Group to use")
    # parser.add_option("--user", dest="user", default=None,
    #                   help="User to use")
    # parser.add_option("--selector", dest="selector", default="or",
    #                   help="Selection flag")
    parser.add_option("--filters", dest="filters", default=None,
                      action="callback", callback=gs_util.callback_optparse,
                      help="Output format to use given as a list")
    (options, args) = parser.parse_args()
    level = {
        1: log.ERROR,
        2: log.WARNING,
        3: log.INFO,
        4: log.DEBUG
    }.get(options.verbosity, log.DEBUG)
    main(options, args)
