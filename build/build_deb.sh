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

mkdir build_deb

mkdir -p build_deb/DEBIAN/

mkdir -p build_deb/opt/dvmps/bin
mkdir -p build_deb/opt/dvmps/scripts
#mkdir -p build_deb/opt/dvmps/extra
mkdir -p build_deb/var/opt/dvmps

cp $2/misc/dvmps.init build_deb/DEBIAN/

cp $2/service/DVMPSCleanup.py build_deb/opt/dvmps/bin/
cp $2/service/DVMPSClient.py build_deb/opt/dvmps/bin/
cp $2/service/DVMPSDAO.py build_deb/opt/dvmps/bin/
cp $2/service/DVMPSPlacementAgent.py build_deb/opt/dvmps/bin/
cp $2/service/DVMPSService.py build_deb/opt/dvmps/bin/
cp $2/service/DVMPSWSGIFlup.py build_deb/opt/dvmps/bin/
cp $2/service/DVMPSWSGI.py build_deb/opt/dvmps/bin/
cp $2/service/DVMPSWSGIRef.py build_deb/opt/dvmps/bin/

cp $2/scripts/check_kvm build_deb/opt/dvmps/scripts/
cp $2/scripts/setup build_deb/opt/dvmps/scripts/
cp $2/scripts/setup_apt build_deb/opt/dvmps/scripts/
cp $2/scripts/setup_database build_deb/opt/dvmps/scripts/
cp $2/scripts/setup_libvirt build_deb/opt/dvmps/scripts/
cp $2/scripts/setup_network build_deb/opt/dvmps/scripts/

cat > build_deb/DEBIAN/control <<EOF
Package: dvmps
Version: $1
Architecture: all
Maintainer: Heikki Nousiainen <heikki.nousiainen@f-secure.com>
Depends: libvirt-bin, qemu-kvm, nginx, python-flup, python-libvirt, python-pygresql, postgresql, isc-dhcp-server, munin-node, ntpdate
Description: Dynamic virtual machine provisioning service
 Dynamic virtual machine provisioning service
EOF

dpkg -b build_deb dvmps_$1.deb
