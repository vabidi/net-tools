#!/usr/bin/python

import sys
import os
import argparse
import re
import subprocess
import json

hosts = ["10.2.32.4", "10.2.32.5", "10.2.32.6"]


ESX_PEM_FILE = "/root/vmc/vabidi-perf2-esx.pem"
PROXY_PEM_FILE = "/root/vmc/vabidi-perf2.pem" 
POPVM_UH = "vmc-ankitparmar@pop.sddc-52-33-168-54.vmc.vmware.com"


OPTS = "-o StrictHostKeyChecking=no " \
       "-o UserKnownHostsFile=/dev/null -o loglevel=quiet"


class RemoteHost(object):
    """ Support calling local scripts remote. """

    def __init__(self, hostname, keyfile, proxy_keyfile):
        """ host in the form of user@hostname. """
        self._user = "root"
        self._hostname = hostname
        self._keyf = keyfile
        self._proxykf = proxy_keyfile
        self._remote_root = "/tmp"
        self._proxy_cmd = "ssh -W %%h:%%p -i %s %s" % (self._proxykf, POPVM_UH)

    def userhostnameget(self):
        """ Return user and host name. """
        return "%s@%s" % (self._user, self._hostname)


    def callremote_stdout(self, workdir, remote_script):
        """ Call a script on a remote system.
        The current working directory on the remote system is define
        by self._remote_root.
        """
        workdir = os.path.join(self._remote_root, workdir)
        cmd1 = "ssh %(opts)s -i %(keyf)s -o ProxyCommand='%(prx)s' " % \
                {"opts": OPTS,
                "keyf": self._keyf,
                "prx" : self._proxy_cmd
                }

        cmd2 =  "%(ush)s 'cd %(wd)s; %(prog)s'" % \
                {
                "ush" : self.userhostnameget(),
                "wd"  : workdir,
                "prog": remote_script
                }

        cmd = cmd1 + cmd2
        result = subprocess.check_output(cmd, shell=True)
        return result


def remote_host_create(hostname):
    """ Return a handle to a remote host. """

    keyfile = ESX_PEM_FILE
    proxy_keyfile = PROXY_PEM_FILE
    return RemoteHost(hostname, keyfile, proxy_keyfile)


def parseArgs(argv):
    parser = argparse.ArgumentParser()
    #parser.add_argument("test_name", help="name of test")
    #parser.add_argument("--cmd", help="command string")
    args = parser.parse_args()
    return args

def get_nics(sut, vmid):
    cmd = "vim-cmd vmsvc/get.guest %s" % vmid
    out = sut.callremote_stdout("/tmp", cmd)
    out = out.decode('utf-8')
    lines = out.split("\n")

    inside = 0
    result = {}
    nic_count = 0
    name = "eth%d" % nic_count
    for line in lines:
        if "vim.vm.GuestInfo.NicInfo" in line:
            inside = 1
        elif "vim.net.IpConfigInfo.IpAddress" in line:
            inside = 2
        #Get the network information for each vnic
        if inside == 1:
            find = re.search(r'network = "([\w0-9\ ]+)"', line)
            if find:
                inside = 0
                continue
        #Get the ip of each vnic
        if inside == 2:
            if "]" in line:
                nic_count += 1
                #re-initialize 'nic'
                name = "eth%d" % nic_count
                inside = 0
                continue
            find = re.search(r'ipAddress = "(\d+\.\d+\.\d+\.\d+)",', line)
            if find:
                result[name] = find.group(1)
    return result

def get_vminfo(sut, vmi):
    info = {}
    out = vmi.decode('utf-8')
    lines = out.split("\n")
    lines = lines[1:]
    lines = [item for item in lines if len(item) > 0]
    #each line corresponds to one vm
    for line in lines:
        cols = [item for item in line.split(" ") if len(item) > 0]
        vimid = cols[0]
        name =  cols[1]
        nics = get_nics(sut, vimid)
        info[name] = nics
  
    return info

if __name__ == '__main__':
    allvms = {}
    for host in hosts:
        print "Fetching VM information from %s" % host
    	cmd = "vim-cmd vmsvc/getallvms"
    	sut1 = remote_host_create(host)
    	out = sut1.callremote_stdout("/tmp", cmd)
    	vmnics = get_vminfo(sut1, out)
        print "Found %d VMs" % len(vmnics)
        with open('vms_on_%s' % host, 'w') as outfile:
            json.dump(vmnics, outfile)
        allvms.update(vmnics)
    with open('allvms.json', 'w') as outfile:
        json.dump(allvms, outfile)
    print "Wrote file allvms.json"

  
