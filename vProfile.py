#! /usr/bin/env python
#
# Module for generating profile stats format for ProfViz
# 
# Written by William Cheung, Mar. 2016
#

"""Tools for processing results of the profilers from Python Library:

Terms in our symbols:
    'pstats' refers to profiler results dumped by 'profile' or 'cProfile',
    and 'vstats' profiler results dumped by 'vProfile'

    To provide similar interfaces with 'profile' and 'cProfile', we use
    'dump_stats' instead of 'dump_vstats' as the name of the function that
    dumps profiler results to a file in class 'Profile' 
"""

import sys
import os
import json
from optparse import OptionParser


__all__ = ["load_pstats", "loads_pstats", "load_vstats", "loads_vstats"
           "dump_vstats", "pstats2vstats", "vstats2callermap", "vstats_summary",
           "simple_code_format", "simple_funcname",
           "run", "runctx", "Profile"]

#__________________________________________________________________________
# Utility classes


class fake_code:
    def __init__(self, label):
        filename, lineno, funcname = label
        
        # we _SHOULD_ ensure the consistency of our results
        if filename == '~':  # for cProfile case
            filename = ''        

        self.co_filename = filename
        self.co_firstlineno = lineno
        self.co_name = str(funcname)

    def __str__(self):
        # generate key for vstats
        if self.co_filename == '':
            return self.co_name
        else:
            return "%s [%s:%s]" % (self.co_name,
                                   self.co_filename, self.co_firstlineno)


class fake_entry:
    def __init__(self, stats_item):
        # convert standard pstats entry to fake_entry
        func, cc, nc, tt, ct = stats_item
        self.code = fake_code(func)
        self.callcount = nc
        self.reccallcount = nc - cc
        self.inlinetime = tt
        self.totaltime = ct
        self.callees = {}  # map: func -> fake_subentry


class fake_entry2:
    # compatible with fake_entry, defined for json decoding
    def __init__(self, code,
                 callcount, reccallcount, inlinetime, totaltime, callees):
        self.code = code
        self.callcount = callcount
        self.reccallcount = reccallcount
        self.inlinetime = inlinetime
        self.totaltime = totaltime
        self.callees = callees


class fake_subentry:
    def __init__(self, callcount, totaltime):
        self.callcount = callcount  # times called by a caller
        self.totaltime = totaltime  # total time spent when called by a caller
        

#__________________________________________________________________________
# Customized JSON encoder & JSON decoder

