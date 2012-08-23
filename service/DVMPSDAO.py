#!/usr/bin/python

import pgdb
import time
import random
import os
import logging
import sys

class DatabaseConnection:
    def __init__(self, database=None, host=None, user=None, password=None):
        self.dbconnection = pgdb.connect(database=database, host=host, user=user, password=password)

    def __del__(self):
        if self.dbconnection is not None:
            self.dbconnection.close()
            self.dbconnection = None

class MacIpPairs:
    def __init__(self, dbaseconnection):
        self.dbc = dbaseconnection
        self.logger = logging.getLogger('dvmps')

    def allocate(self, image_id):
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select id, mac, ip from mac_ip_pairs")
        free_pairs = cursor.fetchall()
        cursor.close()
        random.shuffle(free_pairs)
        for pair in free_pairs:
            try:
                fn = os.path.join('/var/lib/libvirt/ip_mac_allocations', pair[1].replace(':', '-'))
                fh = os.open(fn, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                os.write(fh, str(image_id))
                os.close(fh)
                return pair[0]
            except OSError, e:
                if e.errno != 17:
                    self.logger.error("MacIpPairsDAO: registering lock file '%s' failed with errno %d, message '%s'" % (e.errno, e.strerror))
            except:
                self.logger.error("MacIpPairsDAO: registering lock file '%s' failed with exception: '%r'" % (fn, sys.exc_info()[1]))

        return None

    def deallocate(self, mac_id):
        mac = self.get_mac_for_mac_id(mac_id)
        if mac is None:
            self.logger.error("MacIpPairsDAO: cannot map_id %d to mac address" % mac_id)
            return
        fn = os.path.join('/var/lib/libvirt/ip_mac_allocations', mac.replace(':', '-'))
        try:
            os.unlink(fn)
        except:
            self.logger.warn("MacIpPairsDAO: deleting lock file '%s' failed with exception: '%r'" % (sys.exc_info()[1]))

    def get_mac_for_mac_id(self, mac_id):
        mac = None
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select mac from mac_ip_pairs where id = %d", (mac_id,))
        res = cursor.fetchone()
        if res is not None:
            mac = res[0]
        cursor.close()
        return mac

    def get_ip_for_mac_id(self, mac_id):
        ip = None
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select ip from mac_ip_pairs where id = %d", (mac_id,))
        res = cursor.fetchone()
        if res is not None:
            ip = res[0]
        cursor.close()
        return ip

    def get_mac_id_for_mac(self, mac):
        mac_id = None
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select id from mac_ip_pairs where mac = %s", (mac,))
        res = cursor.fetchone()
        if res is not None:
            mac_id = res[0]
        cursor.close()
        return mac_id

    def get_ip_for_mac(self, mac):
        ip = None
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select ip from mac_ip_pairs where mac = %s", (mac,))
        res = cursor.fetchone()
        if res is not None:
            ip = res[0]
        cursor.close()
        return ip

class AllocatedImages:
    def __init__(self, dbaseconnection):
        self.dbc = dbaseconnection
        self.logger = logging.getLogger('dvmps')

    def allocate(self, instance_name, mac_id, base_image_name, valid_for=3600, priority=50, comment=''):
        result = False
        timenow = int(time.time())
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("insert into allocated (instance_name, mac_id, base_image_name, creation_time, valid_for, priority, comment) values (%s, %d, %s, %d, %d, %d, %s)", (instance_name, mac_id, base_image_name, timenow, valid_for, priority, comment))
        if cursor.rowcount > 0:
            result = True
        self.dbc.dbconnection.commit()
        cursor.close()
        return result

    def deallocate(self, instance_name):
        result = False
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("delete from allocated where instance_name = %s", (instance_name,))
        if cursor.rowcount > 0:
            result = True
        self.dbc.dbconnection.commit()
        cursor.close()
        return result

    def renew(self, instance_name, valid_for=3600):
        timenow = int(time.time())
        result = False
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("update allocated set creation_time = %d, valid_for = %d where instance_name = %s", (timenow, valid_for, instance_name))
        if cursor.rowcount > 0:
            result = True
        self.dbc.dbconnection.commit()
        cursor.close()
        return result

    def get_configuration(self, instance_name):
        ret = None
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select id, instance_name, mac_id, base_image_name, creation_time, valid_for, priority, comment from allocated where instance_name = %s", (instance_name,))
        if cursor.rowcount > 0:
            image = cursor.fetchone()
            ret = { "id": image[0], "instance_name" : image[1], "mac_id": image[2], "base_image_name": image[3], "creation_time": image[4], "valid_for": image[5], "priority": image[6], "comment": image[7] }
        cursor.close()
        return ret

    def get_images(self):
        ret = []
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select instance_name from allocated")
        image_records = cursor.fetchall()
        for image in image_records:
            ret.append(image[0])
        cursor.close()
        return ret

    def get_images_below_priority(self, priority):
        ret = []
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select instance_name from allocated where priority < %d order by priority", (priority,))
        image_records = cursor.fetchall()
        for image in image_records:
            ret.append(image[0])
        cursor.close()
        return ret
