#!/usr/bin/python

import argparse
import subprocess
from time import sleep
import re
import sys

MYCMD='localcli --plugin-dir /usr/lib/vmware/esxcli/int networkinternal nic privstats get -n vmnic0'

def args_get():
    """ Retrieve script args """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("-c", "--cmd", help="command line", default=MYCMD)
    parser.add_argument("-d", "--delta", type = int, default = 10,
                        help="delta duration in secs")

    args = parser.parse_args()
    return args

def diff_item(t):           
    if t[0].isdigit():
        return str(int(t[1])-int(t[0]))
    else:
        return t[0]

def main():
    args = args_get()
    print("Duration = %d" % args.delta)
    print("Command = " + args.cmd)
                            
    ob = subprocess.check_output(args.cmd, shell=True)
    lines1 = ob.decode('utf-8')
    seq1 = re.split(r'([:\s\n]\s*)', lines1)
    print(lines1)

    sleep(float(args.delta))

    ob = subprocess.check_output(args.cmd, shell=True)
    lines2 = ob.decode('utf-8')
    seq2 = re.split(r'([:\s\n]\s*)', lines2)
    print("After %d seconds, the values are:" % args.delta)
    print(lines2)
                            
    newseq = [diff_item(t) for t in zip(seq1, seq2)]
    print("The diffs of the numerical values are:")
    print(''.join(newseq))


if __name__=="__main__":
    main()


