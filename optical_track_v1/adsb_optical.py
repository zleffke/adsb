#!/usr/bin/env python
##################################################
# Title: ADSB Optical Tracking
# Author: Zach Leffke
# Description: ADSB Optical Tracking project
# Generated: Aug 2019
##################################################

import os
import sys
import string
import serial
import math
import time
import numpy
import argparse
import json

from threading import Thread
from main_thread import *
import datetime as dt

def main(cfg):
    main_thread = Main_Thread(cfg)
    main_thread.daemon = True
    main_thread.run()
    sys.exit()

if __name__ == '__main__':
    startup_ts = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
	#--------START Command Line option parser------------------------------------------------------
    parser = argparse.ArgumentParser(description="Data Recorder",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    #General Options
    cwd = os.getcwd()
    #sch_fp_default = '/'.join([cwd, 'schedule'])
    cfg_fp_default = '/'.join([cwd, 'config'])
    parser.add_argument("--cfg_fp"   ,
                        dest   = "cfg_path" ,
                        action = "store",
                        type   = str,
                        default=cfg_fp_default,
                        help   = 'config path')
    parser.add_argument("--cfg_file" ,
                        dest="cfg_file" ,
                        action = "store",
                        type = str,
                        default="dev_config.json" ,
                        help = 'config file')

    args = parser.parse_args()
    #--------END Command Line option parser------------------------------------------------------
    os.system('reset')
    print "args", args
    cfg_fp = '/'.join([args.cfg_path, args.cfg_file])
    print "config file:", cfg_fp
    with open(cfg_fp, 'r') as cfg_f:
        cfg = json.loads(cfg_f.read())



    log_name = '.'.join([cfg['main']['name'],'main'])
    log_path = '/'.join([cfg['main']['log']['path'],startup_ts])
    cfg['main']['log'].update({
        'name':log_name,
        'startup_ts':startup_ts,
        'path':log_path
    })
    if not os.path.exists(cfg['main']['log']['path']):
        os.makedirs(cfg['main']['log']['path'])


    for key in cfg['thread_enable'].keys():
        #cfg[key].update({'log':{}})
        log_name =  '.'.join([cfg['main']['name'],cfg[key]['name']])
        cfg[key].update({
            'main_log':cfg['main']['log']['name']
        })
        cfg[key]['log'].update({
            'path':cfg['main']['log']['path'],
            'name':log_name,
            'startup_ts':startup_ts,
        })


    print json.dumps(cfg, indent=4)

    main(cfg)
    sys.exit()
