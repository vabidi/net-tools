#!/usr/bin/python

"""
Given two files which contain performance statistics, find the difference.
This is useful when you have two snapshots, and want to compute the delta values
"""

"""
Example: 
"""

import re
import sys

def diff_item(t):
    if t[0].isdigit():
        return str(int(t[1])-int(t[0]))
    else:
        return t[0]

def main():
    [f1, f2] = sys.argv[1:]
    with open(f1, 'r') as hdl:
        lines1 = hdl.readlines()
    with open(f2, 'r') as hdl:
        lines2 = hdl.readlines()

    for l1, l2 in zip(lines1, lines2):
         
        seq1 = re.split(r'([:\s\n]\s*)', l1)
        seq2 = re.split(r'([:\s\n]\s*)', l2)
        newseq = [diff_item(t) for t in zip(seq1, seq2)]
        print ''.join(newseq)


if __name__=="__main__":
    main()

