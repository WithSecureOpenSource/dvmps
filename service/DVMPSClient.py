import sys
import json
import urllib2
from optparse import OptionParser
import urlparse

def __build_url(options, command):
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(options.serverurl)
    url = urlparse.urlunsplit((scheme, netloc, command, '', ''))
    return url

def allocate(options, base_image, expires, comment):
    data = { 'base_image': base_image, 'expires': expires, 'comment': comment }
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
    data_str = json.dumps(data)
    url = __build_url(options, 'status')
    o = urllib2.urlopen(url, data_str)
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def systemstatus(options):
    url = __build_url(options, 'systemstatus')
    o = urllib2.urlopen(url, json.dumps(None))
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def running_images(options):
    url = __build_url(options, 'running_images')
    o = urllib2.urlopen(url, json.dumps(None))
    rep_str = o.read()
    rep = json.loads(rep_str)
    return rep

def base_images(options):
    url = __build_url(options, 'base_images')
    o = urllib2.urlopen(url, json.dumps(None))
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

    if arglen < 2:
        usage()
        sys.exit(-1)

    if command == 'allocate':
        ret = allocate(options, args[1], options.validfor, options.comment)
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
    else:
        usage()
        sys.exit(-1)
