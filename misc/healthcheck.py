import subprocess
import urllib2
import urlparse

def run_command(command_and_args, shell=False):
    proc = subprocess.Popen(command_and_args, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (sout,serr) = proc.communicate()
    return (proc.returncode, sout, serr)

def test_connections(hostnames, mustpass=1):
    successful = 0
    for hostname in hostnames:
        url = urlparse.urlunsplit(('http', hostname, '', '', ''))
        try:
            o = urllib2.urlopen(url)
            d = o.read()
            successful = successful + 1
        except:
            pass
    if successful < mustpass:
        return False
    return True

def test_libvirt():
    (rc,out,err) = run_command(['/etc/init.d/libvirt-bin', 'status'])
    if rc != 0:
        return False
    return True        

if __name__ == '__main__':
    # FIXME: read list of cluster hosts from some common configuration file created in setup - debian installation pkg is not used only on GTN cluster
    alive = test_connections(['dvmps01.infra.gtn','dvmps02.infra.gtn','dvmps03.infra.gtn','dvmps04.infra.gtn','dvmps05.infra.gtn'], mustpass=2)
    if alive == True:
	alive = test_libvirt()
    if alive == False:
        (rc,out,err) = run_command(['/sbin/shutdown','-r','5','connection lost to GW'])
