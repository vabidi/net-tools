"""
 Run traffic using STC (Spirent Test Center)

"""

from operator import itemgetter
import argparse
import yaml
import logging
import os
import sys
import time
import datetime
import json
import signal
import subprocess
from collections import  defaultdict
import pdb

from vmware.spark.operations.spirent_operations import SpirentInt
import perf_collect

#import vmware.spark.common.logger as logger
#log = logger.setup_logging(__name__)


DURATION = 30
DROP_THRESH = 100.0
WTO = 300 # Port Generator Timeout, secs

def args_get():
    """ Retrieve scripts args """
    parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument("config_file", help="Input yaml file")
    parser.add_argument("--verbose", help="Verbose output", action="store_true")
    args = parser.parse_args()
    return args


def read_configs(infile):
    """ Read the yaml file """
    cfg = {}
    with open(infile) as hdl:
        cfg = yaml.safe_load(hdl)
    return cfg

def get_vm_data():
    """ For debugging """
    vmd = {'stc2': {'ips': ['10.98.80.241', '10.99.1.209'],'gw': '10.99.1.1'},
           'stc1': {'ips': ['10.98.80.199',  '10.99.1.89'],'gw': '10.99.1.1'}}
    vmd1 = {'stc1': {'ips': ['192.168.20.2', '192.168.50.2'],'gw': '192.168.50.1'},
            'stc2': {'ips': ['192.168.20.3', '192.168.50.3'],'gw': '192.168.50.1'}}
    return vmd

def convert_vm_data(stcv_vms):
    """ Convert to the format which  spirent_operations wants """
    vmd = {}
    for item in stcv_vms:
        vm_name = item.keys()[0]
        vald = item.values()[0]
        ips = [vald['mgmt_ip'], vald['data_ip']]
        vcd = {'ips': ips, 'gw': vald['gw_ip']}
        vmd[vm_name] = vcd
    return vmd

def create_streamblocks(sd, streamd):
    """ Create streamblocks with default parameter values:
          framelen=64, nflows=1
        use modify_streamblocks() to modify the parameter values
    """
    for sb_name, val in streamd.iteritems():
        tx_vm, rx_vms = itemgetter('tx_vm', 'rx_vms')(val)
        tx_port = sd.get_ports(tx_vm)[0]
        tx_dev = sd.port_emulated_dev[tx_port]
        tx_if = sd.stc.get(tx_dev, 'children-Ipv4If')
        
        for rx_vm in rx_vms:
            rx_port = sd.get_ports(rx_vm)[0]
            rx_dev = sd.port_emulated_dev[rx_port]

            rx_if = sd.stc.get(rx_dev, 'children-Ipv4If')

            attr = {'Name': sb_name, 'under': tx_port,
                    'srcbinding-targets': tx_if, 'dstbinding-targets': rx_if,
                    'ExpectedRxPort': rx_port,
                    'FixedFrameLength': 64
                    }

            sblk = sd.stc.create('streamblock', **attr)
            sd.streamblocks.append(sblk)
            sd.port_sblks[tx_port].append(sblk)

            # Add UDP header and rangemodifier
            udp = sd.stc.create('udp:Udp', under=sblk, name='udp')
            attr = {'under': sblk, 'RecycleCount': '1',
                'OffsetReference': 'udp.sourcePort', 'Data': '1024', 'Mask': '65535',
                'EnableStream': 'True'}
            sd.stc.create('RangeModifier', **attr)

def delete_streamblocks(sd):
    for sblk in sd.streamblocks:
        sd.stc.delete(sblk)
    sd.streamblocks = []
    sd.port_sblks = defaultdict(list)


def config_port_generators(sd, load, duration):
    for port in sd.ports:
        # we only need look at tx_ports
        if port not in sd.port_sblks:
            continue
        attr = {'LoadMode': 'FIXED', 'FixedLoad': load*1000, 
                'LoadUnit': 'FRAMES_PER_SECOND',
                'DurationMode': 'SECONDS', 'Duration': duration}
        gen_obj = sd.stc.get(port + '.Generator')['children']
        sd.stc.config(gen_obj, **attr)


