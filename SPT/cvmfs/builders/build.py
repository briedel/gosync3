#!/usr/bin/env python
"""
Build the SPT CVMFS repository on this OS.

Example:
  ./build.py --dest /cvmfs/icecube.opensciencegrid.org --src ../icecube.opensciencegrid.org
"""

import sys
import os
from build_util import get_module

# append this directory to the path
if os.path.dirname(__file__) not in sys.path:
    sys.path.append(os.path.dirname(__file__))


def get_variants():
    build_variants = {}
    for module in os.listdir(os.path.join(os.path.dirname(__file__),'variants')):
        if module.endswith('.py') and module != '__init__.py':
            tmp = os.path.splitext(module)[0]
            try:
                build_variants[tmp] = get_module('variants.'+tmp)
            except Exception:
                print('failed to import variants.'+tmp)
                raise
    return build_variants


def absolute(p):
    return os.path.abspath(os.path.expandvars(os.path.expanduser(p)))


def main():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("--dest", type="string", default=None,
                      help="CVMFS repository destination (inside repo)")
    parser.add_option("--src", type="string", default=None, 
                      help="Source for repository template")
    parser.add_option("--variant", type="string", default=None, 
                      help="Specific variant to build")
    parser.add_option("--scratch", type="string", default=None, 
                      help="Scratch directory (default: /tmp)")
    parser.add_option("--svnup", type="string", default=None, 
                      help="SVN update {True,False}")
    
    (options, args) = parser.parse_args()
    
    build_variants = get_variants()
    
    options.dest = absolute(options.dest)
    options.src = absolute(options.src)
    
    if options.scratch:
        os.environ['TMPDIR'] = options.scratch
        os.environ['TEMP'] = options.scratch
        os.environ['TMP'] = options.scratch
    
    kwargs = {}
    if options.svnup and options.svnup.lower() in ('1','true','on','yes','y','t'):
        kwargs['svn_up'] = True
    elif options.svnup and options.svnup.lower() in ('0','false','off','no','n','f'):
        kwargs['svn_up'] = False
    elif options.svnup:
        raise Exception('unknown option for svnup: %s'%options.svnup)
    
    not_found = True
    for v in build_variants:
        if (options.variant and options.variant in v) or not options.variant:
            build_variants[v](src=options.src, dest=options.dest,**kwargs)
            not_found = False
    if not_found:
        raise Exception('variant %s not found'%(str(options.variant)))

if __name__ == '__main__':
    main()