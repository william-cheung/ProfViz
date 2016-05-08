#
#  Module for converting vstats to dot source
#      based on code from gprof2dot.py written by Jose Fonseca
#          see https://github.com/jrfonseca/gprof2dot
#      vstats is a profiling output format defined in vProfile.py
#
#  Written by William Cheung, Mar. 2016 
#

#__________________________________________________________________________
# Code for generating dot source

import math


class Theme:
    def __init__(self,
            bgcolor = (0.0, 0.0, 1.0),
            mincolor = (0.0, 0.0, 0.0),
            maxcolor = (0.0, 0.0, 1.0),
            fontname = "Arial",
            minfontsize = 10.0,
            maxfontsize = 10.0,
            minpenwidth = 0.5,
            maxpenwidth = 4.0,
            gamma = 2.2,
            skew = 1.0):
        self.bgcolor = bgcolor
        self.mincolor = mincolor
        self.maxcolor = maxcolor
        self.fontname = fontname
        self.minfontsize = minfontsize
        self.maxfontsize = maxfontsize
        self.minpenwidth = minpenwidth
        self.maxpenwidth = maxpenwidth
        self.gamma = gamma
        self.skew = skew

    def graph_bgcolor(self):
        return self.hsl_to_rgb(*self.bgcolor)

    def graph_fontname(self):
        return self.fontname

    def graph_fontsize(self):
        return self.minfontsize

    def node_bgcolor(self, weight):
        return self.color(weight)

    def node_fgcolor(self, weight):
        return self.graph_bgcolor()

    def node_fontsize(self, weight):
        return self.fontsize(weight)

    def edge_color(self, weight):
        return self.color(weight)

    def edge_fontsize(self, weight):
        return self.fontsize(weight)

    def edge_penwidth(self, weight):
        return max(weight*self.maxpenwidth, self.minpenwidth)

    def edge_arrowsize(self, weight):
        return 0.5 * math.sqrt(self.edge_penwidth(weight))

    def fontsize(self, weight):
        return max(weight**2 * self.maxfontsize, self.minfontsize)

    def color(self, weight):
        weight = min(max(weight, 0.0), 1.0)

        hmin, smin, lmin = self.mincolor
        hmax, smax, lmax = self.maxcolor

        if self.skew < 0:
            raise ValueError("Skew must be greater than 0")
        elif self.skew == 1.0:
            h = hmin + weight*(hmax - hmin)
            s = smin + weight*(smax - smin)
            l = lmin + weight*(lmax - lmin)
        else:
            base = self.skew
            h = hmin + ((hmax-hmin)*(-1.0 + (base ** weight)) / (base - 1.0))
            s = smin + ((smax-smin)*(-1.0 + (base ** weight)) / (base - 1.0))
            l = lmin + ((lmax-lmin)*(-1.0 + (base ** weight)) / (base - 1.0))

        return self.hsl_to_rgb(h, s, l)

    def hsl_to_rgb(self, h, s, l):
        """Convert a color from HSL color-model to RGB.

        See also:
        - http://www.w3.org/TR/css3-color/#hsl-color
        """

        h = h % 1.0
        s = min(max(s, 0.0), 1.0)
        l = min(max(l, 0.0), 1.0)

        if l <= 0.5:
            m2 = l*(s + 1.0)
        else:
            m2 = l + s - l*s
        m1 = l*2.0 - m2
        r = self._hue_to_rgb(m1, m2, h + 1.0/3.0)
        g = self._hue_to_rgb(m1, m2, h)
        b = self._hue_to_rgb(m1, m2, h - 1.0/3.0)

        # Apply gamma correction
        r **= self.gamma
        g **= self.gamma
        b **= self.gamma

        return (r, g, b)

    def _hue_to_rgb(self, m1, m2, h):
        if h < 0.0:
            h += 1.0
        elif h > 1.0:
            h -= 1.0
        if h*6 < 1.0:
            return m1 + (m2 - m1)*h*6.0
        elif h*2 < 1.0:
            return m2
        elif h*3 < 2.0:
            return m1 + (m2 - m1)*(2.0/3.0 - h)*6.0
        else:
            return m1


