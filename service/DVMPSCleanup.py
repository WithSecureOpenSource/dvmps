#!/usr/bin/python

import libvirt
import uuid
import DVMPSDAO
import os
import stat
import time

dbc = DVMPSDAO.DatabaseConnection(database='dvmps')
ali = DVMPSDAO.AllocatedImages(dbc) 

def cleanup_logs():
    logdir = '/var/log/libvirt/qemu'
    seconds_to_keep = 60*60*24*3

    now = time.time()

    logfiles = []
    try:
        logfiles = os.listdir(logdir)
    except:
        pass

    for entry in logfiles:
        filename = os.path.join(logdir, entry)
        try:
            st = os.stat(filename)
            if stat.S_ISREG(st.st_mode) and now - st.st_ctime > seconds_to_keep:
                os.unlink(filename)
        except:
            pass

def cleanup_libvirt():
    connection = libvirt.open(None)
    if connection is not None:
        names = [connection.lookupByID(id).name() for id in connection.listDomainsID()]
        for name in names:
            try:
                 u = uuid.UUID(name)
            except:
                 continue

            if ali.get_configuration(name) == None:
                 print "vm: %s not found in active set" % name
                 try:
                     dom = connection.lookupByName(name)
                     dom.destroy()
                 except Exception, e:
                     print str(e)
            else:
                 pass
    else:
        print "FAILED to open libvirt connection"

def cleanup_images():
    images = os.listdir('/var/lib/libvirt/images/active_dynamic/')
    for name in images:
        name, _, ending = name.partition(".")
        if len(name) != 36 or not ending in ('qcow2', 'img'):
            continue

        try:
            u = uuid.UUID(name)
        except:
            continue

        if ali.get_configuration(name) == None:
            print "image: %s not found in active set" % name
            os.unlink('/var/lib/libvirt/images/active_dynamic/%s.%s' % (name, ending))
        else:
            pass

def cleanup_xmls():
    images = os.listdir('/var/lib/libvirt/qemu/active_dynamic/')
    for name in images:
        if len(name) != 40 or name[-4:] != '.xml':
            continue
        name = name[:-4]
        try:
            u = uuid.UUID(name)
        except:
            continue

        if ali.get_configuration(name) == None:
            print "xml: %s not found in active set" % name
            os.unlink('/var/lib/libvirt/qemu/active_dynamic/%s.xml' % name)
        else:
            pass

def cleanup_monitors():
    images = os.listdir('/var/lib/libvirt/qemu/')
    for name in images:
        if len(name) != 44 or name[-8:] != '.monitor':
            continue
        name = name[:-8]
        try:
            u = uuid.UUID(name)
        except:
            continue

        if ali.get_configuration(name) == None:
            print "monitor: %s not found in active set" % name
            os.unlink('/var/lib/libvirt/qemu/%s.monitor' % name)
        else:
            pass

def cleanup_mac_ip_bindings():
    bindings = os.listdir('/var/lib/libvirt/ip_mac_allocations/')
    for binding in bindings:
        image_id = ""
        if time.time() - os.stat('/var/lib/libvirt/ip_mac_allocations/' + binding).st_ctime < 5:
            print "Skipping file newer than 5 seconds to give grace period for writing"
        with open('/var/lib/libvirt/ip_mac_allocations/' + binding) as f:
            image_id = f.read()
        try:
            u = uuid.UUID(image_id)
        except:
            continue

        if ali.get_configuration(image_id) == None:
            print "ip_mac_binding: %s not found in active set, claimed to be owned by %s" % (binding, image_id)
            os.unlink('/var/lib/libvirt/ip_mac_allocations/%s' % binding)

if __name__ == "__main__":
    cleanup_logs()
    cleanup_libvirt()
    cleanup_images()
    cleanup_xmls()
    cleanup_monitors()
    cleanup_mac_ip_bindings()

