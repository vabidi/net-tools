#!/bin/python
'''
 Set vdl2 property udpPortInHash=true for all the STC data ports.
 default behaviour is that all flows from a particular STC VM will hash
 into the same pNIC rx queue on the receiver host.
 After setting the above property, hashing will be based on udp ports also.
 '''
import subprocess
import re
cmd = "net-stats -l | grep STC | grep eth1 | awk '{print $1}' "
ob = subprocess.check_output(cmd, shell=True)
ob = ob.decode('utf-8')
ids = ob.strip().split('\n')

cmd = "net-dvs -l"
ob = subprocess.check_output(cmd, shell=True)
ob = ob.decode('utf-8')
lines = ob.strip().split('\n')

# initialize circular buffer.
# we'll store the last 4 lines in this buffer
nidx = 0
buf = ["", "", "", ""]

port_uuids = []

for line in lines:
    buf[nidx] = line.strip()
    nidx = (nidx+1)%4
    find = re.search(r'(portID=)(\d+)', line)
    if find:
        portID = find.group(2)
        if portID not in ids:
            continue
        # now search for port UUID in stored lines
        prevline = buf[nidx]
        find2 = re.search(r'(port) ([a-f,0-9,\-]*)', prevline)
        if find2:
            port_uuid = find2.group(2)
            print("portID = %s  UUID = %s" % (portID, port_uuid))
            port_uuids.append(port_uuid)

for port_uuid in port_uuids:
    cmd = 'net-dvs -s "com.vmware.port.extraConfig.vdl2.udpPortsInHash=true" -p %s vmc-hostswitch' % port_uuid
    print(cmd)
    ob = subprocess.check_output(cmd, shell=True)
