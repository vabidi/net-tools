#!/usr/bin/python

import sys
import os
import argparse
import yaml
import json
import sys
import logging
# use fabric<2.0
from fabric.decorators import task, parallel
from fabric.operations import run
from fabric.context_managers import env
from fabric.api import execute, quiet
import pdb

# iperf server port
BASEPORT = 5001


def fabric_env(env):
    env.user = 'root'
    env.password = 'ca$hc0w'
    env.host_data = dict()
    return env

def get_vm_ip(vm_info, name):
    mgmt_ip, data_ip = None, None
    for vmm in vm_info:
	for k, val in vmm.items():
		if k == name:
			mgmt_ip = val['mgmt_ip']
			data_ip = val['data_ip']
			return (mgmt_ip, data_ip)	
    return (mgmt_ip, data_ip)

def get_vm_dataip_list(vm_info, names):
    """ Given list of names, return list of IPs """
    data_ips = []
    for name in names:
        data_ip = get_vm_ip(vm_info, name)[1]
        data_ips.append(data_ip)
    return data_ips


def parse_mbps(bwstr, unitstr):
    bw = float(bwstr)
    if unitstr == 'Gbits/sec':
        mbps = int(bw*1000)
    elif unitstr == 'Mbits/sec':
        mbps = int(bw)
    else:
        print "ERROR: Bad unit string %s" % unitstr
	mbps = 0
    return mbps

def iparse_tcp_res(result):
    tot_mbps, tot_sum = 0, 0
    ns, nt = 0, 0
    for value in result.values():
        ns += 1
        lines = [line.strip() for line in value.split('\n')]
        liter = iter(lines)
        for line in liter:
       	    if "sec" in line:
                #pdb.set_trace()
                line = line.split()
                if len(line) > 1:
                    if line[0] == '[SUM]':
                        mbps = parse_mbps(line[-2], line[-1])
                        tot_sum += mbps
                    else:
                        mbps = parse_mbps(line[-2], line[-1])
                        tot_mbps += mbps
                        nt += 1
    # If we parsed the 'SUM' lines, then ignore the per-thread results
    if tot_sum > 0:
        return ns, nt, tot_sum
    else:
        return ns, nt, tot_mbps

def do_test_tcp(argt, configs):
    global env
    sips, dips = [], []
    vm_info = configs['vms']
    streams = configs['test_info']['streams']
    for stream in streams:
        for sbname, val in stream.items():
		tx_vm = val['tx_vm']
		rx_vms = val['rx_vms']
        	sips.append(get_vm_ip(vm_info, tx_vm)[0])
        	dips.append(get_vm_dataip_list(vm_info, rx_vms))
        
    env = fabric_env(env)
    env.hosts = sips
    for i, sip in enumerate(sips):
        env.host_data[sip] = {'dest': dips[i], 'duration': argt.duration, 
                              'P': argt.pthreads}
    res = execute(test_tcp)
    ns, nt, mbps = iparse_tcp_res(res)
    print "clients=%d threads=%d Total Mbps = %d" % (ns, nt, mbps)


@parallel
def test_tcp():
    cmdf = " -P %(P)s  -t %(duration)s"
    subcmd = cmdf % env.host_data[env.host]
    destinations = env.host_data[env.host]['dest']
    multicmd = ""
    for dest in destinations:
        cmd = "iperf -c %s " % dest + subcmd
        multicmd = multicmd + cmd + " &"
    
    multicmd = multicmd + " wait" 
    out = run(multicmd)
    return out

def read_configs(infile):
    """ Read the yaml file """
    cfg = {}
    with open(infile) as hdl:
        cfg = yaml.safe_load(hdl)
    return cfg


def args_get():
    parser = argparse.ArgumentParser()
    parser.add_argument("config_file", help="Input yaml file")
    parser.add_argument("--duration", help="duration", type=int, default=30)
    parser.add_argument("--pthreads", help="parallel threads", type=int, default=1)
    argt = parser.parse_args()
    return argt

if __name__ == '__main__':
    argt = args_get()
    configs = read_configs(argt.config_file)
    try:
    	do_test_tcp(argt, configs)
    except Exception, err:                                                      
        print "ERROR: %s" % str(err)
