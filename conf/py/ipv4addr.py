import re

IPV4ADDR_RE = re.compile(r'^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$')

def ipv4addr_range(start_ip, end_ip):
    start_ip_bytes = ipv4addr_dotdec2bytes(start_ip)
    end_ip_bytes = ipv4addr_dotdec2bytes(end_ip)
    assert(start_ip_bytes <= end_ip_bytes)

    for ip_bytes in range(start_ip_bytes, end_ip_bytes + 1):
        yield ipv4addr_bytes2dotdec(ip_bytes)

def ipv4addr_dotdec2bytes(ip_dotdec):
    m = IPV4ADDR_RE.match(ip_dotdec)
    octets = []
    if m:
        for i in range(1, 5):
            o = int(m.group(i))
            if o < 256:
                octets.append(o)
    k = 3
    ip_bytes = 0
    for o in octets:
        ip_bytes = ip_bytes + (o << (8 * k))
        k = k - 1
    return ip_bytes


def ipv4addr_bytes2dotdec(ip_bytes):
    k = 3
    octets = []
    while k >= 0:
        o = str((ip_bytes >> (8 * k)) & 255)
        octets.append(o)
        k = k - 1
    return '.'.join(octets)
