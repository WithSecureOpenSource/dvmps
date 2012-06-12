#!/usr/bin/python

from wsgiref.simple_server import make_server
import DVMPSWSGI

dvmps_wsgi = None

def wsgi_app(environ, start_response):
    return dvmps_wsgi.dvmps_app(environ, start_response)

if __name__ == '__main__':
    dvmps_wsgi = DVMPSWSGI.DVMPSWSGI(database='dvmps')

    httpd = make_server('', 80, wsgi_app)
    print "Serving on port 80..."

    # Serve until process is killed
    httpd.serve_forever()
