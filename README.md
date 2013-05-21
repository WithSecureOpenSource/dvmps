
---------------------------
1. Building DVMPS packages
---------------------------

1. Go to dvmps directory
2. Update the changelog if needed eg. for adding extra version information
  $ dch -i "comment"
     or
  $ dch -l-$USER "comment"
3. Build packages
  $ dpkg-buildpackage


----------------------------------------
2. Installing and running DVMPS service
----------------------------------------
1. Install
  $ dpkg -i dvmps-server-<version>_all.deb
2. Setup DVMPS
  $ dvmps-setup
3. Running and stopping DVMPS service
  $ service dvmps {start|stop|restart}

Additional configurations:
1. Update server clock regularly. Two options:
  a) Install and configure 'ntp' (Network Time Protocol daemon) for automatic
     system clock updates
  b) Install 'ntpdate' and use cron to update the system clock


2.1. Munin-node configuration
------------------------------
Install munin-dvmps-plugin on the same machine as dvmps-server. For allowing Munin web UI to be viewed from external sources check the munin-node allow rule.

Open the /etc/munin/munin-node.conf file and look for the line beginning with word 'allow'.
For allowing all taffic, change the line to "allow .*" and restart munin-node.
  $ service munin-node restart


2.2. Setting up guest a image
------------------------------
There are few options for creating the disk image, like install the 
guest OS from scratch or convert an existing guest image to kvm qcow2 format.

1.a Installing from ISO
  # Create an 8G qcow2 image
  $ qemu-img create -f qcow2 -o preallocation=metadata disk_image.qcow2 8G
  # Install OS
  $ virt-install --connect=qemu:///system \
        --name debian-stable \
        --ram 2048 \
        --vcpus=2 \
        --os-type linux \
        --os-variant debiansqueeze \
        --disk path=<path>disk_image.qcow2 \
        --cdrom <path>debian-7.0.0-amd64-DVD-1.iso \
        --graphics vnc

1.b Converting from existing image 
  $ qemu-img convert system.vmdk -O qcow2 disk_image.qcow2

1.c Copy an existing qcow2 image and name it 'disk_image.qcow2'

2. Create libvirt xml configuration
  Use the template/virtual_machine_config.xml as a template 

3. Move the disk_image.qcow2 and virtual_machine_config.xml files
   in a subdirectory under the libvirt image directory:
       /var/lib/libvirt/images/<image name>/


---------------------------------------
3. Installing and running DVMPS client
---------------------------------------
1. Install
  $ dpkg -i dvmps-client-<version>_all.deb

2. Run from command line. Example:
  $ dvmps --serverurl http://<dvmps server address> create <base_image>
  $ dvmps --serverurl http://<dvmps server address> poweron <image_id>

3. Using from python script. Example:
#!/usr/bin/python
import DVMPSClient

ret = DVMPSClient.create(serverurl, image, validfor, priority, comment)
if image_id in ret:
    DVMPSClient.poweron(serverurl, ret['image_id'])

# For more details about the python API see /usr/share/pyshared/DVMPSClient.py


