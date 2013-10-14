#!/usr/bin/python

"""
Copyright (c) 2011-2013 F-Secure
See LICENSE for details
"""

import time
import subprocess
import os
import uuid
import DVMPSDAO
import libvirt
import xml.dom.minidom as minidom
import logging
import sys
import random
import threading

domain_state_str = {
    libvirt.VIR_DOMAIN_NOSTATE: 'no state',
    libvirt.VIR_DOMAIN_RUNNING: 'running',
    libvirt.VIR_DOMAIN_BLOCKED: 'blocked',
    libvirt.VIR_DOMAIN_PAUSED: 'paused',
    libvirt.VIR_DOMAIN_SHUTDOWN: 'in shutdown',
    libvirt.VIR_DOMAIN_SHUTOFF: 'shut off',
    libvirt.VIR_DOMAIN_CRASHED: 'crashed',
    libvirt.VIR_DOMAIN_PMSUSPENDED: 'suspended'
}

class DVMPSService():
    __active_dynamic_root = '/var/lib/libvirt/dvmps_active/images/'
    __maintenance_flag_file = '/var/lib/libvirt/maintenance'
    _vm_lock = threading.Lock()

    def __init__(self, database=None):
        self.database = database
        self.logger = logging.getLogger('dvmps')
        self.node_placement_data = None

    def __cloned_disk_image_path(self, image_id):
        return os.path.join(self.__active_dynamic_root, '%s.qcow2' % image_id)

    def __cloned_xml_definition_path(self, image_id):
        return os.path.join(self.__active_dynamic_root, '%s.xml' % image_id)

    def __base_image_definitions_path(self):
        return '/var/lib/libvirt/images'

    def __base_disk_image_path(self, base_image_name):
        return '/var/lib/libvirt/images/%s/disk_image.qcow2' % base_image_name

    def __base_xml_template_path(self, base_image_name):
        return '/var/lib/libvirt/images/%s/virtual_machine_config.xml' % base_image_name

    def __run_command(self, command_and_args):
        proc = subprocess.Popen(command_and_args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (sout,serr) = proc.communicate()
        return (proc.returncode, sout, serr)

    def __get_domain_status(self, domain):
        if not domain:
            return "allocated"

        (state, reason) = domain.state(0)
        if state == libvirt.VIR_DOMAIN_NOSTATE or state > libvirt.VIR_DOMAIN_PMSUSPENDED:
            return "allocated"
        else:
            return domain_state_str[state]

    def __get_vnc_port(self, image_id, domain):
        if not domain:
            return None

        port = None
        xmlspec = domain.XMLDesc(0)
        nodes = []

        try:
            xmldom = minidom.parseString(xmlspec)
            nodes = xmldom.getElementsByTagName('graphics')
        except:
            self.logger.error("__get_vnc_port(%s): failed to parse XML, exception: %s" % (image_id, str(sys.exc_info()[1])))
            return None

        for node in nodes:
            port_candidate = node.getAttribute('port')
            if port_candidate is not None and port_candidate != '':
                port = str(port_candidate)
        return port

    def __list_base_images(self):
        dirpath = self.__base_image_definitions_path()
        ls = os.listdir(dirpath)
        image_list = [d for d in ls if os.path.isdir(dirpath+'/'+d)]
        return image_list

    def _free_space(self):
        s =  os.statvfs(self.__active_dynamic_root)
        return ((s.f_bsize*s.f_bfree)/1024**3) >= 15

    def __create_image(self, image_id):
        retval = False
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)
        mip = DVMPSDAO.MacIpPairs(dbc)

        base_images = self.__list_base_images()

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None and allocated_image_conf.has_key('base_image_name') and allocated_image_conf.has_key('mac_id'):
            full_path_base_image_file = None
            full_path_xml_template_file = None
            mac = None

            if allocated_image_conf['base_image_name'] in base_images:
                try:
                    __full_path_base_image_file = self.__base_disk_image_path(allocated_image_conf['base_image_name'])
                    __full_path_xml_template_file = self.__base_xml_template_path(allocated_image_conf['base_image_name'])
                    __full_path_base_image_file = os.path.realpath(__full_path_base_image_file)
                    __full_path_xml_template_file = os.path.realpath(__full_path_xml_template_file)
                    os.stat(__full_path_base_image_file)
                    os.stat(__full_path_xml_template_file)
                    full_path_base_image_file = __full_path_base_image_file
                    full_path_xml_template_file = __full_path_xml_template_file
                except:
                    pass

            if allocated_image_conf.has_key('mac_id'):
                mac = mip.get_mac_for_mac_id(allocated_image_conf['mac_id'])
                ipaddr = mip.get_ip_for_mac_id(allocated_image_conf['mac_id'])

            if full_path_base_image_file is not None and full_path_xml_template_file is not None and mac is not None and ipaddr is not None and self._free_space():
                (rc,out,err) = self.__run_command(['qemu-img', 'create', '-b', full_path_base_image_file, '-f', 'qcow2', self.__cloned_disk_image_path(image_id)])
                if rc == 0:
                    f = open(full_path_xml_template_file, 'r')
                    xmlspec = f.read()
                    f.close()
                    xmlspec = xmlspec.replace('$(VM_ID)', image_id)
                    xmlspec = xmlspec.replace('$(IMAGE_FILE)', self.__cloned_disk_image_path(image_id))
                    xmlspec = xmlspec.replace('$(MAC_ADDRESS)', mac)
                    xmlspec = xmlspec.replace('$(CPU)', str(random.randint(0,23)))
                    f = open(self.__cloned_xml_definition_path(image_id), 'w')
                    f.write(xmlspec)
                    f.close()
                    retval = True
                    self.logger.info("__create_image(%s): image successfully created - mac: %s - ipaddr: %s" % (image_id,mac,ipaddr))
                else:
                    self.logger.error("__create_image(%s): qemu-img failed to create new overlay image\nSTDOUT\n%s\nSTDERR\n%s" % (image_id,out,err))
            else:
                self.logger.error("__create_image(%s): failed to gather all necessary image configuration" % (image_id,))
        else:
            self.logger.warn("__create_image(%s): failed to look up image configuration" % (image_id,))

        return retval

    def __poweron_image_try(self, image_id, xml_spec, track=3, connection=None):
        dom = None
        try:
            dom = connection.createXML(xml_spec, 0)
        except:
            self.logger.error("__poweron_image(%s): failed to launch image, exception: %s" % (image_id,str(sys.exc_info()[1])))
            return False
        if track > 0:
            time.sleep(track)
        try:
            dom = connection.lookupByName(image_id)
        except:
            self.logger.error("__poweron_image(%s): despite successfully reported launch, domain is not found, exception: %s" % (image_id,str(sys.exc_info()[1])))
            return False
        self.logger.info("__poweron_image(%s): image successfully launched" % (image_id,))
        return True

    def __poweron_image(self, image_id, connection=None):
        retval = False
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            full_path_xml_def_file = self.__cloned_xml_definition_path(image_id)

            fh = open(full_path_xml_def_file, 'r')
            xml_spec = fh.read()
            fh.close()

            dom = self.__poweron_image_try(image_id, xml_spec, track=3, connection=connection)
            if dom == False:
                self.logger.warn("__poweron_image(%s): failed once, retrying" % (image_id,))
                dom = self.__poweron_image_try(image_id, xml_spec, track=3, connection=connection)
            if dom != False:
                retval = True
        else:
            self.logger.warn("__poweron_image(%s): failed to look up image configuration" % (image_id,))
        return retval

    def __get_images(self, connection):
        e = None
        for _ in xrange(2):
            try:
                return [connection.lookupByID(id).name() for id in connection.listDomainsID()]
            except Exception, e:
                pass
        if e:
            raise e

    def __poweroff_image(self, image_id, connection=None, strict_mode=True):
        retval = False
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        allocated_image_conf = ali.get_configuration(image_id)
        try:
            if allocated_image_conf is not None:
                for _ in xrange(2):
                    if image_id in self.__get_images(connection):
                        try:
                            dom = connection.lookupByName(image_id)
                            dom.destroy()
                            time.sleep(5)
                        except Exception, e:
                            if "No such image" in str(e):
                                return True
                    else:
                        return True
                if not image_id in self.__get_images(connection):
                    return True
                else:
                    return False
            else:
                self.logger.warn("__poweroff_image(%s): failed to look up image configuration" % (image_id,))
                return False
        except Exception, e:
            self.logger.error("__poweroff_image(%s): error %s" % (image_id, str(e)))
            return False

    def __destroy_image(self, image_id):
        retval = False
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            retval = True
            try:
                os.remove(self.__cloned_disk_image_path(image_id))
            except:
                self.logger.warn("__destroy_image(%s): failed to remove disk image %s" % (image_id, self.__cloned_disk_image_path(image_id)))
                retval = False
                pass

            try:
                os.remove(self.__cloned_xml_definition_path(image_id))
            except:
                self.logger.warn("__destroy_image(%s): failed to remove xml definition %s" % (image_id, self.__cloned_xml_definition_path(image_id)))
                retval = False
                pass

            if retval == True:
                self.logger.info("__destroy_image(%s): image successfully destroyed" % (image_id,))
        else:
            self.logger.warn("__destroy_image(%s): failed to look up image configuration" % (image_id,))

    def cleanup_expired_images(self):
        connection = None

        try:
            dbc = DVMPSDAO.DatabaseConnection(database=self.database)
            ali = DVMPSDAO.AllocatedImages(dbc)
            mip = DVMPSDAO.MacIpPairs(dbc)
            timenow = int(time.time())

            image_ids = ali.get_images()
            for image_id in image_ids:
                image_record = ali.get_configuration(image_id)
                if image_record is not None and image_record.has_key('creation_time') and image_record.has_key('valid_for'):
                    with open("/proc/uptime") as f:
                        booted, _ = f.read().split()
                    booted = int(float(booted))
                    time_before_expiry = image_record['creation_time'] + image_record['valid_for'] - timenow
                    if time_before_expiry < 0 or image_record['creation_time'] < booted:
                        self.logger.info("cleanup_expired_images: found expired image %s" % (image_id,))
                        if connection is None:
                            connection = libvirt.open(None)
                        self.__poweroff_image(image_id, connection=connection)
                        self.__destroy_image(image_id)
                        ali.deallocate(image_id)
                        if image_record.has_key('mac_id'):
                            mip.deallocate(image_record['mac_id'])
        except:
            if connection is not None:
                connection.close()
            raise

        if connection is not None:
            connection.close()

    def create_instance(self, base_image, valid_for, priority, comment, image_id=None, connection=None):
        if os.path.isfile(self.__maintenance_flag_file):
            self.logger.info("create_instance: declining image creation in maintenance mode")
            try:
                with open(self.__maintenance_flag_file) as flag_f:
                    maintenance_msg = flag_f.read()
            except IOError:
                maintenance_msg = ''
            return { 'result': False, 'error': 'Maintenance mode - not allocating images - %s' % maintenance_msg }

        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)
        mip = DVMPSDAO.MacIpPairs(dbc)

        if not image_id:
            image_id = str(uuid.uuid4())

        self.logger.info("create_instance: request to allocate image of type %s" % (base_image,))

        base_images = self.__list_base_images()
        if base_image not in base_images:
            self.logger.warn("create_instance: no such base_image configured %s" % (base_image,))
            return { 'result': False, 'error': 'No such base image configured' }

        connection_cleanup = False
        if connection is None:
            try:
                connection = libvirt.open(None)
                connection_cleanup = True
            except:
                self.logger.warn("create_instance: failed to open libvirt connection, exception: %s" % (str(sys.exc_info()[1]),))
                return { 'result': False, 'error': 'Failed to open libvirt connection' }

        try:
            while True:
                mac_id = mip.allocate(image_id)
                if mac_id is not None:
                    break
                else:
                    lower_priority_images = ali.get_images_below_priority(priority)
                    if len(lower_priority_images) == 0:
                        break
                    else:
                        low_image_id = lower_priority_images[0]
                        low_image_conf = ali.get_configuration(low_image_id)
                        if low_image_conf is not None:
                            self.logger.info("create_instance: destroying lower priority image %s" % (low_image_id,))
                            self.__poweroff_image(low_image_id, connection=connection)
                            self.__destroy_image(low_image_id)
                            ali.deallocate(low_image_id)
                            if low_image_conf.has_key('mac_id'):
                                mip.deallocate(low_image_conf['mac_id'])
                        else:
                            break
        except Exception, e:
            self.log.error("create_instance: %s" % str(e))
            if connection_cleanup == True:
                connection.close()
            return { 'result': False, 'error': 'Exception during mac allocation' }

        if mac_id is None:
            self.logger.warn("create_instance: no free MAC/IP pairs")
            if connection_cleanup == True:
                connection.close()
            return { 'result': False, 'error': 'Could not allocate a free MAC address' }

        if ali.allocate(image_id, mac_id, base_image, valid_for=valid_for, comment=comment, priority=priority) == False:
            self.logger.error("create_instance: failed to allocate image (DAO)")
            mip.deallocate(mac_id)
            if connection_cleanup == True:
                connection.close()
            return { 'result': False, 'error': 'Failed to allocate image' }

        with self._vm_lock:
            if self.__create_image(image_id) == False:
                self.logger.error("create_instance: failed to setup virtual machine")
                ali.deallocate(image_id)
                mip.deallocate(mac_id)
                if connection_cleanup == True:
                    connection.close()
                return { 'result': False, 'error': 'Failed to create backing image' }

        self.logger.info("create_instance: successfully allocated image %s of type %s" % (image_id, base_image))
        ret_val = self.__image_status(image_id, connection=connection)
        if connection_cleanup == True:
            connection.close()
        return ret_val

    def allocate_image_deprecated(self, base_image, valid_for, priority, comment, image_id=None, connection=None):
        connection_cleanup = False
        if connection is None:
            try:
                connection = libvirt.open(None)
                connection_cleanup = True
            except:
                self.logger.warn("allocate_image: failed to open libvirt connection, exception: %s" % (str(sys.exc_info()[1]),))
                return { 'result': False, 'error': 'Failed to open libvirt connection' }
        # mandatory duplication so deallocation and poweron work
        if not image_id:
            image_id = str(uuid.uuid4())
        ret_val = self.create_instance(base_image, valid_for, priority, comment, image_id=image_id, connection=connection)

        if ret_val['result'] == False:
            if connection_cleanup == True:
                connection.close()
            return ret_val

        if self.__poweron_image(image_id, connection=connection) != True:
            self.logger.error("allocate_image: failed to launch virtual machine")
            self.deallocate_image(image_id, connection=connection)
            if connection_cleanup == True:
                connection.close()
            return { 'result': False, 'error': 'Failed to launch virtual machine' }

        self.logger.info("allocate_image: successfully allocated and launched image %s of type %s" % (image_id, base_image))
        ret_val = self.__image_status(image_id, connection=connection)
        if connection_cleanup == True:
            connection.close()
        return ret_val

    def deallocate_image(self, image_id, connection=None):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)
        mip = DVMPSDAO.MacIpPairs(dbc)

        ret_val = { 'result': False, 'error': 'No such image' }

        connection_cleanup = False
        if connection is None:
            try:
                connection = libvirt.open(None)
                connection_cleanup = True
            except:
                self.logger.warn("deallocate_image: failed to open libvirt connection, exception: %s" % (str(sys.exc_info()[1]),))
                return { 'result': False, 'error': 'Failed to open libvirt connection' }

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            self.logger.info("deallocate_image(%s): deallocating" % (image_id,))
            if not self.__poweroff_image(image_id, connection=connection, strict_mode=False):
                return { 'result': False, 'error': 'Unable to shutdown the image. Leaving things unremoved, please investigate' }
            self.__destroy_image(image_id)
            ali.deallocate(image_id)
            if allocated_image_conf.has_key('mac_id'):
                mip.deallocate(allocated_image_conf['mac_id'])
            ret_val = { 'result': True, 'image_id': image_id, 'status': 'not-allocated' }
        else:
            self.logger.warn("deallocate_image(%s): failed to look up image configuration" % (image_id,))

        if connection_cleanup == True:
            connection.close()
        return ret_val

    def revert_image(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        ret_val = { 'result': False, 'error': 'No such image' }

        try:
            connection = libvirt.open(None)
        except:
            self.logger.warn("revert_image: failed to open libvirt connection, exception: %s" % (str(sys.exc_info()[1]),))
            return { 'result': False, 'error': 'Failed to open libvirt connection' }

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            self.logger.info("revert_image(%s): reverting" % (image_id,))
            self.__poweroff_image(image_id, connection=connection)
            self.__destroy_image(image_id)
            self.__create_image(image_id)
            self.__poweron_image(image_id, connection=connection)
            ret_val = self.__image_status(image_id, connection=connection)
        else:
            self.logger.warn("revert_image(%s): failed to look up image configuration" % (image_id,))

        connection.close()
        return ret_val

    def __image_status(self, image_id, connection=None):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)
        mip = DVMPSDAO.MacIpPairs(dbc)

        ret_val = None

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            valid_for = 0
            ip_addr = None
            base_image = None
            comment = None
            priority = 50

            try:
                domain = connection.lookupByName(image_id)
            except:
                domain = None
                self.logger.warn("__image_status(%s): no such domain, exception: %s" % (image_id, str(sys.exc_info()[1])))
            vnc_port = self.__get_vnc_port(image_id, domain)
            status = self.__get_domain_status(domain)

            if allocated_image_conf.has_key('creation_time') and allocated_image_conf.has_key('valid_for'):
                valid_for = allocated_image_conf['creation_time'] + allocated_image_conf['valid_for'] - int(time.time())
            if allocated_image_conf.has_key('mac_id'):
                ip_addr = mip.get_ip_for_mac_id(allocated_image_conf['mac_id'])
            if allocated_image_conf.has_key('base_image_name'):
                base_image = allocated_image_conf['base_image_name']
            if allocated_image_conf.has_key('comment'):
                comment = allocated_image_conf['comment']
            if allocated_image_conf.has_key('priority'):
                priority = allocated_image_conf['priority']
            ret_val = { 'result': True, 'image_id': image_id, 'status': status, 'ip_addr': ip_addr, 'base_image': base_image, 'valid_for': valid_for, 'priority': priority, 'comment': comment, 'vncport': vnc_port }
        else:
            self.logger.warn("__image_status(%s): failed to look up image configuration" % (image_id,))

        return ret_val

    def image_status(self, image_id):
        try:
            connection = libvirt.open(None)
        except:
            self.logger.warn("image_status: failed to open libvirt connection, exception: %s" % (str(sys.exc_info()[1]),))
            return { 'result': False, 'error': 'Failed to open libvirt connection' }

        ret_val = self.__image_status(image_id, connection=connection)
        if ret_val is None:
            ret_val = { 'result': True, 'image_id': image_id, 'status': 'not-allocated' }
        connection.close()
        return ret_val

    def poweroff_image(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        try:
            connection = libvirt.open(None)
        except:
            self.logger.warn("poweroff_image: failed to open libvirt connection, exception: %s" % (str(sys.exc_info()[1]),))
            return { 'result': False, 'error': 'Failed to open libvirt connection' }

        ret_val = { 'result': False, 'error': 'no such image' }

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            self.__poweroff_image(image_id, connection=connection)
            ret_val = { 'result': True, 'image_id': image_id }
        else:
            self.logger.warn("poweroff_image(%s): failed to look up image configuration" % (image_id,))

        connection.close()
        return ret_val

    def poweron_image(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        ret_val = { 'result': False, 'error': 'no such image' }

        try:
            connection = libvirt.open(None)
        except:
            self.logger.warn("poweron_image: failed to open libvirt connection, exception: %s" % (str(sys.exc_info()[1]),))
            return { 'result': False, 'error': 'Failed to open libvirt connection' }

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            self.__poweron_image(image_id, connection=connection)
            ret_val = self.__image_status(image_id, connection=connection)
        else:
            self.logger.warn("poweron_image(%s): failed to look up image configuration" % (image_id,))

        connection.close()
        return ret_val

    def running_images(self):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        images = ali.get_images()
        image_statuses = []

        try:
            connection = libvirt.open(None)
        except:
            self.logger.warn("running_images: failed to open libvirt connection, exception: %s" % (str(sys.exc_info()[1]),))
            return { 'result': False, 'error': 'Failed to open libvirt connection' }

        for image in images:
            image_status = self.__image_status(image, connection=connection)
            if image_status != None:
                image_statuses.append(image_status)
        connection.close()
        ret_val = { 'result': True, 'running_images': image_statuses }
        return ret_val

    def renew(self, image_id, valid_for):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)
        return { 'result': ali.renew(image_id, valid_for), 'message': 'New VM renew time %s' % valid_for }

    def base_images(self):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)

        base_images = self.__list_base_images()

        return { 'result': True, 'base_images': base_images }

    def set_maintenance_mode(self, maintenance=True, message=''):
        if maintenance:
            try:
                with open(self.__maintenance_flag_file, 'wb') as flag_f:
                    flag_f.write(message)
            except:
                return { 'result': False }
        else:
            if os.path.isfile(self.__maintenance_flag_file):
                try:
                    os.unlink(self.__maintenance_flag_file)
                except:
                    return { 'result': False }
        return { 'result': True, 'maintenance': maintenance, 'message': message }

    def get_node_images(self):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        base_images = self.__list_base_images()
        image_counts = {}

        for base_image in base_images:
            image_counts[base_image] = 0
        base_image_names = image_counts.keys()

        running_images = ali.get_images()
        for image in running_images:
            image_info = ali.get_configuration(image)
            if image_info is not None and image_info.has_key('base_image_name') and image_counts.has_key(image_info['base_image_name']):
                image_counts[image_info['base_image_name']] = image_counts[image_info['base_image_name']] + 1

        result = []
        for name in base_image_names:
            result.append({'base_image_name':name, 'running_instances': image_counts[name]})

        return { 'result': True, 'images': result }

    def get_node_placement_data(self):
        return { 'result': True, 'placement_data': self.node_placement_data }

    def set_node_placement_data(self, node_placement_data):
        self.node_placement_data = node_placement_data
        return { 'result': True }
