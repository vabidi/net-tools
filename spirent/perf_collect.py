#!/usr/bin/python2.7
"""
 Do collections from remote hosts

 Prerequisites: 
    1. collect the SDDC keys, and set up ssh aliases.
        cd files; ./get_sddc_info.sh <sddc-name>
        This will create ./files/sddc_cmds
    2. mkdir /vmkstatsdir  on esx hosts
    3. copy scripts to esx hosts: 
        /tools/get_ena_stats.py, /tools/vmkstats.sh
"""

import argparse
import os
import sys
import time
import datetime
import json
import subprocess
import pdb


def args_get():
    """ Retrieve scripts args """
    parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument("--tag", help="tagname", default="hello, world")
    args = parser.parse_args()
    return args

def output_prepare(info):
    """ Make a directory, if needed """
    now = datetime.datetime.now()
    fpn = now.strftime("%Y/%m/%d/%H.%M.%S")
    rdir = os.path.join("./output", fpn)
    try:
        os.makedirs(rdir)
    except OSError:
        pass
    fname = os.path.join(rdir, "about.txt")
    with open(fname, mode='w') as hdl:
        hdl.write(info)

    return rdir


def get_ssh_cmd(target):
    with open("files/sddc_cmds") as hdl:
        lines = hdl.readlines()
    for line in lines:
        lsp = line.strip().split('==')
        if len(lsp) > 1 and lsp[0] == target:
            return lsp[1]
    return None


def make_dir(rdir, sdir):
    newdir = os.path.join(rdir, sdir)
    try:
        os.makedirs(newdir)
    except OSError:
        pass
    return newdir

def parse_edge_portstats(psj1, psj2):
    """ Compute delta value from the given json strings """

    ps1 = json.loads(psj1)
    ps2 = json.loads(psj2)
    txpkts = int(ps2['tx_packets']) - int(ps1['tx_packets'])
    txdrops = int(ps2['tx_drops']) - int(ps1['tx_drops'])
    drop_percent = txdrops * 100.0 / txpkts
    return drop_percent

def print_edge_cpustats_summary(cpu_stats):
    """ Extract values from the given json string"""
    res = json.loads(cpu_stats)
    for cp in res:
        # Code below is for this format  <num>: <txKpps>, <percent>%
        line = ""
        for k, v in cp.items():
            if k == "core":
                line += v + ': '
            elif k == "tx":
                line += str(int(v.split()[0])/1000) + ', '
            elif k == "usage":
                line += v
        print line

def parse_netstats(fname):
    vmnicd = {}
    def _decode_dict(ad):
        try:
            name = ad["name"]
            if name == "vmnic0":
                vmnicd.update(ad)
        except KeyError:pass
        return ad

    def get_value(dic, key):
        return int(dic[key])

    with open(fname) as hdl:
        data = json.load(hdl, object_hook=_decode_dict)
    txpps = get_value(vmnicd, "txpps")
    txeps = get_value(vmnicd, "txeps")
    rxpps = get_value(vmnicd, "rxpps")
    totalpps = (txpps+rxpps)
    txdp = txeps*100.0/txpps
    return (totalpps, txdp)


def do_collections_EW(rdir):
    """ collect performance metrics from hosts 
        User must ensure that file 'sddc_cmds' has the correct commands to ssh
    """
    esx0_ssh = get_ssh_cmd("esx0")
    esx2_ssh = get_ssh_cmd("esx2")
    scpr2 = get_ssh_cmd("scpr2")

    netstats_cmd = " net-stats -A -t WwQqi -i 10"

    #net-stats from esx1
    cmd = esx0_ssh + netstats_cmd
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
    rdir0 = make_dir(rdir, "esx0")
    fnetstats0 = os.path.join(rdir0, "ns.out")
    with open(fnetstats0, mode='w') as hdl:
        hdl.write(result)

    #net-stats from esx2
    cmd = esx2_ssh + netstats_cmd
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
    rdir2 = make_dir(rdir, "esx2")
    fnetstats2 = os.path.join(rdir2, "ns.out")
    with open(fnetstats2, mode='w') as hdl:
        hdl.write(result)

    # collect ena stats from esx2
    ena_cmd = " /tools/get_ena_stats.py -d 5"
    cmd = esx2_ssh + ena_cmd
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
    fname = os.path.join(rdir2, "enastats.out")
    with open(fname, mode='w') as hdl:
        hdl.write(result)

    # collect vmkstats on esx2, copy it over
    vmkst_cmd = " /tools/vmkstats.sh"
    cmd = esx2_ssh + vmkst_cmd
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
    cmd = scpr2 + " " + rdir2
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')

    # Parse net-stats output to get hclk drops
    totalpps, hclk_txdp = parse_netstats(fnetstats0)
    print "esx0 totalpps = %d hclk drop percent = %.3f" % (totalpps, hclk_txdp)
    totalpps, hclk_txdp = parse_netstats(fnetstats2)
    print "esx2 totalpps = %d hclk drop percent = %.3f" % (totalpps, hclk_txdp)