class json_encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (fake_code, fake_entry, fake_subentry)):
            return obj.__dict__ 
        elif isinstance(obj, tuple):
            return list(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def json_decoder(obj):
    if 'co_filename' in obj:
        return fake_code((obj['co_filename'],
                          obj['co_firstlineno'],
                          obj['co_name']))
    elif 'callees' in obj:
        return fake_entry2(obj['code'],
                           obj['callcount'],
                           obj['reccallcount'],
                           obj['inlinetime'],
                           obj['totaltime'],
                           obj['callees'])
    elif 'callcount' in obj:
        return fake_subentry(obj['callcount'], obj['totaltime'])
    return obj

#__________________________________________________________________________
# Simple interface


def load_pstats(filename):
    fp = open(filename, 'rb')
    try:
        import marshal
        stats = marshal.load(fp)
    finally:
        fp.close()
    return stats


def loads_pstats(content):
    # unmarshal pstats form a string
    import marshal
    return marshal.loads(content)


def load_vstats(filename):
    fp = open(filename, 'r')
    try:
        return json.load(fp, object_hook=json_decoder)
    finally:
        fp.close()


def loads_vstats(content):
    return json.loads(content, object_hook=json_decoder)


def dump_vstats(vstats, filename):
    fp = open(filename, 'w')
    try:
        json.dump(vstats, fp, cls=json_encoder)
    finally:
        fp.close()


def pstats2vstats(stats):
    # convert pstats to vstats
    vstats, callee_map = {}, {}
    for func, (cc, nc, tt, ct, callers) in stats.iteritems():
        stats_item = (func, cc, nc, tt, ct)
        entry = fake_entry(stats_item)
        name = str(entry.code)
        vstats[name] = entry
        for caller, caller_stats in callers.iteritems():
            caller_name = str(fake_code(caller))
            if not callee_map.has_key(caller_name):
                callee_map[caller_name] = {}
            callee_map[caller_name][name] = caller_stats
    _update_callees(vstats, callee_map)
    return vstats


def _update_callees(vstats, callee_map):
    for caller, callees in callee_map.iteritems():
        if caller not in vstats:
            continue
        entry = vstats[caller]
        entry.callees = callees
        
        t_sum = 0.0
        for callee, xstats in callees.iteritems():
            callcount, totaltime = xstats, -1.0 
            if isinstance(xstats, (tuple)):  # for cProfile results
                callcount = xstats[0]
                totaltime = xstats[3]
            t_sum += totaltime
            callees[callee] = fake_subentry(callcount, totaltime)

        # test if there exist recursive calls
        if t_sum < 0 or _test_greater(t_sum, entry.totaltime - entry.inlinetime):
            # print caller, t_sum, entry.totaltime, entry.inlinetime
            for callee in callees:
                # we are in a case where there exist recursive calls, and we mark
                # total time that the callee spent when called by the caller
                # 'unknown' for simplicity. 
                callees[callee].totaltime = -1.0 # unknown


def _test_greater(x, y, rel_tol=1e-6):
    return x - y > max(x, y) * rel_tol


def vstats2callermap(vstats):
    # get the dict that maps a callee to a list of its callers
    caller_map = {}
    for func, entry in vstats.iteritems():
        for callee in entry.callees:
            if callee not in caller_map:
                caller_map[callee] = set()
            caller_map[callee].add(func)
    return caller_map


def vstats_summary(vstats):
    # summary total execution time
    summary = 0
    for _, entry in vstats.iteritems():
        summary = max(summary, entry.totaltime)
    return summary


def simple_code_format(code):
    where = '<built-in>'
    if code.co_filename:
        filename = os.path.basename(code.co_filename)
        where = '%s:%d' % (filename, code.co_firstlineno)
    return simple_funcname(code.co_name), where


def simple_funcname(funcname):
    import re
    if funcname.startswith('<method') and funcname.endswith('objects>'):
        # e.g. <method 'close' of 'file' objects>
        match = re.findall('\'(\w+(\.\w+)*)\'', funcname)
        names = [group[0] for group in match]
        return '<%s.%s>' % (names[1], names[0])
    if funcname.startswith('<built-in method'):
        # e.g. <built-in method __new__ of type objest at 0x12345678>
        match = re.findall('<built-in method (\w+) of type object at (\w+)>',
                           funcname)
        if match:
            return '<object.%s> @%s' % match[0]
        else:
            match = re.findall('<built-in method (\w+)>', funcname)
            if match:
                return '<%s>' % match[0]
    if funcname.startswith('<function'):
        match = re.findall('<function (\w+) at (\w+)>', funcname)
        if match:
            return '<%s> @%s' % match[0]
    return funcname

#__________________________________________________________________________

profile_module = 'cProfile'


def run(statement, filename=None, sort=-1):
    """Run statement under profiler optionally saving results in filename

    This function takes a single argument that can be passed to the
    "exec" statement, and an optional file name.  In all cases this
    routine attempts to "exec" its first argument and gather profiling
    statistics from the execution. If no file name is present, then this
    function automatically prints a simple profiling report, sorted by the
    standard name string (file/line/function-name) that is presented in
    each line.
    """
    prof = Profile(profile_module)
    try:
        prof = prof.run(statement)
    except SystemExit:
        pass
    if filename is not None:
        prof.dump_stats(filename)
    else:
        return prof.print_stats(sort)


def runctx(statement, globals, locals, filename=None, sort=-1):
    """Run statement under profiler, supplying your own globals and locals,
    optionally saving results in filename.

    statement and filename have the same semantics as profile.run
    """
    prof = Profile(profile_module)
    try:
        prof = prof.runctx(statement, globals, locals)
    except SystemExit:
        pass
    
    if filename is not None:
        prof.dump_stats(filename)
    else:
        return prof.print_stats(sort)


#__________________________________________________________________________
# Profiler class, which is an adaptor actually

class Profile:
    def __init__(self, module='cProfile'):
        import importlib
        profmod = importlib.import_module(module)
        self.profiler = profmod.Profile()
        self.stats = None

    def get_stats(self):
        import tempfile
        fp = tempfile.NamedTemporaryFile(delete=False)
        fp.close()
        self.profiler.dump_stats(fp.name)
        stats = load_pstats(fp.name)
        self.stats = pstats2vstats(stats)
        os.remove(fp.name)
        return self.stats

    def print_stats(self, sort=-1):
        self.profiler.print_stats(sort)

    def dump_stats(self, filename):
        dump_vstats(self.get_stats(), filename)

    def run(self, cmd):
        self.profiler = self.profiler.run(cmd)
        return self

    def runctx(self, cmd, globals, locals):
        self.profiler = self.profiler.runctx(cmd, globals, locals)
        return self

#__________________________________________________________________________


def main():
    usage = "%s [-o output_file_path] [-s sort] scriptfile [arg] ..."
    parser = OptionParser(usage=usage % os.path.basename(sys.argv[0]))
    parser.allow_interspersed_args = False
    parser.add_option('-o', '--outfile', dest="outfile",
        help="save stats to <outfile>", default=None)
    parser.add_option('-s', '--sort', dest="sort",
        help="sort order when printing to stdout, based on pstats.Stats class",
        default=-1)

    if not sys.argv[1:]:
        parser.print_usage()
        sys.exit(2)
        
    (options, args) = parser.parse_args()
    sys.argv[:] = args
    
    if len(args) > 0:
        progname = args[0]
        sys.path.insert(0, os.path.dirname(progname))
        with open(progname, 'rb') as fp:
            code = compile(fp.read(), progname, 'exec')
        globs = {
            '__file__': progname,
            '__name__': '__main__',
            '__package__': None,
        }
        runctx(code, globs, None, options.outfile, options.sort)
    else:
        parser.print_usage()
    return parser

# When invoked as main program, invoke the profiler on a script
if __name__ == '__main__':
    main()
