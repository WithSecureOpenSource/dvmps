#!/usr/bin/python

import sys
import json
import urllib2
from optparse import OptionParser
import urlparse
import urllib

def __build_url(options, command, parameters = None):
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(options.serverurl)
    if parameters is not None:
        query_string = urllib.urlencode(parameters)
    else:
        query_string = ''
    url = urlparse.urlunsplit((scheme, netloc, command, query_string, ''))
    return url

def allocate(options, base_image, expires, priority, comment):
    data = { 'base_image': base_image, 'expires': expires, 'priority': priority, 'comment': comment }
    data_str = json.dumps(data)
    url = __build_url(options, 'allocate')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def deallocate(options, image_id):
    data = { 'image_id': image_id }
    data_str = json.dumps(data)
    url = __build_url(options, 'deallocate')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def revert(options, image_id):
    data = { 'image_id': image_id }
    data_str = json.dumps(data)
    url = __build_url(options, 'revert')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def poweroff(options, image_id):
    data = { 'image_id': image_id }
    data_str = json.dumps(data)
    url = __build_url(options, 'poweroff')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def poweron(options, image_id):
    data = { 'image_id': image_id }
    data_str = json.dumps(data)
    url = __build_url(options, 'poweron')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def status(options, image_id):
    data = { 'image_id': image_id }
    url = __build_url(options, 'status', data)
    o = urllib2.urlopen(url)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def systemstatus(options):
    url = __build_url(options, 'systemstatus')
    o = urllib2.urlopen(url)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def running_images(options):
    url = __build_url(options, 'running_images')
    o = urllib2.urlopen(url)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def base_images(options):
    url = __build_url(options, 'base_images')
    o = urllib2.urlopen(url)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def show_image_addresses(options):
    (scheme, host_add, path, query, fragment) = urlparse.urlsplit(options.serverurl)
    images = running_images(options)
    print "Image ID - IP Address - VNC Address"
    for image in images["running_images"]:
        print "%s - %s - %s:%s" % (image['image_id'], image["ip_addr"], host_add, image["vncport"])

def maintenance(options, message):
    if message == 'cancel':
        data = { 'maintenance': False}
    else:
        data = { 'maintenance': True, 'message': message }
    data_str = json.dumps(data)
    url = __build_url(options, 'maintenance')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def usage():
    print "Usage: %s [<options>] <command> <arguments..>" % sys.argv[0]
    print " %s allocate <base_image>" % sys.argv[0]
    print " %s deallocate <image_id>" % sys.argv[0]
    print " %s revert <image_id>" % sys.argv[0]
    print " %s poweroff <image_id>" % sys.argv[0]
    print " %s poweron <image_id>" % sys.argv[0]
    print " %s status <image_id>" % sys.argv[0]
    print " %s systemstatus" % sys.argv[0]
    print " %s running_images" % sys.argv[0]
    print " %s base_images" % sys.argv[0]
    print " %s image_addresses" % sys.argv[0]
    print " %s maintenance <message|'cancel'>" % sys.argv[0]
    print ""
    print "Options:"
    print "--serverurl  <url>       Base URL for allocation server (e.g. http://dyn-node1.example.com) [mandatory]"
    print "--validfor   <seconds>   Specify maximum lifetime of <seconds> upon instance allocation or renewal (default 3600 seconds or 1 hour)"
    print "--comment    <comment>   Specify comment upon instance allocation"

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--serverurl', dest='serverurl')
    parser.add_option('--validfor', dest='validfor', type='int', default='3600')
    parser.add_option('--comment', dest='comment', default='')
    parser.add_option('--priority', dest='priority', type='int', default='50')
    (options, args) = parser.parse_args()

    if options.serverurl == None:
        print "Mandatory --serverurl option was not given"
        usage()
        sys.exit(-1)

    ret = None
    arglen = len(args)
    if arglen < 1:
        usage()
        sys.exit(-1)
    command = args[0]

    if command == 'systemstatus':
        ret = systemstatus(options)
        print json.dumps(ret, indent=4)
        sys.exit(0)
    elif command == 'running_images':
        ret = running_images(options)
        print json.dumps(ret, indent=4)
        sys.exit(0)
    elif command == 'base_images':
        ret = base_images(options)
        print json.dumps(ret, indent=4)
        sys.exit(0)
    elif command == 'image_addresses':
        show_image_addresses(options)
        sys.exit(0)

    if arglen < 2:
        usage()
        sys.exit(-1)

    if command == 'allocate':
        ret = allocate(options, args[1], options.validfor, options.priority, options.comment)
        print json.dumps(ret, indent=4)
    elif command == 'deallocate':
        ret = deallocate(options, args[1])
        print json.dumps(ret, indent=4)
    elif command == 'revert':
        ret = revert(options, args[1])
        print json.dumps(ret, indent=4)
    elif command == 'poweroff':
        ret = poweroff(options, args[1])
        print json.dumps(ret, indent=4)
    elif command == 'poweron':
        ret = poweron(options, args[1])
        print json.dumps(ret, indent=4)
    elif command == 'status':
        ret = status(options, args[1])
        print json.dumps(ret, indent=4)
    elif command == 'maintenance':
        ret = maintenance(options, args[1])
        print json.dumps(ret, indent=4)
    else:
        usage()
        sys.exit(-1)