TEMPERATURE_COLORMAP = Theme(
    mincolor = (2.0/3.0, 0.80, 0.25), # dark blue
    maxcolor = (0.0, 1.0, 0.5), # satured red
    gamma = 1.0
)

PINK_COLORMAP = Theme(
    mincolor = (0.0, 1.0, 0.90), # pink
    maxcolor = (0.0, 1.0, 0.5), # satured red
)

GRAY_COLORMAP = Theme(
    mincolor = (0.0, 0.0, 0.85), # light gray
    maxcolor = (0.0, 0.0, 0.0), # black
)

BW_COLORMAP = Theme(
    minfontsize = 8.0,
    maxfontsize = 24.0,
    mincolor = (0.0, 0.0, 0.0), # black
    maxcolor = (0.0, 0.0, 0.0), # black
    minpenwidth = 0.1,
    maxpenwidth = 8.0,
)


class DotWriter:
    """Writer for the DOT language.

    See also:
    - "The DOT Language" specification
      http://www.graphviz.org/doc/info/lang.html
    """

    def __init__(self, fp):
        self.fp = fp

    def graph(self, vstats, theme, summary=0):
        self.begin_graph()

        fontname = theme.graph_fontname()

        self.attr('graph', fontname=fontname, ranksep=0.25, nodesep=0.125)
        self.attr('node', fontname=fontname, shape="box", style="filled", fontcolor="white", width=0, height=0)
        self.attr('edge', fontname=fontname)

        if not summary: # if summary is not given
            # we take max total time of entries in vstats as summary :)
            for _, entry in vstats.iteritems():
                summary = max(summary, entry.totaltime)

        from vProfile import simple_code_format
        for func, entry in vstats.iteritems():
            labels = []
            labels.append('%s [%s]' % simple_code_format(entry.code))
            labels.append('%6.2f%%' % (100.0 * entry.totaltime / summary))
            labels.append('(%6.2f%%)' % (100.0 * entry.inlinetime / summary))
            labels.append(str(entry.callcount))

            label = '\n'.join(labels)
            weight = entry.totaltime / summary

            self.node(id(func),
                label = label,
                color = self.color(theme.node_bgcolor(weight)),
                fontcolor = self.color(theme.node_fgcolor(weight)),
                fontsize = "%.2f" % theme.node_fontsize(weight),
            )

            for callee in entry.callees:
                callee_entry = vstats[callee]
                labels = []
                labels.append('%s %s' % simple_code_format(callee_entry.code))
                labels.append('%6.2f%%' % (100.0 * callee_entry.totaltime / summary))
                labels.append('(%6.2f%%)' % (100.0 * callee_entry.inlinetime / summary))
                labels.append(str(callee_entry.callcount))

                label = '\n'.join(labels)
                weight = callee_entry.totaltime / summary
                self.edge(id(func), id(callee),
                    label = label,
                    color = self.color(theme.edge_color(weight)),
                    fontcolor = self.color(theme.edge_color(weight)),
                    fontsize = "%.2f" % theme.edge_fontsize(weight),
                    penwidth = "%.2f" % theme.edge_penwidth(weight),
                    labeldistance = "%.2f" % theme.edge_penwidth(weight),
                    arrowsize = "%.2f" % theme.edge_arrowsize(weight),
                )

        self.end_graph()

    def begin_graph(self):
        self.write('digraph {\n')

    def end_graph(self):
        self.write('}\n')

    def attr(self, what, **attrs):
        self.write("\t")
        self.write(what)
        self.attr_list(attrs)
        self.write(";\n")

    def node(self, node, **attrs):
        self.write("\t")
        self.id(node)
        self.attr_list(attrs)
        self.write(";\n")

    def edge(self, src, dst, **attrs):
        self.write("\t")
        self.id(src)
        self.write(" -> ")
        self.id(dst)
        self.attr_list(attrs)
        self.write(";\n")

    def attr_list(self, attrs):
        if not attrs:
            return
        self.write(' [')
        first = True
        for name, value in attrs.iteritems():
            if first:
                first = False
            else:
                self.write(", ")
            self.id(name)
            self.write('=')
            self.id(value)
        self.write(']')

    def id(self, id):
        if isinstance(id, (int, float)):
            s = str(id)
        elif isinstance(id, basestring):
            if id.isalnum():
                s = id
            else:
                s = self.escape(id)
        else:
            raise TypeError
        self.write(s)

    def color(self, (r, g, b)):
        def float2int(f):
            if f <= 0.0:
                return 0
            if f >= 1.0:
                return 255
            return int(255.0*f + 0.5)

        return "#" + "".join(["%02x" % float2int(c) for c in (r, g, b)])

    def escape(self, s):
        s = s.encode('utf-8')
        s = s.replace('\\', r'\\')
        s = s.replace('\n', r'\n')
        s = s.replace('\t', r'\t')
        s = s.replace('"', r'\"')
        return '"' + s + '"'

    def write(self, s):
        self.fp.write(s)

