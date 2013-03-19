#!/usr/bin/python

import sys
import json
import urllib2
from optparse import OptionParser
import urlparse
import urllib

def __build_url(serverurl, command, parameters = None):
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(serverurl)
    if parameters is not None:
        query_string = urllib.urlencode(parameters)
    else:
        query_string = ''
    url = urlparse.urlunsplit((scheme, netloc, command, query_string, ''))
    return url

def create(serverurl, base_image, expires, priority, comment):
    data = { 'base_image': base_image, 'expires': expires, 'priority': priority, 'comment': comment }
    data_str = json.dumps(data)
    url = __build_url(serverurl, 'create')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def allocate(serverurl, base_image, expires, priority, comment):
    data = { 'base_image': base_image, 'expires': expires, 'priority': priority, 'comment': comment }
    data_str = json.dumps(data)
    url = __build_url(serverurl, 'allocate')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def deallocate(serverurl, image_id):
    data = { 'image_id': image_id }
    data_str = json.dumps(data)
    url = __build_url(serverurl, 'deallocate')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def revert(serverurl, image_id):
    data = { 'image_id': image_id }
    data_str = json.dumps(data)
    url = __build_url(serverurl, 'revert')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def poweroff(serverurl, image_id):
    data = { 'image_id': image_id }
    data_str = json.dumps(data)
    url = __build_url(serverurl, 'poweroff')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def poweron(serverurl, image_id):
    data = { 'image_id': image_id }
    data_str = json.dumps(data)
    url = __build_url(serverurl, 'poweron')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def status(serverurl, image_id):
    data = { 'image_id': image_id }
    url = __build_url(serverurl, 'status', data)
    o = urllib2.urlopen(url)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def systemstatus(serverurl):
    url = __build_url(serverurl, 'systemstatus')
    o = urllib2.urlopen(url)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def running_images(serverurl):
    url = __build_url(serverurl, 'running_images')
    o = urllib2.urlopen(url)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def base_images(serverurl):
    url = __build_url(serverurl, 'base_images')
    o = urllib2.urlopen(url)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def show_image_addresses(serverurl):
    (scheme, host_add, path, query, fragment) = urlparse.urlsplit(serverurl)
    images = running_images(serverurl)
    print "Image ID - IP Address - VNC Address"
    for image in images["running_images"]:
        print "%s - %s - %s:%s" % (image['image_id'], image["ip_addr"], host_add, image["vncport"])

def maintenance(serverurl, message):
    if message == 'cancel':
        data = { 'maintenance': False}
    else:
        data = { 'maintenance': True, 'message': message }
    data_str = json.dumps(data)
    url = __build_url(serverurl, 'maintenance')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def usage():
    print "Usage: %s [<options>] <command> <arguments..>" % sys.argv[0]
    print " %s create <base_image>" % sys.argv[0]
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
        ret = systemstatus(options.serverurl)
        print json.dumps(ret, indent=4)
        sys.exit(0)
    elif command == 'running_images':
        ret = running_images(options.serverurl)
        print json.dumps(ret, indent=4)
        sys.exit(0)
    elif command == 'base_images':
        ret = base_images(options.serverurl)
        print json.dumps(ret, indent=4)
        sys.exit(0)
    elif command == 'image_addresses':
        show_image_addresses(options.serverurl)
        sys.exit(0)

    if arglen < 2:
        usage()
        sys.exit(-1)

    if command == 'create':
        ret = create(options.serverurl, args[1], options.validfor, options.priority, options.comment)
        print json.dumps(ret, indent=4)
    elif command == 'allocate':
        ret = allocate(options.serverurl, args[1], options.validfor, options.priority, options.comment)
        print json.dumps(ret, indent=4)
    elif command == 'deallocate':
        ret = deallocate(options.serverurl, args[1])
        print json.dumps(ret, indent=4)
    elif command == 'revert':
        ret = revert(options.serverurl, args[1])
        print json.dumps(ret, indent=4)
    elif command == 'poweroff':
        ret = poweroff(options.serverurl, args[1])
        print json.dumps(ret, indent=4)
    elif command == 'poweron':
        ret = poweron(options.serverurl, args[1])
        print json.dumps(ret, indent=4)
    elif command == 'status':
        ret = status(options.serverurl, args[1])
        print json.dumps(ret, indent=4)
    elif command == 'maintenance':
        ret = maintenance(options.serverurl, args[1])
        print json.dumps(ret, indent=4)
    else:
        usage()
        sys.exit(-1)
