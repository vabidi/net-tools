#!/bin/python

"""
Collect packet-drop statistics, and optionally, net-stats, from an ESX host
Output is printed to console, and is also written to file '/tmp/vmaperf1.out'

Usage examples:

 1. Collect drop counts
 ./vmaperf.py --swport <switchport>

 2. Collect drop counts and net-stats
 ./vmaperf.py --swport <switchport> --netstats

 3. Collect drop counts and net-stats for 100 seconds, at 4-second intervals
 ./vmaperf.py --swport <switchport> --netstats --tsec 100 --duration 4

  Default is to collect for 300 seconds, at 5-second intervals

 CAUTION: Running this monitoring program does cost CPU cycles and memory.
       Consider the overhead of running it.
       When running with default parameters (as in example #1), the overhead is negligible.
       When running with --netstats, esp with small values of --duration, or with large values of --tsec, overhead can be significant.

Questions and bug reports: please email vabidi@vmware.com
"""
import sys
import os
import time
import subprocess
import argparse
import signal


pc_fname = "/tmp/vmaperf1.out"
ns_fname = "/tmp/ns1.out"
MAX_SECONDS = 300
DFLT_INTERVAL = 5

vmnic_rxd, vmx_rxd, nioc_txd, rxpkts = 0, 0, 0, 0
i = 0
rdrops, rpkts = [], []


def parseArgs(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--tsec", help="time in secs", type=int, default=MAX_SECONDS)
    parser.add_argument("--duration", help="duration in secs", type=int, default=DFLT_INTERVAL)
    parser.add_argument("--swport", help="switchport number", required=True)
    parser.add_argument("--netstats", help="collect net-stats", action="store_true")
    args = parser.parse_args()
    return args


def endit():
    global pcfile
    # compute drop percent
    dp = sum(rdrops) * 100.0 / sum(rpkts)
    line = "Total drops = %d rxpkts = %d Drop Percentage is %.3f" % (sum(rdrops), sum(rpkts), dp)

    print(line)
    pcfile.write(line + "\n---------\n")
    pcfile.close()
    if argt.netstats:
        time.sleep(2)
        pcfile = open(pc_fname, 'a')
        nsfile = open(ns_fname)
        pcfile.write(nsfile.read())
        pcfile.close()
        nsfile.close()

    sys.exit()

def sighandler(frame, signum):
    endit()


def start_netstats(argt):
    ival = argt.duration
    num = argt.tsec/ival
    cmd = "net-stats -A -t WwQqi -i %d -n %d -o %s" % (ival, num, ns_fname)
    print(cmd)
    subprocess.Popen(cmd.split())


def get_kw_value(cli, name):
    res = subprocess.check_output(cli, shell=True)
    res = str(res)
    for line in res.split('\\n'):
        if name in line:
            return int(line.split(':')[-1])

    # I considered return None below, but decided that would increase caller complexity, with questionable benefit
    return 0


argt = parseArgs(sys.argv)
signal.signal(signal.SIGINT, sighandler)
swport = argt.swport
duration = argt.duration

cli1 = "localcli --plugin-dir /usr/lib/vmware/esxcli/int networkinternal nic privstats get -n vmnic0"

cli2 = "vsish -e get /net/portsets/DvsPortset-0/ports/%s/vmxnet3/rxSummary" % swport

cli3 = "vsish -e get /vmkModules/netsched_hclk/devs/vmnic0/qleaves/netsched.pools.vm.%s/info" % swport

cli_line = cli1 + "\n" + cli2 + "\n" + cli3 + "\n"

title = "\nSecs\tvmnic0-rxdrops\tvmxnet3-rxdrops\thclk-txdrops\trxpkts\t%drops\n"
title += "-"*70 + "\n"
pcfile = open(pc_fname, 'w')
pcfile.write(cli_line)
pcfile.write(title)
print(cli_line)
print(title)

# Start net-stats if required
if argt.netstats:
    start_netstats(argt)


while i <= argt.tsec:
    val = get_kw_value(cli1, 'rx_pkts')
    del_rxpkts = (val - rxpkts)
    rxpkts = val

    val = get_kw_value(cli1, 'rx_drops')
    del_vmnic_rxd = (val - vmnic_rxd)
    vmnic_rxd = val

    val = get_kw_value(cli2, 'running out of buffers')
    del_vmx_rxd = (val - vmx_rxd)
    vmx_rxd = val

    val = get_kw_value(cli3, 'pktsDropped')
    del_nioc_txd = (val - nioc_txd)
    nioc_txd = val

    if i > 0:
        drops = del_vmnic_rxd + del_vmx_rxd + del_nioc_txd
        drop_percent = drops * 100.0 / del_rxpkts
        rdrops.append(drops)
        rpkts.append(del_rxpkts)
    else:
        drop_percent = 0.0

    line = "%d \t %d  \t %d  \t %d \t %d \t %.3f\n" % \
            (i, del_vmnic_rxd, del_vmx_rxd, del_nioc_txd, del_rxpkts,
            drop_percent)

    pcfile.write(line)
    print(line)
    i += duration
    time.sleep(duration)
endit()
