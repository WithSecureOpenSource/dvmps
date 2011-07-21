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
                json_reply = self.server.vm_allocation_service.allocate_image(base_image, expires, comment)
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
                json_reply = self.server.vm_allocation_service.deallocate_image(image_id)
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
                json_reply = self.server.vm_allocation_service.image_status(image_id)
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
            json_reply = self.server.vm_allocation_service.status()
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
        self.allocated_images = {}
        self.mac_ip_records = {}
        self.configured_base_images = {}
        self.sync_lock = threading.RLock()

    def allocate_image(self, base_image, expires, comment):
        self.sync_lock.acquire()
        if not self.configured_base_images.has_key(base_image):
            self.sync_lock.release()
            return { 'result': False, 'error': 'No such base image configured' }
        mac = self.allocate_mac()
        if mac is None:
            self.sync_lock.release()
            return { 'result': False, 'error': 'Could not allocate a free MAC address' }
        image_id = self.get_image_id(mac)
        ip_addr = self.find_ip_for_mac(mac)
        allocated_info = {}
        allocated_info['image_id'] = image_id
        allocated_info['mac'] = mac
        allocated_info['ip_addr'] = ip_addr
        allocated_info['base_image'] = base_image
        allocated_info['creation_time'] = int(time.time())
        allocated_info['expires'] = expires
        allocated_info['comment'] = ''
        if comment is not None:
            allocated_info['comment'] = comment
        self.allocated_images[image_id] = allocated_info
        ret_val = { 'result': True, 'image_id': image_id, 'ip_addr': ip_addr, 'base_image': base_image, 'expires': expires }
        self.sync_lock.release()
        return ret_val

    def deallocate_image(self, image_id):
        self.sync_lock.acquire()
        ret_val = { 'result': False, 'error': 'No such image' }
        if self.allocated_images.has_key(image_id):
            self.deallocate_mac(self.allocated_images[image_id]['mac'])
            ret_val = { 'result': True, 'image_id': image_id, 'status': 'not-allocated' }
            del self.allocated_images[image_id]
        self.sync_lock.release()
        return ret_val

    def image_status(self, image_id):
        self.sync_lock.acquire()
        if self.allocated_images.has_key(image_id):
            time_before_expiry = self.allocated_images[image_id]['creation_time'] + self.allocated_images[image_id]['expires'] - int(time.time())
            if time_before_expiry >= 0:
                ret_val = { 'result': True, 'image_id': image_id, 'status': 'allocated', 'ip_addr': self.allocated_images['ip_addr'], 'base_image': self.allocated_images['ip_addr'], 'expires': time_bfore_expiry, 'comment': self.allocated_images['comment'] }
        ret_val = { 'result': True, 'image_id': image_id, 'status': 'not-allocated' }
        self.sync_lock.release()
        return ret_val

    def status(self):
        print 'status callback'
        self.sync_lock.acquire()
        ret_val = { 'result': True, 'allocated_images': 13 }
        self.sync_lock.release()
        return ret_val

    def expire_thread_loop(self):
        while self.running == True:
            self.sync_lock.acquire()
            # do work here
            self.sync_lock.release()
            time.sleep(5)

    def define_mac_ip_pair(self, mac, ip):
        self.sync_lock.acquire()
        self.mac_ip_records[mac] = { 'ip_addr': ip, 'allocated': False }
        self.sync_lock.release()

    def allocate_mac(self):
        ret_val = None
        self.sync_lock.acquire()
        mac_keys = self.mac_ip_records.keys()
        for key in mac_keys:
            if self.mac_ip_records[key]['allocated'] == False:
                self.mac_ip_records[key]['allocated'] = True
                ret_val = key
                break
        self.sync_lock.release()
        return ret_val

    def deallocate_mac(self, mac):
        self.sync_lock.acquire()
        if self.mac_ip_records.has_key(mac):
            self.mac_ip_records[mac]['allocated'] = False
        self.sync_lock.release()

    def find_ip_for_mac(self, mac):
        ret_val = None
        self.sync_lock.acquire()
        if self.mac_ip_records.has_key(mac):
            retval = self.mac_ip_records[mac]['ip_addr']
        self.sync_lock.release()
        return ret_val

    def get_image_id(self, mac):
        return 'dynamic_image_%s' % mac.replace(':', '')

    def define_base_image(self, base_id, memory, image_filename):
        self.sync_lock.acquire()
        self.configured_base_images[base_id] = { 'base_id': base_id, 'memory': memory, 'image_filename': image_filename }
        self.sync_lock.release()

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
