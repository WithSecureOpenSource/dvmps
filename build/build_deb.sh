#!/bin/sh
#
# Copyright (c) 2012 F-Secure Corporation. All Rights Reserved.
#

set -e

if [ -z "$1" -o -z "$2" ]; then
    echo "Usage: build_deb.sh <version> <rootdir>"
    exit 1
fi

if test -d build_deb; then
    rm -rf build_deb
fi

mkdir -p build_deb/DEBIAN/

install -d build_deb/opt/dvmps/bin
install -d build_deb/opt/dvmps/setup_scripts
install -d build_deb/opt/dvmps/extra
install -d build_deb/opt/dvmps/extra/munin
install -d build_deb/etc/cron.hourly
install -d build_deb/etc/cron.d
install -d build_deb/etc/init.d
install -d build_deb/var/opt/dvmps/run
install -d build_deb/etc/default

install -m 0644 $2/service/DVMPSCleanup.py build_deb/opt/dvmps/bin/
install -m 0644 $2/service/DVMPSClient.py build_deb/opt/dvmps/bin/
install -m 0644 $2/service/DVMPSDAO.py build_deb/opt/dvmps/bin/
install -m 0644 $2/service/DVMPSPlacementAgent.py build_deb/opt/dvmps/bin/
install -m 0644 $2/service/DVMPSService.py build_deb/opt/dvmps/bin/
install -m 0644 $2/service/DVMPSWSGIFlup.py build_deb/opt/dvmps/bin/
install -m 0644 $2/service/DVMPSWSGI.py build_deb/opt/dvmps/bin/
install -m 0644 $2/service/DVMPSWSGIRef.py build_deb/opt/dvmps/bin/

install -m 0644 $2/misc/healthcheck.py build_deb/opt/dvmps/bin/

install -m 0755 $2/scripts/check_kvm build_deb/opt/dvmps/setup_scripts/
install -m 0755 $2/scripts/setup build_deb/opt/dvmps/setup_scripts/
install -m 0755 $2/scripts/setup_apt build_deb/opt/dvmps/setup_scripts/
install -m 0755 $2/scripts/setup_database build_deb/opt/dvmps/setup_scripts/
install -m 0755 $2/scripts/setup_dhcpd build_deb/opt/dvmps/setup_scripts/
install -m 0755 $2/scripts/setup_httpd build_deb/opt/dvmps/setup_scripts/
install -m 0755 $2/scripts/setup_libvirt build_deb/opt/dvmps/setup_scripts/
install -m 0755 $2/scripts/setup_munin_node build_deb/opt/dvmps/setup_scripts/
install -m 0755 $2/scripts/setup_network build_deb/opt/dvmps/setup_scripts/

install -m 0644 $2/misc/dhcp_config_generator.py build_deb/opt/dvmps/extra/
install -m 0644 $2/misc/dns_config_generator.py build_deb/opt/dvmps/extra/
install -m 0644 $2/misc/dns_reverse_config_generator.py build_deb/opt/dvmps/extra/
install -m 0644 $2/misc/ipv4addr.py build_deb/opt/dvmps/extra/
install -m 0644 $2/misc/mac_ip_generator.py build_deb/opt/dvmps/extra/

install -m 0644 $2/misc/dvmps.nginx-site build_deb/opt/dvmps/extra/
install -m 0644 $2/misc/dvmps.schema build_deb/opt/dvmps/extra/

install -m 0644 $2/misc/munin/dvmps_dirsizes build_deb/opt/dvmps/extra/munin/
install -m 0644 $2/misc/munin/dvmps_priorities build_deb/opt/dvmps/extra/munin/
install -m 0644 $2/misc/munin/dvmps_priorities_pct build_deb/opt/dvmps/extra/munin/
install -m 0644 $2/misc/munin/dvmps_types build_deb/opt/dvmps/extra/munin/
install -m 0644 $2/misc/munin/dvmps_clonerate build_deb/opt/dvmps/extra/munin/

install -m 0755 $2/misc/cron.hourly/ntpdate build_deb/etc/cron.hourly/
install -m 0755 $2/misc/cron.d/dvmps_cleanup build_deb/etc/cron.d/
install -m 0755 $2/misc/cron.d/healthcheck build_deb/etc/cron.d/

install -m 0755 $2/misc/dvmps.init build_deb/etc/init.d/dvmps
install -m 0644 $2/misc/dvmps.defaults build_deb/etc/default/dvmps

cat > build_deb/DEBIAN/control <<EOF
Package: dvmps
Version: $1
Architecture: all
Maintainer: Heikki Nousiainen <heikki.nousiainen@f-secure.com>
Depends: libvirt-bin, qemu-kvm, nginx, python-flup, python-libvirt, python-pygresql, postgresql, isc-dhcp-server, munin-node, ntpdate
Description: Dynamic virtual machine provisioning service
 Dynamic virtual machine provisioning service
EOF

fakeroot dpkg -b build_deb dvmps_$1.deb
