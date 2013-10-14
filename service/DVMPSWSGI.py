#!/usr/bin/python

"""
Copyright (c) 2011-2013 F-Secure
See LICENSE for details
"""

import DVMPSService
import json
import os.path
import urlparse

class DVMPSWSGI:
    REQUEST_GET = 1
    REQUEST_POST = 2

    def __init__(self, database=None):
        self.dvmps = DVMPSService.DVMPSService(database=database)
        self.dvmps.cleanup_expired_images()

    def dvmps_app(self, environ, start_response):
        command = os.path.basename(environ['SCRIPT_NAME'])

        status = '200 OK'
        headers = [('Content-type', 'text/plain')]

        start_response(status, headers)

        res = None

        if self.dvmps is None:
            return [json.dumps({'result':False, 'error':'Internal error, DVMPS service not initialized'})]

        request_params = None

        if environ['REQUEST_METHOD'] == 'POST' and environ.has_key('CONTENT_LENGTH'):
            request_type = self.REQUEST_POST
            data_size = int(environ['CONTENT_LENGTH'])
            data = environ['wsgi.input'].read(data_size)
            try:
                request_params = json.loads(data)
            except:
                return [json.dumps({'result':False, 'error':'Failed to decode request parameters'})]
        elif environ['REQUEST_METHOD'] == 'GET' or environ['REQUEST_METHOD'] == 'HEAD':
            request_type = self.REQUEST_GET
            keys_values = urlparse.parse_qsl(environ['QUERY_STRING'])
            request_params = {}
            for key,value in keys_values:
                request_params[key] = value
        else:
            return [json.dumps({'result':False, 'error':'Invalid request method'})]

        if request_params is None or type(request_params).__name__ != 'dict':
            request_params = {}

        if command == 'create' and request_type == self.REQUEST_POST:
            base_image = None
            expires = None
            comment = None
            priority = 50
            if request_params.has_key('base_image'):
                base_image = request_params['base_image']
            if request_params.has_key('expires'):
                expires = request_params['expires']
            if request_params.has_key('comment'):
                comment = request_params['comment']
            if request_params.has_key('priority'):
                priority = request_params['priority']
            if base_image is not None and expires is not None:
                res = self.dvmps.create_instance(base_image, expires, priority, comment)

        elif command == 'allocate' and request_type == self.REQUEST_POST:
            base_image = None
            expires = None
            comment = None
            priority = 50
            if request_params.has_key('base_image'):
                base_image = request_params['base_image']
            if request_params.has_key('expires'):
                expires = request_params['expires']
            if request_params.has_key('comment'):
                comment = request_params['comment']
            if request_params.has_key('priority'):
                priority = request_params['priority']
            if base_image is not None and expires is not None:
                res = self.dvmps.allocate_image_deprecated(base_image, expires, priority, comment)

        elif command == 'deallocate' and request_type == self.REQUEST_POST:
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                res = self.dvmps.deallocate_image(image_id)

        elif command == 'revert' and request_type == self.REQUEST_POST:
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                res = self.dvmps.revert_image(image_id)

        elif command == 'poweroff' and request_type == self.REQUEST_POST:
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                res = self.dvmps.poweroff_image(image_id)

        elif command == 'poweron' and request_type == self.REQUEST_POST:
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                res = self.dvmps.poweron_image(image_id)

        elif command == 'maintenance' and request_type == self.REQUEST_POST:
            message = ''
            if request_params.has_key('message'):
                message = request_params['message']
            if request_params.has_key('maintenance') and type(request_params['maintenance']).__name__ == 'bool':
                if request_params['maintenance'] == True:
                    res = self.dvmps.set_maintenance_mode(True, message)
                else:
                    res = self.dvmps.set_maintenance_mode(False, '')

        elif command == 'status':
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                res = self.dvmps.image_status(image_id)

        elif command in ('systemstatus', 'running_images'):
            res = self.dvmps.running_images()

        elif command == 'base_images':
            res = self.dvmps.base_images()

        elif command == 'get_node_images':
            res = self.dvmps.get_node_images()

        elif command == 'get_node_placement_data':
            res = self.dvmps.get_node_placement_data()

        elif command == 'set_node_placement_data' and request_type == self.REQUEST_POST:
            if request_params.has_key('node_placement_data'):
                res = self.dvmps.set_node_placement_data(request_params['node_placement_data'])
        elif command == 'renew' and request_type == self.REQUEST_POST:
            try:
                res =  self.dvmps.renew(**request_params)
            except Exception as e:
                res = {'result':False, 'error': str(e)}
        else:
            res = {'result':False, 'error':'Unknown command or bad request method'}

        indent = None
        if request_params.has_key('indent'):
            try:
                indent = int(request_params['indent'])
            except:
                pass
        return [json.dumps(res, indent=indent)]
