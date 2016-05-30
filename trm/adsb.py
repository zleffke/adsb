#!/usr/bin/env python
#########################################
#   Title: Tracking Daemon              #
# Project: VTGS Tracking Daemon         #
# Version: 1.2                          #
#    Date: Mar 13, 2015                 #
#  Author: Zach Leffke, KJ4QLP          #
# Comment: This is the initial version  # 
#          of the Tracking Daemon.      #
#########################################

import math
import string
import time
import sys
import csv
import os
import socket

from adsb_utilities import *
from optparse import OptionParser

if __name__ == '__main__':
    #--------START Command Line option parser------------------------------------------------------
    usage  = "usage: %prog "
    parser = OptionParser(usage = usage)
    h_adsb_ip       = "Set ADSB Modem IP [default=%default]"
    h_adsb_port     = "Set ADSB Modem Port [default=%default]"
    h_gs_lat        = "Set GS Latitude [default=%default [deg]]"
    h_gs_lon        = "Set GS Longitude [default=%default [deg]]"
    h_gs_alt        = "Set GS Altitude [default=%default [km]]"
    
    parser.add_option("", "--adsb_ip"  , dest="adsb_ip"  , type="string", default="198.82.148.60" , help=h_adsb_ip)
    parser.add_option("", "--adsb_port", dest="adsb_port", type="int"   , default="30003"         , help=h_adsb_port)
    parser.add_option("", "--gs_lat"   , dest="gs_lat"   , type="float" , default="37.202195"     , help=h_gs_lat)
    parser.add_option("", "--gs_lon"   , dest="gs_lon"   , type="float" , default="-80.406851"    , help=h_gs_lon)
    parser.add_option("", "--gs_alt"   , dest="gs_alt"   , type="float" , default="0.630936"      , help=h_gs_alt)
    
    (options, args) = parser.parse_args()
    #--------END Command Line option parser------------------------------------------------------    

    msg_list = []
    ac_list = []
    old_list = []

    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((options.adsb_ip, options.adsb_port))
    total_msg_count = 0
    aircraft_count = 0

    gs = gs(options.gs_lat, options.gs_lon, options.gs_alt)

    for l in readlines(s):
        total_msg_count += 1
        msg = sbs1_msg(l.strip('\r').split(','), options)

        if len(ac_list) == 0:
            ac_list.append(aircraft(msg.hex_ident))
            ac_list[len(ac_list)-1].add_msg(msg, gs)
        else:
            idx = -1
            for i in range(len(ac_list)): 
                if msg.hex_ident == ac_list[i].icao: 
                    idx = i
                    break

            if idx != -1:
                ac_list[i].add_msg(msg, gs)
            else:
                ac_list.append(aircraft(msg.hex_ident))
                ac_list[len(ac_list)-1].add_msg(msg, gs)

        for i in range(len(ac_list)):
            if ac_list[i].since > 60: 
                old_list.append(ac_list.pop(i))
                break
                    
                    #aircraft_count = len(aircraft_list)

        Print_Data(ac_list, old_list)
        #print data
        #if ((len(data[14])!=0) and (len(data[15])!=0) and (len(data[11])!=0)):
        #    lat = float(data[14])
        #    lon = float(data[15])
        #    alt = float(data[11])*0.0003048
        #    [rho, az, el] = RAZEL(options.gs_lat, options.gs_lon, options.gs_alt, lat, lon, alt)
        #    print "%s\t%2.6f\t%2.6f\t%5i\t%3.1f\t%3.1f\t%2.1f\t%s" % (str(data[4]),lat, lon, alt/0.0003048, rho, az, el, data[1])
            #print data[4],data[14], data[15], data[11], rho, az, el
    sys.exit()
