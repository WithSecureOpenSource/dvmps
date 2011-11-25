import socket
import os
import DVMPSClient
#import mockedDVMPSClient as DVMPSClient
from optparse import OptionParser
import subprocess

def allocateMachine(host, base_img, expires, comment):
    parser = OptionParser()
    parser.add_option('--serverurl',
                      dest='serverurl',
                      default='http://%s' % host)
    (options, args) = parser.parse_args()
    ret = DVMPSClient.allocate(options, base_img, expires * 60, 50, comment)
    if 'result' in ret:
        if ret['result'] == False:
            return False, None, ret['error']

    if ret['status'] != "allocated":
        return False, None, 'Error is: ' + str(ret)
    
    return True, ret['ip_addr'], None

def deallocate(blade, machine_id):
    parser = OptionParser()
    parser.add_option('--serverurl',
                      dest='serverurl',
                      default="http://%s" % blade)
    (options, args) = parser.parse_args()
    response = DVMPSClient.deallocate(options, machine_id)
    return response

def listRunningVms(host):
    parser = OptionParser()
    parser.add_option('--serverurl',
                      dest='serverurl',
                      default='http://%s' % host)
    (options, args) = parser.parse_args()
    return DVMPSClient.running_images(options)

def listTemplates(host):
    parser = OptionParser()
    parser.add_option('--serverurl',
                      dest='serverurl',
                      default='http://%s' % host)
    (options, args) = parser.parse_args()
    return DVMPSClient.base_images(options)
   
def canConnectWithRemoteDesktop(ip_add):
    #should be able to connect a socket to ip_add:3389
    socket_to_rd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        socket_to_rd.settimeout(2)
        socket_to_rd.connect((ip_add, 3389))
        socket_to_rd.close()
        return True
    except socket.error:
        return False

def connectWithRemoteDesktop(ip_add):
    if os.path.isfile("Default.rdp"):
        subprocess.Popen(r'mstsc.exe Default.rdp /v:' + ip_add)
    else:
        subprocess.Popen(r'mstsc.exe /v:' + ip_add)
 
class Curry:
    def __init__(self, fun, *args, **kwargs):
        self.fun = fun
        self.pending = args[:]
        self.kwargs = kwargs.copy()

    def __call__(self, *args, **kwargs):
        if kwargs and self.kwargs:
            kw = self.kwargs.copy()
            kw.update(kwargs)
        else:
            kw = kwargs or self.kwargs

        return self.fun(*(self.pending + args), **kw)
