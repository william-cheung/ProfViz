#! /usr/bin/env python
#
#  Tool for converting stats saving by lsprof(CProfile) to stats which is
#  readable by kcachegrind
#
#  Written by
#      David Allouche
#      Jp Calderone & Itamar Shtull-Trauring
#      Johan Dahlin
#
#  Dowloaded from https://people.gnome.org/~johan/lsprofcalltree.py
#
#  Modified by William Cheung


import optparse
import sys
import os

try:
    import cProfile
except ImportError:
    raise SystemExit("This script requires cProfile from Python 2.5")


def label(code):
    if isinstance(code, str):
        return code   # ('~', 0, code)    # built-in functions ('~' sorts at the end)
    else:
        return '%s %s:%d' % (code.co_name,
                             code.co_filename,
                             code.co_firstlineno)

filename_of_builtin_funcs = ''


class KCacheGrind(object):
    def __init__(self, profiler):
        self.data = profiler.get_stats()
        self.out_file = None

    def output(self, out_file):
        self.out_file = out_file
        print >> out_file, 'events: Ticks'
        self._print_summary()
        for entry in self.data:
            self._entry(entry)

    def _print_summary(self):
        max_cost = 0
        for entry in self.data:
            totaltime = int(entry.totaltime * 1000)
            max_cost = max(max_cost, totaltime)
        print >> self.out_file, 'summary: %d' % (max_cost,)

    def _entry(self, entry):
        out_file = self.out_file
        code = entry.code

        if isinstance(code, str):
            print >> out_file, 'fi=%s' % filename_of_builtin_funcs
        else:
            print >> out_file, 'fi=%s' % (code.co_filename,)
        print >> out_file, 'fn=%s' % (label(code),)

        inlinetime = int(entry.inlinetime * 1000)
        if isinstance(code, str):
            print >> out_file, '0 ', inlinetime
        else:
            print >> out_file, '%d %d' % (code.co_firstlineno, inlinetime)

        # recursive calls are counted in entry.calls
        if entry.calls:
            calls = entry.calls
        else:
            calls = []

        if isinstance(code, str):
            lineno = 0
        else:
            lineno = code.co_firstlineno

        for subentry in calls:
            self._subentry(lineno, subentry)
        print >> out_file

    def _subentry(self, lineno, subentry):
        out_file = self.out_file
        code = subentry.code
        print >> out_file, 'cfn=%s' % (label(code),)
        if isinstance(code, str):
            print >> out_file, 'cfi=%s' % filename_of_builtin_funcs
            print >> out_file, 'calls=%d 0' % (subentry.callcount,)
        else:
            print >> out_file, 'cfi=%s' % (code.co_filename,)
            print >> out_file, 'calls=%d %d' % (
                subentry.callcount, code.co_firstlineno)

        totaltime = int(subentry.totaltime * 1000)
        print >> out_file, '%d %d' % (lineno, totaltime)


def main():
    usage = "%s [-o output_file_path] scriptfile [arg] ..."
    parser = optparse.OptionParser(usage=usage % os.path.basename(sys.argv[0]))
    parser.allow_interspersed_args = False
    parser.add_option('-o', '--outfile', dest="outfile",
                      help="save stats to <outfile>", default=None)
    #parser.add_option('-i', '--ignore-builtin',
    #                  action="store_true", dest="ignore_builtins", default=False,
    #                  help="don't dump stats of built-in funcs")

    if not sys.argv[1:]:
        parser.print_usage()
        sys.exit(2)

    options, args = parser.parse_args()

    sys.argv[:] = args

    prof = cProfile.Profile()
    try:
        try:
            prof = prof.run('execfile(%r)' % (sys.argv[0],))
        except SystemExit:
            pass
    finally:
        if options.outfile:
            kg = KCacheGrind(prof)
            kg.output(file(options.outfile, 'w'))
        else: # no outfile provided
            prof.print_stats()

if __name__ == '__main__':
    sys.exit(main())
