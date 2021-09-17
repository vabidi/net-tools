#!/usr/bin/python

""""
Run performance tests to measure TCP bandwidth.
Output is printed to console.

Usage example:

 ./ifabtest.py <config_file> --duration 60 --pthreads 4

Questions and bug reports: please email vabidi@vmware.com
"""

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

DURATION_DFLT = 60
BASEPORT = 5201

def fabric_env(env, configs):
    env.user = configs['constants']['username']
    env.password = configs['constants']['password']
    env.host_data = dict()
    return env

def get_vm_ip(vm_info, name):
    ''' VM may have a single port, or two ports - a mgmt port and a data port'''
    mgmt_ip, data_ip = None, None
    for vmm in vm_info:
	for k, val in vmm.items():
		if k == name:
			if 'port_ip' in val:
				mgmt_ip = val['port_ip']
				data_ip = val['port_ip']
			else:	
				mgmt_ip = val['mgmt_ip']
				data_ip = val['data_ip']
			return (mgmt_ip, data_ip)	
    return (mgmt_ip, data_ip)


def get_stream_info(streams, sname):
    for stm in streams:
	for k, val in stm.items():
		if k == sname:
			return val
    return None


def parse_mbps(bwstr, unitstr):
    bw = float(bwstr)
    if unitstr == 'Gbits/sec':
        mbps = int(bw*1000)
    elif unitstr == 'Mbits/sec':
        mbps = int(bw)
    else:
        raise ValueError("Bad unit string %s" % unitstr)
    return mbps

def iparse_tcp_res(result):
    tot_mbps, tot_sum = 0, 0
    ns, nt = 0, 0
    for value in result.values():
        ns += 1
        lines = [line.strip() for line in value.split('\n')]
        liter = iter(lines)
        for line in liter:
       	    if "sender" in line:
                line = line.split()
                if len(line) > 1:
                    if line[0] == '[SUM]':
                        mbps = parse_mbps(line[-4], line[-3])
                        tot_sum += mbps
                    else:
                        mbps = parse_mbps(line[-4], line[-3])
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
    streams = configs['streams']
    active_streams = configs['test_info']['active_streams']

    for sname in active_streams:
        sbval = get_stream_info(streams, sname)
	if not sbval:
		raise ValueError("Unknown stream name %s" % sname)
        tx_vm = sbval['tx_vm']
        rx_vm = sbval['rx_vm']
        sips.append(get_vm_ip(vm_info, tx_vm)[0])
        dips.append(get_vm_ip(vm_info, rx_vm)[1])
    
    env = fabric_env(env, configs)
    env.hosts = sips
    for i, sip in enumerate(sips):
        env.host_data[sip] = {'dest': dips[i], 'duration': argt.duration, 
                              'P': argt.pthreads, 'procs': argt.procs}
    res = execute(test_tcp)
    ns, nt, mbps = iparse_tcp_res(res)
    print "clients=%d threads=%d Total Mbps = %d" % (ns, nt, mbps)


@parallel
def test_tcp():
    nprocs = env.host_data[env.host]['procs']
    cmdf = " -P %(P)s -i 30 -t %(duration)s "
    subcmd = cmdf % env.host_data[env.host]
    destinations = env.host_data[env.host]['dest']
    multicmd = ""
    for i in xrange(nprocs):
	port = BASEPORT+i
    	cmd = "iperf3 -c %s -p %d" % (destinations, port) + subcmd
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
    parser.add_argument("--duration", help="duration", type=int, default=DURATION_DFLT)
    parser.add_argument("--pthreads", help="parallel threads", type=int, default=1)
    parser.add_argument("--procs", help="number of processes", type=int, default=1)
    argt = parser.parse_args()
    return argt

if __name__ == '__main__':
    argt = args_get()
    configs = read_configs(argt.config_file)

    do_test_tcp(argt, configs)
