#!/usr/bin/python

import sys
import json

time = ""
iteration = ""


def _decode_dict(ad):
    global time
    global iteration
    try:
        time = ad['time']
        iteration = ad['iteration']
    except KeyError: pass
    try:
        name = ad['name']
   
        if name == "vmnic0":
            rxeps = int(ad["vmnic"]["rxeps"])
            if rxeps > 0:
                print("time=%s iteration=%s rxeps = %d" % (time, iteration, rxeps))
        else: pass
    except KeyError: pass
    return ad

def main():
    [filename] = sys.argv[1:]
    with open(filename) as data_file:
        data = json.load(data_file, object_hook=_decode_dict)


if __name__ == "__main__":
     main()