def do_collections_NS(rdir):
    """ collect performance metrics from hosts 
        User must ensure that file 'sddc_cmds' has the correct commands to ssh
    """
    esx1_ssh = get_ssh_cmd("esx1")
    esx2_ssh = get_ssh_cmd("esx2")
    edge1_ssh = get_ssh_cmd("edge1")
    scpr1 = get_ssh_cmd("scpr1")

    netstats_cmd = " net-stats -A -t WwQqi -i 10"

    #net-stats from esx1
    cmd = esx1_ssh + netstats_cmd
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
    rdir1 = make_dir(rdir, "esx1")
    fnetstats1 = os.path.join(rdir1, "ns.out")
    with open(fnetstats1, mode='w') as hdl:
        hdl.write(result)

    #net-stats from esx2
    cmd = esx2_ssh + netstats_cmd
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
    rdir2 = make_dir(rdir, "esx2")
    fnetstats2 = os.path.join(rdir2, "ns.out")
    with open(fnetstats2, mode='w') as hdl:
        hdl.write(result)

    # collect ena stats from esx1
    ena_cmd = " /tools/get_ena_stats.py -d 10"
    cmd = esx1_ssh + ena_cmd
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
    fname = os.path.join(rdir1, "enastats.out")
    with open(fname, mode='w') as hdl:
        hdl.write(result)

    #collect metrics from Edge
    cmd_pfx = " /usr/local/bin/edge-appctl -t /var/run/vmware/edge/dpd.ctl "
    cpu_cmd = cmd_pfx + " cpuusage/show"
    cmd = edge1_ssh + cpu_cmd
    cpu_stats = subprocess.check_output(cmd, shell=True).decode('utf-8')
    portstats_cmd = cmd_pfx + " physical_port/show fp-eth0 stats"
    cmd = edge1_ssh + portstats_cmd
    port_stats1 = subprocess.check_output(cmd, shell=True).decode('utf-8')
    time.sleep(10)
    port_stats2 = subprocess.check_output(cmd, shell=True).decode('utf-8')
    tx_drop_percent = parse_edge_portstats(port_stats1, port_stats2)
    txdp_line = "Edge Tx Drop percent = %.3f" % tx_drop_percent
    rdire = make_dir(rdir, "edge1")
    fname = os.path.join(rdire, "cpuusage.json")
    with open(fname, mode='w') as hdl:
        hdl.write(cpu_stats)
        hdl.write(txdp_line)
    
    # collect vmkstats on esx1, copy it over
    vmkst_cmd = " /tools/vmkstats.sh"
    cmd = esx1_ssh + vmkst_cmd
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
    cmd = scpr1 + " " + rdir1
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')

    #
    # Parse Edge stats to print info which I want
    print_edge_cpustats_summary(cpu_stats)
    print txdp_line
    # Parse net-stats output to get hclk drops
    totalpps, hclk_txdp = parse_netstats(fnetstats1)
    print "esx1 totalpps = %d hclk drop percent = %.3f" % (totalpps, hclk_txdp)
    totalpps, hclk_txdp = parse_netstats(fnetstats2)
    print "esx2 totalpps = %d hclk drop percent = %.3f" % (totalpps, hclk_txdp)


def perf_collect(tagname):
    """ Entry point for function call """
    rdir = output_prepare(tagname)
    if "NS" in tagname or "SN" in tagname:
        do_collections_NS(rdir)
    elif "EW" in tagname:
        do_collections_EW(rdir)
    else:
        print "Nothing to collect for this testname: %s" % tagname
    print "Results dir: %s" % rdir
    return rdir

def main():
    """ Entry point for main program """
    argt = args_get()
    perf_collect(argt.tag)

if __name__ == "__main__":
    try:
        main()
    except Exception, err: 
        print "ERROR: %s" % str(err)
########

