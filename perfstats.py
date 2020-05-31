#!/bin/python

import sys
import os
import time
import subprocess
import argparse
import signal


outfile = "/tmp/pf1.out"
MAX_ITERATIONS = 100

vmnic_rxd, vmx_rxd, nioc_txd, rxpkts = 0, 0, 0, 0
i = 0
rdrops = []
rpkts = []
duration = 0


def parseArgs(argv):                                                            
    parser = argparse.ArgumentParser()                                          
    parser.add_argument("--duration", help="duration in secs", type=int, default=2)
    parser.add_argument("--swport", help="switchport number")
    args = parser.parse_args()                                                  
    return args     


def endit():
    # compute drop percent 
    dp = sum(rdrops) * 100.0 / sum(rpkts)
    line = "Total rxdrops = %d rxpkts = %d Drop Percentage is %.3f" % (sum(rdrops), sum(rpkts), dp)

    print(line)
    fh.write(line)
    fh.close()
    sys.exit()

def sighandler(frame, signum):
    endit()


argt = parseArgs(sys.argv)
signal.signal(signal.SIGINT, sighandler) 
swport = argt.swport
duration = argt.duration

cli1 = "localcli --plugin-dir /usr/lib/vmware/esxcli/int networkinternal nic privstats get -n vmnic0"

cli2 = "vsish -e get /net/portsets/DvsPortset-0/ports/%s/vmxnet3/rxSummary" % swport

cli3 = "vsish -e get /vmkModules/netsched_hclk/devs/vmnic0/qleaves/netsched.pools.vm.%s/info" % swport

cli_line = cli1 + "\n" + cli2 + "\n" + cli3 + "\n"

title = "Secs\tvmnic0-rxdrops\tvmxnet3-rxdrops\thclk-txdrops\trxpkts\t%drops\n"

fh = open(outfile, 'w')
fh.write(cli_line)
fh.write(title)
print(cli_line)
print(title)

while i <= MAX_ITERATIONS:
    res = subprocess.check_output(cli1, shell=True)
    res = str(res)
    for line in res.split('\\n'):
        if 'rx_pkts' in line:
            val = int(line.split(':')[-1])
            del_rxpkts = (val - rxpkts)
            rxpkts = val
        elif 'rx_drops' in line:
            val = int(line.split(':')[-1])
            del_vmnic_rxd = (val - vmnic_rxd)
            vmnic_rxd = val

    res = subprocess.check_output(cli2, shell=True)
    res = str(res)
    for line in res.split('\\n'):
        if "running out of buffers" in line:
            val = int(line.split(':')[-1])
            del_vmx_rxd = (val - vmx_rxd)
            vmx_rxd = val
            break

    res = subprocess.check_output(cli3, shell=True)
    res = str(res)
    for line in res.split('\\n'):
        if 'pktsDropped' in line:
            val = int(line.split(':')[-1])
            del_nioc_txd = (val - nioc_txd)
            nioc_txd = val
            break
    
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

    fh.write(line)
    print(line)
    i += duration
    time.sleep(duration)
endit()

