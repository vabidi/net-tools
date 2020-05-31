#!/bin/python

import sys
import os
import time
import subprocess
import argparse
import signal

def parseArgs(argv):                                                            
        parser = argparse.ArgumentParser()                                          
        parser.add_argument("--duration", help="duration in secs", type=int, default=2)
        args = parser.parse_args()                                                  
        return args     

rxdrops, txp, rxp = 0, 0, 0
rxdrops_t0, txp_t0, rxp_t0 = 0, 0, 0
rxd, txpps, rxpps = 0, 0, 0
first_time = True
start_time = int(time.time())

cmd = "localcli --plugin-dir /usr/lib/vmware/esxcli/int networkinternal nic privstats get -n vmnic0"


def sighandler(frame, signum):
    global txp_t0, rxp_t0, rxdrops_t0
    global txp, rxp, rxdrops
    global start_time
    dur = int(time.time()) - start_time
    del_rxp = rxp - rxp_t0
    del_rxdrops = rxdrops - rxdrops_t0
    print("\nDuration=%ds  rxdrops=%d  rxtotal=%d\n" % (dur, del_rxdrops, del_rxp))
    sys.exit()


argt = parseArgs(sys.argv)
signal.signal(signal.SIGINT, sighandler) 

print("Delta values every %d seconds from command: %s" % (argt.duration, cmd))

while True:
    res = subprocess.check_output(cmd, shell=True)
    res = str(res)
    for line in res.split('\\n'):
        if 'tx_pkts' in line:
            val = int(line.split(':')[-1])
            delta = (val - txp)
            txp = val
            txpps = delta/argt.duration
        elif 'rx_pkts' in line:
            val = int(line.split(':')[-1])
            delta = (val - rxp)
            rxp = val
            rxpps = delta/argt.duration
        elif 'rx_drops' in line:
            val = int(line.split(':')[-1])
            delta = (val - rxdrops)
            rxdrops = val
            rxd = delta
        else:
            continue
    if (first_time):
        rxdrops_t0 = rxdrops
        txp_t0 = txp
        rxp_t0 = rxp
        print(" Values at first read:  tx_pkts = %d rx_pkts = %d rx_drops = %d" % (txp_t0, rxp_t0, rxdrops_t0))
        first_time = False
    else:
        print("txpps = %d rxpps = %d rxdrops = %d" % (txpps, rxpps, rxd))
    time.sleep(argt.duration)

