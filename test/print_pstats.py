import sys
import pprint
import marshal

with open(sys.argv[1], 'rb') as fp:
	stats = marshal.load(fp)
	pprint.pprint(stats)
