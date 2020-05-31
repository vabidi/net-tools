#!/usr/bin/python3.6



import sys
import os
import argparse
import time
from multiprocessing import Pool, TimeoutError
import signal

pool = None
TIME_MSEC = 1.0/1000.0

def compute():
    """ Do some floating-point op to spend cpu cycles """
    _ = 5339.167 * 17.82

def loadcpu(argt):
    nrep = argt.load * 1000
    duration = argt.duration
    start = time.clock()
    while (time.clock() - start) < duration:
        for _ in range(nrep):
            compute()
        time.sleep(TIME_MSEC)


def do_load(argt):
    global pool
    pool = Pool(processes=argt.procs)
    mres = [pool.apply_async(loadcpu, (argt,)) for i in range(argt.procs)]
    try:
        print([res.get(timeout=argt.duration+1) for res in mres])
    except TimeoutError:
        print("---- Timed out after %d seconds ----" % argt.duration)

def parseArgs(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", help="duration in secs", type=int, default=60)
    parser.add_argument("--load", help="percent load (approx)", type=int, default=50)
    parser.add_argument("--procs", help="num processes", type=int, default=1)
    args = parser.parse_args()
    return args

def sighandler(signum, frame):
    #global pool
    #pool.close()
    #pool.terminate()
    #pool.join()
    # The sys.exit call works to cleanup child processes.

    sys.exit()


if __name__ == '__main__':
    argt = parseArgs(sys.argv)

    signal.signal(signal.SIGINT, sighandler)

    do_load(argt)