def modify_streamblocks(sd, framelen, num_flows):
    for sblk in sd.streamblocks:
        sd.stc.config(sblk, FixedFrameLength=framelen)
        sbc = sd.stc.get(sblk)['children']
        rms = [item for item in sbc.split() if item.startswith('rangemodifier')]
        if len(rms) > 0 :
            rangemodifier = rms[0]
            sd.stc.config(rangemodifier, RecycleCount = str(num_flows))
        else:
            print "ERROR: Did not find RangeModifier in %s" % sblk


def process_results(results, secs):
    n, tot_rxpps, tot_drops, tot_dpc = 0, 0, 0, 0
    for sb, res in results.iteritems():
        rxpps = int(res['rx'])/secs
        drops = int(res['Dropped'])
        dpc = float(res['dpc'])
        print "  %s rxpps=%d drops=%d drop-percent %.3f" % (sb, rxpps, drops, dpc)
        tot_rxpps += rxpps
        tot_drops += drops
        tot_dpc += dpc
        n += 1
    if n > 1:
        print "  %s" % "-"*10
        print "   Avg rxpps=%d drops=%d drop-percent %.3f" % (tot_rxpps/n, tot_drops/n, tot_dpc/n)
    print
    return {"rxpps": tot_rxpps/n, "drop_percent": tot_dpc/n}


def sighandler(frame, signum):
    global sd
    print "Received signal %s" % signum
    sd.stc.perform("DetachPortsCommand")
    sd.disconnect_all_chasis()
    sd.terminate_session()


def save_results(rdir, result):
    fname = os.path.join(rdir, "stc_results.out")
    with open(fname, mode='w') as hdl:
        hdl.write(json.dumps(result))
    return result

def main():
    global sd
    signal.signal(signal.SIGINT, sighandler)
    argt = args_get()
    configs = read_configs(argt.config_file)
    license_server = configs['constants']['license_server']
    lab_server = configs['constants']['lab_server']
    duration = configs['constants']['duration']
    nreps = configs['constants']['iterations']
    stcv_vms = configs['stcv_vms']
    stcv_vms = convert_vm_data(stcv_vms)
    print stcv_vms
    test_list = configs['test_list']
    print test_list
    print "creating session ..."
    sd = SpirentInt(license_server, lab_server)

    print "creating ports ..."
    sd.create_ports(stcv_vms)

    print "attaching ports..."
    sd.attach_ports()

    print "creating emulated devices..."
    sd.create_emulated_device()
    sd.stc.perform('L2LearningStartcommand')
    sd.stc.perform('Arpndstart')
    sd.subscribe_results()

    for test in test_list:
        delete_streamblocks(sd) # cleanup streamblocks from previous test
        test_name = test.keys()[0]
        test_params = test.values()[0]
        streams = test_params['streams']
        framelen_list = test_params['frame_length']
        load_list = test_params['load_kpps']
        nflows_list = test_params['num_flows']
        banner = " -- TEST %s --" % test_name
        print banner
        nstreams = len(streams)
        for streamd in streams:
            create_streamblocks(sd, streamd)

        for load in load_list:
            # compute per-stream load
            ps_load = load/nstreams
            config_port_generators(sd, ps_load, duration)
            for framelen in framelen_list:
                for nf in nflows_list:
                    ps_nf = nf/nstreams
                    modify_streamblocks(sd, framelen, ps_nf)
                    for rep in xrange(nreps):
                        banner = "  #%d:load=%skpps len=%s flows=%s" % (rep, load, framelen, nf)
                        print banner
                        test_infod = {"test": test, "load": load, "len": framelen, "flows": nf} 
                        sd.stc.perform("ResultClearAllTrafficCommand")
                        sd.stc.perform("GeneratorStart")
                        time.sleep(10)
                        rdir = perf_collect.perf_collect(test_name)
                        sd.stc.perform("GeneratorWaitForStop", WaitTimeout=WTO)
                        #time.sleep(5)
                        results = sd.get_streamblock_results()
                        prd = process_results(results, duration)
                        save_results(rdir, prd)
                        if prd["drop_percent"] > DROP_THRESH:
                            break
                    else: 
                        continue # executed if inner loop DID NOT break
                    break # executed if inner loop DID break
                          # now we break out of the nf loop


if __name__ == "__main__":
    try:
        main()
    except Exception, err: 
        print "ERROR: %s" % str(err)
    finally:
        print "Cleaning up"
        if sd:
            print "Disconnect and terminate"
            sd.disconnect_all_chasis()
            sd.terminate_session()
########