#__________________________________________________________________________
# Utility functions


def _filter_predicate(entry, threshold, summary):
    if summary > 0:
        return entry.totaltime / summary * 100.0 < threshold
    return entry.totaltime < threshold


def _filter_vstats(vstats, root, threshold, summary):
    if root not in vstats:
        return _aux_filter_vstats(vstats, threshold, summary)

    import collections
    import copy
    result = {}
    visited, queue = set(), collections.deque()

    if not _filter_predicate(vstats[root], threshold, summary):
        queue.append(root)
        visited.add(id(root))
    while len(queue):
        func = queue.popleft()
        result[func] = copy.deepcopy(vstats[func])
        for callee in vstats[func].callees:
            if _filter_predicate(vstats[callee], threshold, summary):
                continue
            if id(callee) not in visited:
                queue.append(callee)
                visited.add(id(callee))

    _clean_vstats(result)

    return result


def _aux_filter_vstats(vstats, threshold, summary):
    import copy
    result = {}
    for func, entry in vstats.iteritems():
        if _filter_predicate(entry, threshold, summary):
            continue
        result[func] = copy.deepcopy(vstats[func])
    _clean_vstats(result)
    return result


def _clean_vstats(vstats):
    for _, entry in vstats.iteritems():
        for callee in entry.callees.keys():
            if callee not in vstats:
                del entry.callees[callee]

#_______________________________________________________________________________
# vstats2dot

# ------------------* comments on the params of vstats2dot *-------------------
# root:
#     a vstats key, corresponding to an entry in vstats 
#     we only consider nodes(funcs/entries) reachable from a given root in
#         vstats when generating a callgraph
#     if root is an invalid key, all nodes in vstats should be our candidates
#
# threshold:
#     we will omit nodes whose overall percentage of its cumtime 
#     (entry.totaltime) below this threshold:
#         if entry.totaltime * 100.0 / summary < threshold, we omit the entry
#
# summary :
#     the total time spent by a program
#
# -----------------------------------------------------------------------------
# NOTE: the comments above are written according to the current implementation
#       of ProfViz
#


def vstats2dot(vstats, root=None, outfile=None,
               threshold=0.0, summary=0):
    vstats = _filter_vstats(vstats, root,
                            threshold, summary)

    output = None
    if outfile:
        output = open(outfile, 'w')
    else:
        import StringIO
        output = StringIO.StringIO()

    try:
        dot_writer = DotWriter(output)
        dot_writer.graph(vstats, TEMPERATURE_COLORMAP, summary)
        if not outfile:
            return output.getvalue()
    finally:
        output.close()
