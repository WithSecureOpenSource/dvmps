import BaseHTTPServer
import urlparse
import json
import threading
import time

class VMAllocationServiceRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse.urlparse(self.path)
        parameter_tuples = urlparse.parse_qsl(parsed.query)
        if parsed.path == '/allocate':
            base_image = None
            expires = None
            comment = None
            for key,value in parameter_tuples:
                if key == 'base_image':
                    base_image = value
                elif key == 'expires':
                    expires = int(value)
                elif key == 'comment':
                    comment = value
            if base_image is not None and expires is not None:
                json_reply = self.server.vm_allocation_service.allocate_callback(base_image, expires, comment)
                if json_reply is not None:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(json.dumps(json_reply))
                    return
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write('<html><body>Bad request</body></html>')
            return
        elif parsed.path == '/deallocate':
            image_id = None
            for key,value in parameter_tuples:
                if key == 'image_id':
                    image_id = value
            if image_id is not None:
                json_reply = self.server.vm_allocation_service.deallocate_callback(image_id)
                if json_reply is not None:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(json.dumps(json_reply))
                    return
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write('<html><body>Bad request</body></html>')
            return
        elif parsed.path == '/imagestatus':
            image_id = None
            for key,value in parameter_tuples:
                if key == 'image_id':
                    image_id = value
            if image_id is not None:
                json_reply = self.server.vm_allocation_service.image_status_callback(image_id)
                if json_reply is not None:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(json.dumps(json_reply))
                    return
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write('<html><body>Bad request</body></html>')
            return
        elif parsed.path == '/status':
            json_reply = self.server.vm_allocation_service.status_callback()
            if json_reply is not None:
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(json.dumps(json_reply))
                return
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write('<html><body>Bad request</body></html>')
            return

        self.send_response(404)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write('<html><body>Not found</body></html>')

    def log_request(code=200, size=0):
        pass

class VMAllocationServiceHTTPServer(BaseHTTPServer.HTTPServer):
    request_queue_size = 1024

class VMAllocationService():
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.httpd = None
        self.expire_thread = None
        self.httpd_thread = None
        self.running = False
        self.allocated_images = []
        self.free_image_specs = []
        self.configured_base_images = []
        self.sync_lock = threading.Lock()

    def allocate_callback(self, base_image, expires, comment):
        print 'allocate callback: %s %d %s' % (base_image, expires, comment)
        self.sync_lock.acquire()
        ret_val = { 'result': True, 'image_id': '%s-aa00bb11cc22' % base_image, 'ip_addr': '192.168.0.1', 'base_image': base_image, 'expires': expires }
        if comment is not None:
            ret_val['comment'] = comment
        self.sync_lock.release()
        return ret_val

    def deallocate_callback(self, image_id):
        print 'deallocate callback: %s' % (image_id)
        self.sync_lock.acquire()
        ret_val = { 'result': True, 'image_id': image_id, 'status': 'free' }
        self.sync_lock.release()
        return ret_val

    def image_status_callback(self, image_id):
        print 'image status callback: %s' % (image_id)
        self.sync_lock.acquire()
        ret_val = { 'result': True, 'image_id': image_id, 'status': 'allocated', 'ip_addr': '192.168.0.1', 'base_image': 'xp', 'expires': 1122 }
        self.sync_lock.release()
        return ret_val
        
    def status_callback(self):
        print 'status callback'
        self.sync_lock.acquire()
        ret_val = { 'result': True, 'allocated_images': 13 }
        self.sync_lock.release()
        return ret_val

    def expire_thread_loop(self):
        while self.running == True:
            print "expire_thread_loop"
            self.sync_lock.acquire()
            # do work here
            self.sync_lock.release()
            time.sleep(5)

    def run(self):
        self.stop()
        self.running = True
        self.expire_thread = threading.Thread(target=self.expire_thread_loop)
        self.expire_thread.start()
        self.httpd = VMAllocationServiceHTTPServer((self.host, self.port), VMAllocationServiceRequestHandler)
        self.httpd.vm_allocation_service = self
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd = None
        if self.httpd_thread is not None:
            self.httpd_thread.join()
            self.httpd_thread = None
        if self.expire_thread is not None:
            self.expire_thread.join()
            self.expire_thread = None
