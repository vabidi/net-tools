#!/usr/bin/python

"""
Examine net-stats for drops and errors

 Usage:
   ./ns_drops.py


"""



import sys
import json
import subprocess


vmnicd = {}
edged = {}

def _decode_dict(ad):
    global vdic, vmnicd, edged, pollworldd, networldd
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

def main():
    cmd = "net-stats -A -t WwQqi -i 2"
    ob = subprocess.check_output(cmd, shell=True)
    import pdb; pdb.set_trace()
    data = json.load(data_file, object_hook=_decode_dict)

   
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

    print         
    
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
    
        print edgest
        print

if __name__ == "__main__":
     main()
