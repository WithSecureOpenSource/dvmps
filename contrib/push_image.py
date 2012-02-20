#!/usr/bin/env python
'''
    WARNING: this tool are made based on the configuration of the Dynamic Provisioning
    Servers configuration at the time of writing, should the servers configurations
    changes this tool may not be relevent anymore. It was also made hastly, this works
    for me, use at your own risk :)

    In a nutshell, the tool is made to copy the KVM image and config to its proper
    location and also create required entry in the dabatase over ssh.

    It attempt to do the follwing in sequence, and fail if condition is not meet.
    1. fail if login invalid.
    2. fail if has no file write permission
    3. fail if has no db insert permission
    4. fail if image or xml config file exists (condition is overwritable)
    5. fail if db entry with the same name exists (condition is overwritable)
    6. copy image file to remote server
    7. copy xml config file to remote server
    8. insert db record
'''
import paramiko
import optparse
import socket
import sys
import os

#----------------------------------------------------------------------------
class PushImageException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

#----------------------------------------------------------------------------

remote_servers = [ {'host': '10.133.34.2'},
                   {'host': '10.133.34.3'},
                   {'host': '10.133.34.4'},
                   {'host': '10.133.34.5'},
                   {'host': '10.133.34.6'},
                   {'host': '10.133.34.7'},
                   {'host': '10.133.34.8'},
                 ]

# libvirt-qemu:kvm
remote_img_path = '/var/lib/libvirt/images/base/'
remote_cfg_path = '/var/lib/libvirt/qemu/templates/'
#remote_img_path = '/home/hengze/'
#remote_cfg_path = '/home/hengze/'

# use to check if have permission to write and delete
remote_imgtouch = "junk_please_delete.tmp"
remote_cfgtouch = "junk_please_delete.tmp"

#----------------------------------------------------------------------------
# 1. check login credential and permission to write
# 2. check postgres access
# 3.
#
def status(message):
    sys.stdout.write(message)


#----------------------------------------------------------------------------
def check_filesystem_rw(ssh, path_name, file_name, host_name):
    '''
    '''
    full_path = os.path.join( path_name, file_name )

    # try to write
    error_msg = ssh.exec_command("touch %s" % full_path)[2].readlines()
    if len(error_msg) > 0:
        raise PushImageException("Failed to write to %r at %r.\n%r" % (path_name, host_name, error_msg))

    # try to delete
    error_msg = ssh.exec_command("rm %s" % full_path)[2].readlines()
    if len(error_msg) > 0:
        raise PushImageException("Failed to delete %r at %r.\n%r" % (path_name, host_name, error_msg))


def check_database_insert(ssh, host_name):
    '''
    '''
    # get the current database username
    stdin, stdout, stderr = ssh.exec_command("psql dvmps -c 'select CURRENT_USER AS user;'")
    stdout_result = stdout.readlines()
    stderr_result = stderr.readlines()

    # not able to get db user name?
    if len(stderr_result) > 0:
        raise PushImageException("Failed to access database at %r.\n%r" % (host_name, stderr_result))

    # parse output to get user name.
    # expected output:
    #   user
    #  ------
    #   root
    #  (1 row)
    db_user = stdout_result[2].strip()

    # check if the current user has the insert permission
    # select has_table_privilege('dummyuser','public.base_images','insert');
    stdin, stdout, stderr = ssh.exec_command("psql dvmps -c \"select has_table_privilege('%s','public.base_images','insert')\"" % db_user)
    stdout_result = stdout.readlines()
    stderr_result = stderr.readlines()

    # parse output to get privileges info
    # expected output:
    # has_table_privilege
    # ---------------------
    # t
    #(1 row)
    has_privilege = stdout_result[2].strip()
    if has_privilege == 't':
        return


    raise PushImageException("User %r has no privilege to insert into table 'public.base_images' at %r\n%r" % (db_user, host_name, stderr_result))


#----------------------------------------------------------------------------
def is_file_exists(ssh, path_name, file_name, host_name):
    ''' return True if the file exists, False otherwise.
    '''
    full_path = os.path.join( path_name, file_name )

    # execute ls and if there is something return it exists
    stdout_msg = ssh.exec_command("ls %r" % full_path)[1].readlines()
    if len(stdout_msg) > 0:
        return True

    return False


#----------------------------------------------------------------------------
def is_db_entry_exists(ssh, base_image_name):
    # psql dvmps -c "select * from base_images where base_image_name='hengze-debian6-x64';"
    #
    #  id |  base_image_name   |     configuration_template      |     base_image_file      |       description
    # ----+--------------------+---------------------------------+--------------------------+-------------------------
    #  33 | hengze-debian6-x64 | template-hengze-debian6-x64.xml | hengze-debian6-x64.qcow2 | hengze debian6 test box
    # (1 row)
    #
    # find if the db entry with the same base_image_name already exists
    stdin, stdout, stderr = ssh.exec_command("psql dvmps -c \"select * from base_images where base_image_name=%r\"" % base_image_name)
    stdout_result = stdout.readlines()
    stderr_result = stderr.readlines()

    # expecting "(0 rows)" if no row is return
    if stdout_result[-2].strip() == "(0 rows)":
        return False

    return True


#----------------------------------------------------------------------------
def scp_file(ssh, local_filename, remote_filename):
    # Start a scp channel
    trans = ssh.get_transport()
    scp_channel = trans.open_session()

    f = file(local_filename, 'rb')
    scp_channel.exec_command('scp -v -t %s\n'
                             % '/'.join(remote_filename.split('/')[:-1]))
    scp_channel.send('C%s %d %s\n'
                     %(oct(os.stat(local_filename).st_mode)[-4:],
                       os.stat(local_filename)[6],
                       remote_filename.split('/')[-1]))
    #scp_channel.sendall(f.read())
    chunk = f.read(1024)
    while chunk:
        scp_channel.send(chunk)
        chunk = f.read(1024)


    # Cleanup
    f.close()
    scp_channel.close()


