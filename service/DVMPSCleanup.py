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
        ids = connection.listDomainsID()
        for id in ids:
            dom = connection.lookupByID(id)
            name = dom.name()
            try:
                 u = uuid.UUID(name)
            except:
                 continue

            if ali.get_configuration(name) == None:
                 print "vm: %s not found in active set" % name
                 dom.destroy()
            else:
                 pass
    else:
        print "FAILED to open libvirt connection"

def cleanup_images():
    images = os.listdir('/var/lib/libvirt/images/active_dynamic/')
    for name in images:
        if len(name) != 40 or name[-4:] != '.img':
            continue
        name = name[:-4]
        try:
            u = uuid.UUID(name)
        except:
            continue

        if ali.get_configuration(name) == None:
            print "image: %s not found in active set" % name
            os.unlink('/var/lib/libvirt/images/active_dynamic/%s.img' % name)
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

if __name__ == "__main__":
    cleanup_logs()
    cleanup_libvirt()
    cleanup_images()
    cleanup_xmls()
    cleanup_monitors()

