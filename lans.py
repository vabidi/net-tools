#!/usr/bin/python

"""
 Extract interesting information from net-stats outpiut.

 Usage:
   ./lans.py netstatsresult.json

   You can operate on a bunch of files, like this:
    find . -name "netstatsresult.json" | xargs -n1 ./lans.py

"""



import sys
import json
from colorama import Fore, Style

HI_THRESH = 90.00

thresholds = {"txpps": 1000, "rxpps": 1000, "txeps": 0, "rxeps": 0, 
        "used": 10, "run": 10}

vdic = {}
vmnicd = {}
edged = {}
pollworldd = {}
networldd = {}

def _decode_dict(ad):
    global vdic, vmnicd, edged, pollworldd, networldd
    try:
        name = ad['name']
   
        if name.startswith('vmx-vcpu'):
            name = name[len('vmx-'):]
            vdic[name] = ad['used']
        elif name == "vmnic0":
            vmnicd = ad
        elif name.startswith('NSX-Edge') and name.endswith('eth1'):
            edged = ad
        elif name.startswith('vmnic0-pollWorld'):
            name = name[len('vmnic0-pollWorld'):]
            pollworldd[name] = ad['run']
        elif name.startswith('NetWorld-'):
            name = name[len('NetWorld-'):]
            networldd[name] = ad['used']
        else: pass
    except KeyError: pass
    return ad

def is_large(key, val):
    return val > thresholds[key]

def get_value(dic, key, thresh_key = None):
    if not thresh_key:
        thresh_key = key
    val = int(dic[key])
    return val if is_large(thresh_key, val) else 0

def main():
    [filename] = sys.argv[1:]
    with open(filename) as data_file:
        data = json.load(data_file, object_hook=_decode_dict)

    pcpu = data['stats'][0]['cpu']['used']
    print "File: ", filename
    print
    print "pcpu: ", pcpu
    print
    vl = []
    vsum = 0.0
    for k,v in vdic.items():
        if v > 1.00:
            vl.append(k)
            if (v > HI_THRESH):
                vstr = Fore.RED + str(v) + Style.RESET_ALL
            else:
                vstr = str(v)
            vl.append(vstr)
            vsum = vsum + v
    
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
    
    print vmnicst
    print

    ulstats = vmnicd["txqueue"]["uplink_stats"]
    print "Txqueues"
    for item in ulstats:
        if item["pps"] > 0: 
            print item
    print         
    
    # examine Edge statistics
    if edged:
        txpps = get_value(edged, "txpps")
        rxpps = get_value(edged, "rxpps")
        txeps = get_value(edged, "txeps")
        # rxeps is reported in two places. 
        rxeps1 = get_value(edged, "rxeps")
        rxeps2 = get_value(edged["vnic"], "rxeps")
        rxeps = max(rxeps1, rxeps2)
        edgest = "Edge: "
        if txpps:
            edgest = edgest + "txpps: %d " % txpps
        if rxpps:
            edgest = edgest + "rxpps: %d " % rxpps
        if txeps:
            edgest = edgest + "txeps: %d " % txeps
        if rxeps:
            edgest = edgest + "rxeps: %d " % rxeps
    
        print edgest
        print

    # examine pollworldd
    for k, v in pollworldd.items():
        val = get_value(pollworldd, k, 'run')
        if val:
            print "pollWorld %s run%% = %d" % (k, val)
    print

    # examine networldd
    for k, v in networldd.items():
        val = get_value(networldd, k, 'used')
        if val:
            print "NetWorld %s used%% = %d" % (k, val)
    print


    print "vCPUs"
    print " ".join(vl)
    print "-"*40

if __name__ == "__main__":
     main()
