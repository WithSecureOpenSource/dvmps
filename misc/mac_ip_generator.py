#!/usr/bin/python

# This script generates the SQL statements for 'dvmps' database to populate
# the mac_ip_pairs table with the given range of IPv4 addresses.

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
        mac_addr = map(lambda n: "%02x" % ord(n), socket.inet_aton(ip)[-3:])
        print "insert into mac_ip_pairs (mac, ip, allocated, allocation_time, valid_for) values ('00:aa:ee:%s', '%s', false, 0, 0);" % (":".join(mac_addr), ip)
