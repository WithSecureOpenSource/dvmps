#!/usr/bin/python

# This script generates ISC dhcpd host entries for dynamic nodes given an IPv4
# address range. The script output can be appended to the dhcpd.conf file.

import sys
import socket
import ipv4addr

def usage():
    print "Usage: %s <start-ip> <end-ip>" % sys.argv[0]

if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage()
        sys.exit(-1)

    for ip in ipv4addr.ipv4addr_range(sys.argv[1], sys.argv[2]):
        print "host dyn-%s {" % ip.replace('.', '-')
        mac_addr = map(lambda n: "%02x" % ord(n), socket.inet_aton(ip)[-3:])
        print "  hardware ethernet 00:aa:ee:%s;" % ":".join(mac_addr)
        print "  fixed-address %s;" % ip
        print "}"
        print ""
