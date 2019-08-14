#!/usr/bin/env python
#########################################
#   Title: ADSB QT Application          #
# Project: ADSB Fun                     #
# Version: 1.0                          #
#    Date: May 29, 2016                 #
#  Author: Zach Leffke, KJ4QLP          #
# Comment: This is the initial version  # 
#########################################

import math
import string
import time
import sys
import os
import socket
import threading

from data_server import *
from optparse import OptionParser
from adsb_gui import *

def main():
    #--------START Command Line option parser------------------------------------------------------
    usage  = "usage: %prog "
    parser = OptionParser(usage = usage)
    h_adsb_ip       = "Set ADSB Modem IP [default=%default]"
    h_adsb_port     = "Set ADSB Modem Port [default=%default]"
    h_expire        = "Set current list expiration timeout [default=%default [sec]]"
    h_gs_lat        = "Set GS Latitude [default=%default [deg]]"
    h_gs_lon        = "Set GS Longitude [default=%default [deg]]"
    h_gs_alt        = "Set GS Altitude [default=%default [km]]"
    
    parser.add_option("-a", "--adsb_ip"  , dest="adsb_ip"  , type="string", default="198.82.148.60" , help=h_adsb_ip)
    parser.add_option("-p", "--adsb_port", dest="adsb_port", type="int"   , default="30003"         , help=h_adsb_port)
    parser.add_option("-e", "--expire"     , dest="expire"   , type="float" , default="60"     , help=h_expire)
    parser.add_option("", "--gs_lat"   , dest="gs_lat"   , type="float" , default="37.202195"     , help=h_gs_lat)
    parser.add_option("", "--gs_lon"   , dest="gs_lon"   , type="float" , default="-80.406851"    , help=h_gs_lon)
    parser.add_option("", "--gs_alt"   , dest="gs_alt"   , type="float" , default="0.630936"      , help=h_gs_alt)
    
    (options, args) = parser.parse_args()
    #--------END Command Line option parser------------------------------------------------------    

    lock = threading.Lock()

    server_thread = Data_Server(options, lock)
    server_thread.daemon = True
    #server_thread.run() #blocking
    server_thread.start() #Non-block
    #print "Non Block"
    #sys.exit()

    app = QtGui.QApplication(sys.argv)
    win = adsb_gui(lock)
    win.set_callback(server_thread)
    #ex = adsb_gui()
    #server_thread.set_gui_access(ex)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

    
