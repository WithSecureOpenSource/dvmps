import SocketServer
import json
import time
import urllib2
import socket
import logging
import logging.handlers
import optparse
import sys

logger = logging.getLogger('dvmps-pa')

received_node_data = {}

__appname__ = "dvmps-placement-agent"
__usage__ = "%prog [-l <logfile>]"
__version__ = "1.0"
__author__ = "F-Secure Corporation"
__doc__ = "Dynamic Virtual Machine Provisioning Service - Placement Agent"

class UDPHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            node_data = json.loads(self.request[0])
        except:
            logger.warn("non-json data from %s" % self.client_address[0])
            return
        if type(node_data).__name__ != 'dict' or not node_data.has_key('type') or node_data['type'] != 'dvmps_node_update_v1' or not node_data.has_key('images'):
            logger.warn("Data from %s wasn't of the correct type, or was missing mandatory fields" % self.client_address[0])
            return
        node_images = {}
        for candidate in node_data['images']:
            if type(candidate).__name__ == 'dict' and \
               candidate.has_key('running_instances') and type(candidate['running_instances']).__name__ == 'int' and \
               candidate.has_key('base_image_name'):
                if type(candidate['base_image_name']).__name__ == 'str' or type(candidate['base_image_name']).__name__ == 'unicode':
                    node_images[str(candidate['base_image_name'])] = candidate['running_instances']
                else:
                    logger.warn("Invalid type for base_image_name '%s' from %s" % (type(candidate['base_image_name']).__name__, self.client_address[0]))
            else:
                logger.warn("Node image candidate from %s: one or more missing fields or invalid types" % self.client_address[0])
        node_name = self.client_address[0]
        now = int(time.time())
        received_node_data[node_name] = {'images':node_images,'timestamp':now}

        node_image_keys = node_images.keys()
        count = 0
        for node_image_key in node_image_keys:
            count = count + node_images[node_image_key]
        logger.info("received info successful for %s, %d types, %d running instances" % (self.client_address[0], len(node_image_keys), count))

def send_local_data(broadcast_port):
    try:
        opener = urllib2.urlopen('http://localhost/get_node_images')
    except:
        logger.error("Failed to load local node info")
        return
    
    raw_data = opener.read()
    try:
        data = json.loads(raw_data)
    except:
        logger.error("failed to decode json for local node")
        return

    if type(data).__name__ != 'dict' or not data.has_key('result') or data['result'] != True or not data.has_key('images') or type(data['images']).__name__ != 'list':
        logger.error("failed to parse data for local node")
        return

    out_data = {'type':'dvmps_node_update_v1','images':data['images']}
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(json.dumps(out_data), ('<broadcast>', broadcast_port))
    except:
        logger.error("sending local data failed with error")

def prune_stale_data():
    now = int(time.time())
    node_keys = received_node_data.keys()
    for node_key in node_keys:
        if now > received_node_data[node_key]['timestamp'] + 30:
            del received_node_data[node_key]

def get_image_node_score(image_name, node_name):
    score = 0
    node_image_names = received_node_data[node_name]['images']
    for node_image_name in node_image_names:
        if image_name == node_image_name:
            score = score + received_node_data[node_name]['images'][node_image_name]
        else:
            score = score - received_node_data[node_name]['images'][node_image_name]
    return score

def score_sort_helper(item):
    return -item['score']

def calculate_and_publish_placement_strategy():
    prune_stale_data()

    available_images = {}
    image_keys = []

    node_keys = received_node_data.keys()
    for node_key in node_keys:
        node_image_keys = received_node_data[node_key]['images']
        for node_image_key in node_image_keys:
            if available_images.has_key(node_image_key):
                if node_key not in available_images[node_image_key]:
                    available_images[node_image_key].append(node_key)
            else:
                available_images[node_image_key] = [ node_key ]
                image_keys.append(node_image_key)

    allocation_strategy = {}

    for image_key in image_keys:
        scores = []
        for node_key in available_images[image_key]:
            scores.append({'node':node_key, 'score':get_image_node_score(image_key, node_key)})
        sorted_scores = sorted(scores, key=score_sort_helper)
        node_list = []
        for node_image_score in sorted_scores:
            node_list.append(node_image_score['node'])
        allocation_strategy[image_key] = node_list

    out_data = { 'node_placement_data': allocation_strategy }
    try:
        opener = urllib2.urlopen('http://localhost/set_node_placement_data', json.dumps(out_data))
        res = opener.read()
        reply = json.loads(res)
    except:
        logger.error("Failed to store placement data on the local node")
        return

    if not reply.has_key('result') or reply['result'] != True:
        logger.error("Local node reported failure in storing placement data")

def run(broadcast_port):
    server = SocketServer.UDPServer(("0.0.0.0", broadcast_port), UDPHandler)
    server.timeout = 1
    last_updated_timestamp = 0
    while True:
        perform_local_update = False
        now = int(time.time())
        if now > last_updated_timestamp + 10:
            perform_local_update = True
            last_updated_timestamp = now
        if perform_local_update == True:
            send_local_data(broadcast_port)
        server.handle_request()
        if perform_local_update == True:
            calculate_and_publish_placement_strategy()

if __name__ == "__main__":
    p = optparse.OptionParser(description=__doc__, version=__version__)
    p.set_usage(__usage__)
    p.add_option("-l", dest="logfile", help="write log in file")
    p.add_option("-p", dest="broadcast_port", type="int", default=80, help="port used for broadcast messages")
    opt, args = p.parse_args(sys.argv)

    if opt.logfile is not None:
        root_logger = logging.getLogger()
        rotating_handler = logging.handlers.RotatingFileHandler(opt.logfile, maxBytes=1024*1024*10, backupCount=10)
        formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
        rotating_handler.setFormatter(formatter)
        root_logger.addHandler(rotating_handler)
        root_logger.setLevel(logging.WARN)

    run(opt.broadcast_port)