#----------------------------------------------------------------------------
def write_db(ssh, base_image_name, configuration_template, base_image_file, description, overwrite):
    entry_exists = is_db_entry_exists(ssh, base_image_name)
    if overwrite == False and entry_exists == True:
        raise PushImageException("base_image_name %r exists but overwrite flag is false, abort!" % base_image_name)

    command = ""
    if entry_exists:
        # exists, use update
        command = "psql dvmps -c \"update base_images set configuration_template=%r, base_image_file=%r, description=%r where base_image_name=%r;\"" % \
                  (configuration_template, base_image_file, description, base_image_name)
    else:
        # not exists, insert
        command = "psql dvmps -c \"insert into base_images (base_image_name, configuration_template, base_image_file, description) VALUES (%r, %r, %r, %r);\"" % \
                  (base_image_name, configuration_template, base_image_file, description)

    # find if the db entry with the same base_image_name already exists
    stdin, stdout, stderr = ssh.exec_command(command)
    stdout_result = stdout.readlines()
    stderr_result = stderr.readlines()

    if len(stderr_result) > 0:
        raise PushImageException("Failed to write to db!\n%r" % stderr_result)


#----------------------------------------------------------------------------
# main :)
#----------------------------------------------------------------------------
def main():
    ## Check params
    cfg_parser = optparse.OptionParser(usage  = "usage: %prog image_file config_file template_name description",
                                       epilog = "e.g: $ push_image.py winxp.qcow winxp.xml WinXp_x64 '64bit winxp'")

    cfg_parser.add_option("--overwrite",
                          dest="overwrite",
                          default=False,
                          action="store_true",
                          help="overwrite image or config or template entry even if it's already exists.")

    cfg_parser.add_option("--user",
                          dest="username",
                          default="root",
                          help="user name used to connect to remote servers")

    cfg_parser.add_option("--pass",
                          dest="password",
                          default="",
                          help="password used to connect to remote servers")

    # parse params
    (options, args) = cfg_parser.parse_args()

    if len(args) != 4:
        cfg_parser.print_help()
        raise PushImageException("invalid parameter count. must have 4 required arguments.")

    # mandatory args
    img_file_name = args[0]
    cfg_file_name = args[1]
    template_name = args[2]
    description   = args[3]

    # makesure image and config file exists
    if not os.path.exists(img_file_name):
        raise PushImageException("kvm image file not found! [%r]" % img_file_name)
    if not os.path.exists(cfg_file_name):
        raise PushImageException("config file for kvm image not found! [%r]" % cfg_file_name)

    # fillup user name and password
    for server in remote_servers:
        server['user'] = options.username
        server['pass'] = options.password

    ssh_conns = []
    try:
        # collecting valid connections
        for server in remote_servers:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy( paramiko.AutoAddPolicy() )

            #
            # try to login
            status(".")
            ssh.connect( server['host'], username=server['user'], password=server['pass'] )
            ssh_conns.append(ssh)


            #
            # check if write permission is allowed at image location
            status(".")
            check_filesystem_rw( ssh, remote_img_path, remote_imgtouch, server['host'] )

            #
            # check if write permission is allowed at config location
            status(".")
            check_filesystem_rw( ssh, remote_cfg_path, remote_cfgtouch, server['host'] )

            #
            # check if has insert permission in database
            # SELECT CURRENT_USER AS myself;
            # select has_table_privilege('dummyuser','public.base_images','insert');
            status(".")
            check_database_insert( ssh, server['host'] )

            #
            # only check if not overwite existing changes
            if options.overwrite != True:
                # check if database entry exists
                if is_db_entry_exists( ssh, template_name ):
                    raise PushImageException("template name %r already registered in database at %r." % (template_name, server['host']))

                # check if image file exists
                file_name = os.path.basename(img_file_name)
                if is_file_exists( ssh, remote_img_path, file_name, server['host'] ):
                    raise PushImageException("remote file %r at %r already exists at %r." % (file_name, remote_img_path, server['host']))

                # check if config file exists
                file_name = os.path.basename(cfg_file_name)
                if is_file_exists( ssh, remote_cfg_path, file_name, server['host'] ):
                    raise PushImageException("remote file %r at %r already exists at %r" % (file_name, remote_cfg_path, server['host']))

        # write changes to remote servers
        status("\n")
        for ssh in ssh_conns:
            # copy image file (qcow2)
            img_remote_pathname = os.path.join(remote_img_path,  os.path.basename(img_file_name))
            status("copying %r to %r ...\n" % (img_file_name, img_remote_pathname))
            scp_file(ssh, img_file_name, img_remote_pathname)

            # copy config file (xml)
            cfg_remote_pathname = os.path.join(remote_cfg_path,  os.path.basename(cfg_file_name))
            status("copying %r to %r ...\n" % (cfg_file_name, cfg_remote_pathname))
            scp_file(ssh, cfg_file_name, cfg_remote_pathname)

            # write db entry
            status("writing db entry for %r ...\n" % template_name)
            write_db(ssh, template_name, os.path.basename(cfg_file_name), os.path.basename(img_file_name), description, options.overwrite)

    finally:
        for ssh in ssh_conns:
            ssh.close()


#----------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        main()
    except PushImageException, ex:
        print( "\nError: %s\n" % str(ex) )

