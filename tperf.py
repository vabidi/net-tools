
""""
Run performance tests to measure TCP bandwidth.
Uses threading.


Usage example:

 ./tperf.py <config_file> --duration 60 --pthreads 4 --procs 2

Questions and bug reports: please email vabidi@vmware.com
"""

import sys
import os
import argparse
import yaml
import json
import logging
import threading
import json
import subprocess
import pdb

DURATION_DFLT = 60
BASEPORT = 5201


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


def runner(sip, dip, dport, cmd, results):
    print("Start thread %s->%s:%d" % (sip, dip, dport), cmd)
    res = subprocess.check_output(cmd, shell=True)
    results.append(res)


def do_test_tcp(argt, configs):
    sips, dips = [], []
    threads, results, bws = [], [], []
    vm_info = configs['vms']
    streams = configs['streams']
    active_streams = configs['test_info']['active_streams']

    username = configs['constants']['username']
    password = configs['constants']['password']
    password = password.replace("$", r"\$")

    ssh_opt = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o loglevel=quiet"
    
    for sname in active_streams:
        sbval = get_stream_info(streams, sname)
        if not sbval:
            raise ValueError("Unknown stream name %s" % sname)
        tx_vm = sbval['tx_vm']
        rx_vm = sbval['rx_vm']
        sips.append(get_vm_ip(vm_info, tx_vm)[0])
        dips.append(get_vm_ip(vm_info, rx_vm)[1])
    
    for i, sip in enumerate(sips):
        sip = sips[i]
        dip = dips[i]
        sshpass_cmd = "sshpass -p %s ssh %s  %s@%s " % (password, ssh_opt, username, sip)

        for np in range(argt.procs):
            port = BASEPORT+np
            pdict = {"sip": sip, "dip": dip, "duration": argt.duration, "P": argt.pthreads,
                     "port": port}
            remcmd = "iperf3 -c %(dip)s -P %(P)s  -t %(duration)s -p %(port)d --json " % pdict
            cmd = sshpass_cmd + remcmd
            thread = threading.Thread(target=runner, args=(sip, dip, port, cmd, results))
            threads.append(thread)
            thread.start()

    for thread in threads:
        thread.join()

    assert len(threads)==len(results), "Results (%d) and num-threads (%d) mismatch!" % (len(results), len(threads))

    for res in results:
        data = json.loads(res)
        bps = data["end"]["sum_received"]["bits_per_second"]
        mbps = int(float(bps)/(1024**2))
        bws.append(mbps)

    # The word "threads" is bit confusing here.
    # On the runner, we run one python thread for each iperf3 command.
    # Each iperf3 command may run multiple threads.
    nt = len(threads)*argt.pthreads
    print("\nclients=%d threads=%d Total Mbps = %d" % (len(sips), nt, sum(bws)))
    print(" list of BWs" , bws)
    

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
