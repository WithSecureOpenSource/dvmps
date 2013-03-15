#!/usr/bin/python

# This script generates BIND DNS entries for dynamic nodes given an IPv4
# address range. The script output can be appended to the BIND config file.

import sys
import ipv4addr

def usage():
    print "Usage: %s <start-ip> <end-ip>" % sys.argv[0]

if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage()
        sys.exit(-1)

    for ip in ipv4addr.ipv4addr_range(sys.argv[1], sys.argv[2]):
        print "dyn-%s.ta\tIN\tA\t%s" % (ip.replace('.', '-'), ip)
