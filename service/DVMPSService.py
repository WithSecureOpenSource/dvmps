import threading
import time
import subprocess
import shutil
import os
import uuid
import random
import DVMPSDAO

class DVMPSService():
    def __init__(self, database=None):
        self.database = database
        self.sync_lock = threading.RLock()

    def __cloned_disk_image_path(self, image_id):
        return '/var/lib/libvirt/images/active_dynamic/%s.img' % image_id

    def __cloned_xml_definition_path(self, image_id):
        return '/var/lib/libvirt/qemu/active_dynamic/%s.xml' % image_id

    def __base_disk_image_path(self, filename):
        return '/var/lib/libvirt/images/base/%s' % filename

    def __base_xml_template_path(self, filename):
        return '/var/lib/libvirt/qemu/templates/%s' % filename

    def __create_image(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)
        bim = DVMPSDAO.BaseImages(dbc)
        mip = DVMPSDAO.MacIpPairs(dbc)

        self.sync_lock.acquire()
        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None and allocated_image_conf.has_key('base_image_id') and allocated_image_conf.has_key('mac_id'):
            full_path_base_image_file = None
            full_path_xml_template_file = None
            mac = None

            base_image_conf = bim.get_base_image_configuration(allocated_image_conf['base_image_id'])
            if base_image_conf is not None and base_image_conf.has_key('base_image_file') and base_image_conf.has_key('configuration_template'):
                full_path_base_image_file = self.__base_disk_image_path(base_image_conf['base_image_file'])
                full_path_xml_template_file = self.__base_xml_template_path(base_image_conf['configuration_template'])

            if allocated_image_conf.has_key('mac_id'):
                mac = mip.get_mac_for_mac_id(allocated_image_conf['mac_id'])

            if full_path_base_image_file is not None and full_path_xml_template_file is not None and mac is not None:
                subprocess.call(['qemu-img', 'create', '-b', full_path_base_image_file, '-f', 'qcow2', self.__cloned_disk_image_path(image_id)])

                f = open(full_path_xml_template_file, 'r')
                xmlspec = f.read()
                f.close()
                xmlspec = xmlspec.replace('$(VM_ID)', image_id)
                xmlspec = xmlspec.replace('$(IMAGE_FILE)', self.__cloned_disk_image_path(image_id))
                xmlspec = xmlspec.replace('$(MAC_ADDRESS)', mac)
                f = open(self.__cloned_xml_definition_path(image_id), 'w')
                f.write(xmlspec)
                f.close()

        self.sync_lock.release()

    def __poweron_image(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        self.sync_lock.acquire()
        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            full_path_xml_def_file = self.__cloned_xml_definition_path(image_id)
            subprocess.call(['virsh', 'create', full_path_xml_def_file])
        self.sync_lock.release()

    def __poweroff_image(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        self.sync_lock.acquire()
        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            subprocess.call(['virsh', 'destroy', image_id])
        self.sync_lock.release()

    def __destroy_image(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        self.sync_lock.acquire()
        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            os.remove(self.__cloned_disk_image_path(image_id))
            os.remove(self.__cloned_xml_definition_path(image_id))
        self.sync_lock.release()

    def __cleanup_expired_images(self):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)
        bim = DVMPSDAO.BaseImages(dbc)
        mip = DVMPSDAO.MacIpPairs(dbc)
        timenow = int(time.time())

        self.sync_lock.acquire()
        image_ids = ali.get_images()
        for image_id in image_ids:
            image_record = ali.get_configuration(image_id)
            if image_record is not None and image_record.has_key('creation_time') and image_record.has_key('valid_for'):
                time_before_expiry = image_record['creation_time'] + image_record['valid_for'] - int(time.time())
                if time_before_expiry < 0:
                    self.__poweroff_image(image_id)
                    self.__destroy_image(image_id)
                    if image_record.has_key('mac_id'):
                        mip.deallocate(image_record['mac_id'])
                    ali.deallocate(image_id)
        self.sync_lock.release()

    def allocate_image(self, base_image, valid_for, comment):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)
        bim = DVMPSDAO.BaseImages(dbc)
        mip = DVMPSDAO.MacIpPairs(dbc)

        image_id = str(uuid.uuid4())

        self.sync_lock.acquire()
        self.__cleanup_expired_images()

        base_image_conf = bim.get_base_image_configuration_by_name(base_image)
        if base_image_conf is None or not base_image_conf.has_key('id') or not base_image_conf.has_key('base_image_file') or not base_image_conf.has_key('configuration_template'):
            self.sync_lock.release()
            return { 'result': False, 'error': 'No such base image configured' }

        mac_id = mip.allocate(valid_for=valid_for)
        if mac_id is None:
            self.sync_lock.release()
            return { 'result': False, 'error': 'Could not allocate a free MAC address' }

        if ali.allocate(image_id, mac_id, base_image_conf['id'], valid_for=valid_for, comment=comment) == False:
            mip.deallocate(mac_id)
            self.sync_lock.release()
            return { 'result': False, 'error': 'Failed to allocate image' }

        ip_addr = mip.get_ip_for_mac_id(mac_id)

        self.__create_image(image_id)
        self.__poweron_image(image_id)

        ret_val = { 'result': True, 'image_id': image_id, 'ip_addr': ip_addr, 'base_image': base_image, 'valid_for': valid_for }        
        self.sync_lock.release()
        return ret_val

    def deallocate_image(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)
        mip = DVMPSDAO.MacIpPairs(dbc)

        self.sync_lock.acquire()
        self.__cleanup_expired_images()
        ret_val = { 'result': False, 'error': 'No such image' }

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            self.__poweroff_image(image_id)
            self.__destroy_image(image_id)
            if allocated_image_conf.has_key('mac_id'):
                mip.deallocate(allocated_image_conf['mac_id'])
            ali.deallocate(image_id)
            ret_val = { 'result': True, 'image_id': image_id, 'status': 'not-allocated' }

        self.sync_lock.release()
        return ret_val

    def revert_image(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        self.sync_lock.acquire()
        self.__cleanup_expired_images()
        ret_val = { 'result': False, 'error': 'No such image' }

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            self.__poweroff_image(image_id)
            self.__destroy_image(image_id)
            self.__create_image(image_id)
            self.__poweron_image(image_id)
            ret_val = { 'result': True, 'image_id': image_id }

        self.sync_lock.release()
        return ret_val

    def __image_status(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)
        bim = DVMPSDAO.BaseImages(dbc)
        mip = DVMPSDAO.MacIpPairs(dbc)

        self.sync_lock.acquire()
        ret_val = None

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            valid_for = 0
            ip_addr = None
            base_image = None
            comment = None

            if allocated_image_conf.has_key('creation_time') and allocated_image_conf.has_key('valid_for'):
                valid_for = allocated_image_conf['creation_time'] + allocated_image_conf['valid_for'] - int(time.time())
            if allocated_image_conf.has_key('mac_id'):
                ip_addr = mip.get_ip_for_mac_id(allocated_image_conf['mac_id'])
            if allocated_image_conf.has_key('base_image_id'):
                base_image_record = bim.get_base_image_configuration(allocated_image_conf['base_image_id'])
                if base_image_record is not None and base_image_record.has_key('base_image_name'):
                    base_image = base_image_record['base_image_name']
            if allocated_image_conf.has_key('comment'):
                comment = allocated_image_conf['comment']
            ret_val = { 'result': True, 'image_id': image_id, 'status': 'allocated', 'ip_addr': ip_addr, 'base_image': base_image, 'valid_for': valid_for, 'comment': comment }

        self.sync_lock.release()
        return ret_val

    def image_status(self, image_id):
        self.sync_lock.acquire()
        self.__cleanup_expired_images()
        ret_val = self.__image_status(image_id)
        if ret_val is None:
            ret_val = { 'result': True, 'image_id': image_id, 'status': 'not-allocated' }
        self.sync_lock.release()
        return ret_val

    def poweroff_image(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        self.sync_lock.acquire()
        self.__cleanup_expired_images()
        ret_val = { 'result': False, 'error': 'no such image' }

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            self.__poweroff_image(image_id)
            ret_val = { 'result': True, 'image_id': image_id }

        self.sync_lock.release()
        return ret_val

    def poweron_image(self, image_id):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        self.sync_lock.acquire()
        self.__cleanup_expired_images()
        ret_val = { 'result': False, 'error': 'no such image' }

        allocated_image_conf = ali.get_configuration(image_id)
        if allocated_image_conf is not None:
            self.__poweron_image(image_id)
            ret_val = { 'result': True, 'image_id': image_id }

        self.sync_lock.release()
        return ret_val

    def status(self):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        self.sync_lock.acquire()
        self.__cleanup_expired_images()
        images = ali.get_images()
        ret_val = { 'result': True, 'allocated_images': len(images) }
        self.sync_lock.release()
        return ret_val

    def running_images(self):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        ali = DVMPSDAO.AllocatedImages(dbc)

        self.sync_lock.acquire()
        self.__cleanup_expired_images()
        images = ali.get_images()
        image_statuses = []
        for image in images:
            image_status = self.__image_status(image)
            if image_status != None:
                image_statuses.append(image_status)
        ret_val = { 'result': True, 'running_images': image_statuses }
        self.sync_lock.release()
        return ret_val

    def base_images(self):
        dbc = DVMPSDAO.DatabaseConnection(database=self.database)
        bim = DVMPSDAO.BaseImages(dbc)

        self.sync_lock.acquire()
        base_images = bim.get_base_images()
        self.sync_lock.release()
        return { 'result': True, 'base_images': base_images }
