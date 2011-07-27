import BaseHTTPServer
import urlparse
import json
import threading
import time
import subprocess
import shutil
import os

class VMAllocationServiceRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_POST(self):
        parsed = urlparse.urlparse(self.path)
        clen = self.headers.getheader('content-length')
        if clen:
            clen = int(clen)
        else:
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write('<html><body>Bad request</body></html>')
            return
        request_params = None
        data = self.rfile.read(clen)
        try:
            request_params = json.loads(data)
        except:
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write('<html><body>Bad request</body></html>')
            return

        if parsed.path == '/allocate':
            base_image = None
            expires = None
            comment = None
            if request_params.has_key('base_image'):
                base_image = request_params['base_image']
            if request_params.has_key('expires'):
                expires = request_params['expires']
            if request_params.has_key('comment'):
                comment = request_params['comment']
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
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
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
        elif parsed.path == '/status':
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
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
        elif parsed.path == '/systemstatus':
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
        full_path_image_file = '/var/lib/libvirt/images/%s.img' % image_id
        full_path_xml_def_file = '/var/lib/libvirt/qemu/%s.xml' % image_id
#        shutil.copyfile(self.configured_base_images[base_image]['image_filename'], full_path_image_file)
        subprocess.call(['qemu-img', 'create', '-b', self.configured_base_images[base_image]['image_filename'], '-f', 'qcow2', full_path_image_file])
        f = open(self.configured_base_images[base_image]['template_filename'], 'r')
        xmlspec = f.read()
        f.close()
        xmlspec = xmlspec.replace('$(VM_ID)', image_id)
        xmlspec = xmlspec.replace('$(IMAGE_FILE)', full_path_image_file)
        xmlspec = xmlspec.replace('$(MAC_ADDRESS)', mac)
        f = open(full_path_xml_def_file, 'w')
        f.write(xmlspec)
        f.close()
        subprocess.call(['virsh', 'create', full_path_xml_def_file])
        self.allocated_images[image_id] = allocated_info
        ret_val = { 'result': True, 'image_id': image_id, 'ip_addr': ip_addr, 'base_image': base_image, 'expires': expires }        
        self.sync_lock.release()
        return ret_val

    def deallocate_image(self, image_id):
        self.sync_lock.acquire()
        ret_val = { 'result': False, 'error': 'No such image' }
        if self.allocated_images.has_key(image_id):
            subprocess.call(['virsh', 'destroy', image_id])
            full_path_image_file = '/var/lib/libvirt/images/%s.img' % image_id
            full_path_xml_def_file = '/var/lib/libvirt/qemu/%s.xml' % image_id
            os.remove(full_path_image_file)
            os.remove(full_path_xml_def_file)
            self.deallocate_mac(self.allocated_images[image_id]['mac'])
            ret_val = { 'result': True, 'image_id': image_id, 'status': 'not-allocated' }
            del self.allocated_images[image_id]
        self.sync_lock.release()
        return ret_val

    def image_status(self, image_id):
        ret_val = { 'result': True, 'image_id': image_id, 'status': 'not-allocated' }
        self.sync_lock.acquire()
        if self.allocated_images.has_key(image_id):
            image_record = self.allocated_images[image_id]
            time_before_expiry = image_record['creation_time'] + image_record['expires'] - int(time.time())
            if time_before_expiry >= 0:
                ret_val = { 'result': True, 'image_id': image_id, 'status': 'allocated', 'ip_addr': image_record['ip_addr'], 'base_image': image_record['ip_addr'], 'expires': time_before_expiry, 'comment': image_record['comment'] }
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
        self.mac_ip_records[mac] = { 'ip_addr': ip, 'mac': mac, 'allocated': False }
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
            ret_val = self.mac_ip_records[mac]['ip_addr']
        self.sync_lock.release()
        return ret_val

    def get_image_id(self, mac):
        return 'dynamic_image_%s' % mac.replace(':', '')

    def define_base_image(self, base_id, template_filename, image_filename):
        self.sync_lock.acquire()
        self.configured_base_images[base_id] = { 'base_id': base_id, 'template_filename': template_filename, 'image_filename': image_filename }
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

if __name__ == '__main__':
    vma = VMAllocationService(port=80)
    vma.define_mac_ip_pair('00:aa:ee:00:ee:c8', '10.70.180.200')
    vma.define_mac_ip_pair('00:aa:ee:00:ee:c9', '10.70.180.201')
    vma.define_mac_ip_pair('00:aa:ee:00:ee:ca', '10.70.180.202')
    vma.define_mac_ip_pair('00:aa:ee:00:ee:cb', '10.70.180.203')
    vma.define_mac_ip_pair('00:aa:ee:00:ee:cc', '10.70.180.204')
    vma.define_base_image('noushe-linux', '/var/lib/libvirt/qemu/templates/template-noushe-linux-test2.xml', '/var/lib/libvirt/images/base/noushe-linux-test2.qcow2')
    vma.define_base_image('noushe-winxp', '/var/lib/libvirt/qemu/templates/template-noushe-winxp.xml', '/var/lib/libvirt/images/base/noushe-winxp.qcow2')
    vma.run()
