import DVMPSService
import threading
import json
import os.path
import urlparse

class DVMPSWSGI:
    REQUEST_GET = 1
    REQUEST_POST = 2

    def __init__(self, database=None):
        self.dvmps = DVMPSService.DVMPSService(database=database)
        self.sync_lock = threading.Lock()

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

        if command == 'allocate' and request_type == self.REQUEST_POST:
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
                self.sync_lock.acquire()
                try:
                    res = self.dvmps.allocate_image(base_image, expires, priority, comment)
                except:
                    self.sync_lock.release()
                    raise
                self.sync_lock.release()

        elif command == 'deallocate' and request_type == self.REQUEST_POST:
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                self.sync_lock.acquire()
                try:
                    res = self.dvmps.deallocate_image(image_id)
                except:
                    self.sync_lock.release()
                    raise
                self.sync_lock.release()

        elif command == 'revert' and request_type == self.REQUEST_POST:
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                self.sync_lock.acquire()
                try:
                    res = self.dvmps.revert_image(image_id)
                except:
                    self.sync_lock.release()
                    raise
                self.sync_lock.release()

        elif command == 'poweroff' and request_type == self.REQUEST_POST:
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                self.sync_lock.acquire()
                try:
                    res = self.dvmps.poweroff_image(image_id)
                except:
                    self.sync_lock.release()
                    raise
                self.sync_lock.release()

        elif command == 'poweron' and request_type == self.REQUEST_POST:
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                self.sync_lock.acquire()
                try:
                    res = self.dvmps.poweron_image(image_id)
                except:
                    self.sync_lock.release()
                    raise
                self.sync_lock.release()

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
                self.sync_lock.acquire()
                try:
                    res = self.dvmps.image_status(image_id)
                except:
                    self.sync_lock.release()
                    raise
                self.sync_lock.release()

        elif command == 'systemstatus':
            self.sync_lock.acquire()
            try:
                res = self.dvmps.status()
            except:
                self.sync_lock.release()
                raise
            self.sync_lock.release()

        elif command == 'running_images':
            self.sync_lock.acquire()
            try:
                res = self.dvmps.running_images()
            except:
                self.sync_lock.release()
                raise
            self.sync_lock.release()

        elif command == 'base_images':
            self.sync_lock.acquire()
            try:
                res = self.dvmps.base_images()
            except:
                self.sync_lock.release()
                raise
            self.sync_lock.release()

        elif command == 'get_node_images':
            res = self.dvmps.get_node_images()

        else:
            res = {'result':False, 'error':'Unknown command or bad request method'}

        return [json.dumps(res)]
