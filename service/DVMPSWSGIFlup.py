#!/usr/bin/python

import os
import sys
import optparse
from flup.server.fcgi import WSGIServer
import DVMPSWSGI
import logging
import logging.handlers

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
    p.add_option("-l", dest="logfile", help="write log in file")
    opt, args = p.parse_args(sys.argv)

    if not opt.socketfile:
        print "ERROR: socketfile not specified"
        p.print_help()
        sys.exit(-1)

    if opt.logfile is not None:
        root_logger = logging.getLogger()
        rotating_handler = logging.handlers.RotatingFileHandler(opt.logfile, maxBytes=1024*1024*10, backupCount=10)
        formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
        rotating_handler.setFormatter(formatter)
        root_logger.addHandler(rotating_handler)
        root_logger.setLevel(logging.DEBUG)

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
