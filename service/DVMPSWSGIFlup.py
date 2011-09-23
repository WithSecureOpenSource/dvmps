import os
import sys
import optparse
from flup.server.fcgi import WSGIServer
import DVMPSWSGI

__appname__ = "dvmps-node"
__usage__ = "%prog -f <socket_file>"
__version__ = "1.0"
__author__ = "F-Secure Corporation"
__doc__ = "Dynamic Virtual Machine Provisioning Service"

dvmps_wsgi = None

def wsgi_app(environ, start_response):
    return dvmps_wsgi.dvmps_app(environ, start_response)

if __name__ == '__main__':
    p = optparse.OptionParser(description=__doc__, version=__version__)
    p.set_usage(__usage__)
    p.add_option("-f", dest="socketfile", help="listen on <socketfile>")
    p.add_option("-d", dest="database", help="used datebase", default="dvmps") 
    opt, args = p.parse_args(sys.argv)

    if not opt.socketfile:
        print "ERROR: socketfile not specified"
        p.print_help()
        sys.exit(-1)

    dvmps_wsgi = DVMPSWSGI.DVMPSWSGI(database=opt.database)

    try:
        WSGIServer(wsgi_app,
            bindAddress=opt.socketfile,
            umask=0111,
#            multiplexed=True,
            ).run()
    finally:
        # Clean up server socket file
        os.unlink(opt.socketfile)
