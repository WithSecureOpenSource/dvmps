import pgdb
import time

class DatabaseConnection:
    def __init__(self, database=None, host=None, user=None, password=None):
        self.dbconnection = pgdb.connect(database=database, host=host, user=user, password=password)

    def __del__(self):
        if self.dbconnection is not None:
            self.dbconnection.close()
            self.dbconnection = None

class BaseImages:
    def __init__(self, dbaseconnection):
        self.dbc = dbaseconnection

    def get_base_image_configuration_by_name(self, base_image_name):
        ret = None
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select id, base_image_name, configuration_template, base_image_file, description from base_images where base_image_name = %s", (base_image_name,))
        if cursor.rowcount > 0:
            base = cursor.fetchone()
            ret = { "id": base[0], "base_image_name" : base[1], "configuration_template": base[2], "base_image_file": base[3], "description": base[4] }
        cursor.close()
        return ret

    def get_base_image_configuration(self, base_image_id):
        ret = None
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select id, base_image_name, configuration_template, base_image_file, description from base_images where id = %d", (base_image_id,))
        if cursor.rowcount > 0:
            base = cursor.fetchone()
            ret = { "id": base[0], "base_image_name" : base[1], "configuration_template": base[2], "base_image_file": base[3], "description": base[4] }
        cursor.close()
        return ret

class MacIpPairs:
    def __init__(self, dbaseconnection):
        self.dbc = dbaseconnection

    def allocate(self, valid_for=3600):
        ret = None
        timenow = int(time.time())
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select id, mac, ip, allocated, allocation_time from mac_ip_pairs where allocated is false order by allocation_time")
        free_pairs = cursor.fetchall()
        for pair in free_pairs:
            cursor.execute("update mac_ip_pairs set allocated = true, allocation_time = %d, valid_for = %d where id = %d and allocated is false and allocation_time = %d", (timenow, valid_for, pair[0], pair[4]))
            if cursor.rowcount > 0:
                self.dbc.dbconnection.commit()
                ret = pair[0]
                break
            self.dbc.dbconnection.rollback()
        cursor.close()
        return ret

    def deallocate(self, mac_id):
        timenow = int(time.time())
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("update mac_ip_pairs set allocated = false, allocation_time = %d where id = %d and allocated is true", (timenow, mac_id))
        self.dbc.dbconnection.commit()
        cursor.close()

    def renew(self, mac_id, valid_for=3600):
        result = False
        timenow = int(time.time())
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("update mac_ip_pairs set allocation_time = %d, valid_for = %d where id = %d and allocated is true", (timenow, valid_for, mac_id))
        if cursor.rowcount > 0:
            result = True
        self.dbc.dbconnection.commit()
        cursor.close()
        return result

    def cleanup(self):
        timenow = int(time.time())
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("select id, mac, ip, allocated, allocation_time, valid_for from mac_ip_pairs where allocated is true")
        allocated_pairs = cursor.fetchall()
        for pair in allocated_pairs:
            if pair[3] + pair[4] > timenow:
                cursor.execute("update mac_ip_pairs set allocated = false, allocation_time = %d where id = %d and allocated is true and allocation_time = %d", (timenow, pair[0], pair[4]))
                self.dbc.dbconnection.commit()
        cursor.close()

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

    def allocate(self, instance_name, mac_id, base_image_id, valid_for=3600, comment=''):
        result = False
        timenow = int(time.time())
        cursor = self.dbc.dbconnection.cursor()
        cursor.execute("insert into allocated (instance_name, mac_id, base_image_id, creation_time, valid_for, comment) values (%s, %d, %d, %d, %d, %s)", (instance_name, mac_id, base_image_id, timenow, valid_for, comment))
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
        cursor.execute("select id, instance_name, mac_id, base_image_id, creation_time, valid_for, comment from allocated where instance_name = %s", (instance_name,))
        if cursor.rowcount > 0:
            image = cursor.fetchone()
            ret = { "id": image[0], "instance_name" : image[1], "mac_id": image[2], "base_image_id": image[3], "creation_time": image[4], "valid_for": image[5], "comment": image[6] }
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
