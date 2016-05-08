##
#   William Cheung, 2016/03/14
##


import json
import os
import sys


def print_usage():
    appname = os.path.basename(__file__)
    print 'Usage : %s json_file1 [json_file2 ...]' % appname


def load_json(json_file):
    if not os.path.exists(json_file):
        json_file = os.getcwd() + '\\' + json_file
    if not os.path.exists(json_file):
        return None

    fp = open(json_file)
    try:
        return json.load(fp)
    except:
        return None
    finally:
        fp.close()


def do_dup_test(json_object):
    name_set, dup_set = set(), set()
    aux_dup_test(json_object, name_set, dup_set)
    return dup_set


def aux_dup_test(json_object, name_set, dup_set):
    if isinstance(json_object, (list, set)):
        for value in json_object:
            aux_dup_test(value, name_set, dup_set)
    elif isinstance(json_object, dict):
        for key in json_object:
            value = json_object[key]
            if key == 'actionlist':
                continue
            elif key == 'name' and value is not None:
                value = trim(value)
                if value in name_set:
                    dup_set.add(value)
                else:
                    name_set.add(value)
            aux_dup_test(value, name_set, dup_set)


def trim(name):
    pos = name.find('#')
    if pos != -1:
        return name[:pos]
    return name


def dup_test(json_file):
    print 'Processing %s ...' % json_file
    json_object = load_json(json_file)
    if json_object is None:
        print '... FAIL: the file does not exist or has been corrupted'
        return
    dup_set = do_dup_test(json_object)
    if len(dup_set) == 0:
        print '... PASS'
    else:
        print '... FAIL: duplicate names detected: '
        out = '    '
        for name in dup_set:
            out += name + ' '
        print out


def main():
    argc = len(sys.argv)
    if argc < 2:
        print_usage()
    else:
        for filename in sys.argv[1:]:
            dup_test(filename)
    return


if __name__ == '__main__':
    sys.exit(main())
