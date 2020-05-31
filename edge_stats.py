#!/bin/python

"""
Collect traffic stats from Edge

Usage: First, need to collect the SDDC keys, and set up ssh aliases.           
       cd files; ./get_sddc_info.sh <sddc-name> 

Questions and bug reports: please email vabidi@vmware.com
"""
import sys
import os
import time
import subprocess
import argparse
import signal
import json
import pdb

MAX_SECONDS = 300
DFLT_INTERVAL = 5

rxpkts, rxbytes, txpkts, txbytes, txdrops = 0, 0, 0, 0
i = 0
tdrops, tpkts = [], []


def parseArgs(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--tsec", help="time in secs", type=int, default=MAX_SECONDS)
    parser.add_argument("--duration", help="duration in secs", type=int, default=DFLT_INTERVAL)
    args = parser.parse_args()
    return args


def endit():
    # compute drop percent
    dp = sum(tdrops) * 100.0 / sum(tpkts)
    line = "Total drops = %d txpkts = %d Drop Percentage is %.3f" % (sum(tdrops), sum(tpkts), dp)

    print(line)

    sys.exit()

def sighandler(frame, signum):
    endit()

def get_ssh_cmd(target):
    with open("files/sddc_cmds") as hdl:
        lines = hdl.readlines()
    for line in lines:
        lsp = line.strip().split('==')
        if len(lsp) > 1 and lsp[0] == target:
            return lsp[1]
    return None


argt = parseArgs(sys.argv)
signal.signal(signal.SIGINT, sighandler)
duration = argt.duration

cmd1 = " /usr/local/bin/edge-appctl -t /var/run/vmware/edge/dpd.ctl "
cli = cmd1 + " physical_port/show fp-eth0 stats"

edge_ssh = get_ssh_cmd("edge0")
cmd = edge_ssh + cli

title = "\nSecs\trxpkts\trxbytes\ttxpkts\ttxbytes\ttxdrops\t%drops\n"
title += "-"*70 + "\n"
print(cli)
print(title)


while i <= argt.tsec:
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
    resj = json.loads(result)
    rxpkts1  = int(resj['rx_packets'])
    rxbytes1 = int(resj['rx_bytes'])
    txpkts1  = int(resj['tx_packets'])
    txbytes1 = int(resj['tx_bytes'])
    txdrops1 = int(resj['tx_drops'])

    del_rxpkts = (rxpkts1 - rxpkts)
    rxpkts = rxpkts1
    del_rxbytes = (rxbytes1 - rxbytes)
    rxbytes = rxbytes1
    del_txpkts = (txpkts1 - txpkts)
    txpkts = txpkts1
    del_txbytes = (txbytes1 - txbytes)
    tx_bytes = tx_bytes1
    del_txdrops = (txdrops1 - txdrops)
    txdrops = txdrops1

    if i > 0:
        drop_percent = del_txdrops * 100.0 / del_txpkts
        tdrops.append(del_txdrops)
        tpkts.append(del_txpkts)
    else:
        drop_percent = 0.0

    line = "%d \t %d  \t %d  \t %d \t %d \t %d \t %.3f\n" % \
            (i, del_rxpkts, del_rxbytes, del_txpkts, del_txbytes, del_txdrops,
            drop_percent)

    print(line)
    i += duration
    time.sleep(duration)
endit()
