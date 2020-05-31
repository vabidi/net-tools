#!/usr/bin/python

"""
 Read specified counters from vsish and find their differential values over 
 specified interval. 
 User can specify multiple vsish commands, and choose one or more counters from each
 output.

 NOTE: the swport value is hardcoded. REMEMBER TO SET IT CORRECTLY!
    'net-stats -l | grep NSX-Edge-0.eth1'

 Also, collects output from net-stats, and parses it to print out errors.
 Start net-stats and saves output to a file. Then parses the file after interval.
 Thus, the delta counts and net-stats are collected over the same interval.
 
"""

import argparse
import subprocess
from time import sleep
import re
import sys
import json

swport = 100663340

cli1 = "localcli --plugin-dir /usr/lib/vmware/esxcli/int networkinternal nic privstats get -n vmnic0"

cli2 = "vsish -e get /net/portsets/DvsPortset-0/ports/%s/vmxnet3/rxSummary" % swport

cli3 = "vsish -e get /net/portsets/DvsPortset-0/ports/%s/stats" % swport

cli4 = "vsish -e get /net/portsets/DvsPortset-0/ports/%s/inputStats" % swport

cli5 = "vsish -e get /net/portsets/DvsPortset-0/ports/%s/clientStats" % swport


# Enter the CLI commands and tokens here. 
# List of tuples. Each tuple is (<cli str>, [<token1>, <token2>, ...])
#
clis = [(cli1, ['rx_pkts', 'rx_drops']),
        
        (cli2, ['running out of buffers']),

        (cli3, ['droppedTx', 'droppedRx']),

        (cli4, ['pktsDropped']),

        (cli5, ['droppedTx', 'droppedRx'])
       ]


def args_get():
    """ Retrieve script args """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("-d", "--delta", type = int, default = 10,
                        help="delta duration in secs")

    args = parser.parse_args()
    return args

def diff_item(t):
    if t[0].isdigit():
        return str(int(t[1])-int(t[0]))
    else:
        return t[0]

def do_vsish(args):
    print("Duration = %d" % args.delta)

    seqs1, seqs2, newseqs = [], [], []

    for i, tup in enumerate(clis):
        cli = tup[0]
        print("Command = " + cli)
        ob = subprocess.check_output(cli, shell=True)
        lines1 = ob.decode('utf-8')
        ls1 = re.split(r'([:\s\n]\s*)', lines1)
        seqs1.append(ls1)


    sleep(float(args.delta))

    for i, tup in enumerate(clis):
        cli = tup[0]
        ob = subprocess.check_output(cli, shell=True)
        lines2 = ob.decode('utf-8')
        ls2 = re.split(r'([:\s\n]\s*)', lines2)
        seqs2.append(ls2)

    for i, tup in enumerate(clis):
        ls1 = seqs1[i]
        ls2 = seqs2[i]
        diff = [diff_item(t) for t in zip(ls1, ls2)]
        newseqs.append(diff)

    for i, tup in enumerate(clis):
        cli, stats = tup
        print(cli)
        newseq = newseqs[i]
        nls = ''.join(newseq)
        tks = [x.strip() for x in nls.split('\n')]
        for tkv in tks:
            tkn = tkv.split(':')
            if tkn[0] in stats:
                tval = tkn[1]
                print("%s   %s" % (tkn[0], tval))

vmnicd = {}
edged = {}

def _decode_dict(ad):
    global vmnicd, edged
    try:
        name = ad['name']
   
        if name == "vmnic0":
            vmnicd = ad
        elif name.startswith('NSX-Edge') and name.endswith('eth1'):
            edged = ad
        else: pass
    except KeyError: pass
    return ad


def get_value(dic, key):
    val = int(dic[key])
    return val


def start_netstats(args):
    cmd = "net-stats -A -t WwQqi -i %s -o /tmp/ns1.out" % args.delta
    print(cmd)
    subprocess.Popen(cmd.split())

def do_netstats(args):
    with open('/tmp/ns1.out') as datafile:
        data = json.load(datafile, object_hook=_decode_dict)
   
    # examine vmnicd
    txpps = get_value(vmnicd, "txpps")
    rxpps = get_value(vmnicd, "rxpps")
    txeps = get_value(vmnicd, "txeps")
    # rxeps is reported in two places. 
    rxeps1 = get_value(vmnicd, "rxeps")
    rxeps2 = get_value(vmnicd["vmnic"], "rxeps")
    # print totalpps only if both rxpps and txpps are non-zero
    totalpps = (txpps+rxpps) if txpps and rxpps else 0
    vmnicst = "vmnic0: "
    if txpps:
        vmnicst = vmnicst + "txpps: %d " % txpps
    if rxpps:
        vmnicst = vmnicst + "rxpps: %d " % rxpps
    if txeps:
        vmnicst = vmnicst + "txeps: %d " % txeps
    if rxeps1:
        vmnicst = vmnicst + "rxeps: %d " % rxeps1
    if rxeps2:
        vmnicst = vmnicst + "rxeps: %d " % rxeps2

    if totalpps:
        vmnicst = vmnicst + "totalpps: %d " % totalpps
    
    print(vmnicst)
    print()

    # examine Edge statistics
    if edged:
        txeps = get_value(edged, "txeps")
        # rxeps is reported in two places. 
        rxeps1 = get_value(edged, "rxeps")
        rxeps2 = get_value(edged["vnic"], "rxeps")
        rxeps = max(rxeps1, rxeps2)
        edgest = "Edge: "
        if txeps:
            edgest = edgest + "txeps: %d " % txeps
        if rxeps:
            edgest = edgest + "rxeps: %d " % rxeps
    
        print(edgest)
        print()

if __name__=="__main__":
    args = args_get()
    start_netstats(args)
    do_vsish(args)
    sleep(1) # wait before reading the net-stats output file
    do_netstats(args)

