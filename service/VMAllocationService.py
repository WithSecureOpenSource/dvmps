import BaseHTTPServer
import urlparse
import json

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

    def allocate_callback(self, base_image, expires, comment):
        print 'allocate callback: %s %d %s' % (base_image, expires, comment)
        ret_val = { 'result': True, 'image_id': '%s-aa00bb11cc22' % base_image, 'ip_addr': '192.168.0.1', 'base_image': base_image, 'expires': expires }
        if comment is not None:
            ret_val['comment'] = comment
        return ret_val

    def deallocate_callback(self, image_id):
        print 'deallocate callback: %s' % (image_id)
        ret_val = { 'result': True, 'image_id': image_id, 'status': 'free' }
        return ret_val

    def image_status_callback(self, image_id):
        print 'image status callback: %s' % (image_id)
        ret_val = { 'result': True, 'image_id': image_id, 'status': 'allocated', 'ip_addr': '192.168.0.1', 'base_image': 'xp', 'expires': 1122 }
        return ret_val
        
    def status_callback(self):
        print 'status callback'
        ret_val = { 'result': True, 'allocated_images': 13 }
        return ret_val

    def run(self):
        self.httpd = VMAllocationServiceHTTPServer((self.host, self.port), VMAllocationServiceRequestHandler)
        self.httpd.vm_allocation_service = self
        self.httpd.serve_forever()
