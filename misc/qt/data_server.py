#!/usr/bin/env python
#########################################
#   Title: ADSB Data Server Class       #
# Project: ADSB Fun                     #
# Version: 1.0                          #
#    Date: May 29, 2016                 #
#  Author: Zach Leffke, KJ4QLP          #
# Comment: Connects to dump1090 30003   #
#########################################

import socket
import threading
import sys
import os
from adsb_utilities import *

class Data_Server(threading.Thread):
    def __init__ (self, options, lock):
        threading.Thread.__init__(self)
        self._stop      = threading.Event()
        self.lock       = lock
        self.ip         = options.adsb_ip
        self.port       = options.adsb_port
        self.suspend    = False
        self.sock       = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.gs         = gs(options.gs_lat, options.gs_lon, options.gs_alt)
        self.current    = [] # current aircraft list
        self.expired    = [] # old aircraft list
        self.expire     = options.expire

    def run(self):
        self.sock.connect((self.ip, self.port))
        total_msg_count = 0
        aircraft_count = 0
        for l in self.readlines():
            total_msg_count += 1
            msg = sbs1_msg(l.strip('\r').split(','))

            if len(self.current) == 0:
                self.current.append(aircraft(msg.hex_ident))
                self.current[len(self.current)-1].add_msg(msg, self.gs)
            else:
                idx = -1
                for i in range(len(self.current)):
                    if msg.hex_ident == self.current[i].icao:
                        idx = i
                        break

                if idx != -1:
                    try:
                        self.current[i].add_msg(msg, self.gs)
                    except Exception as e:
                        print l
                        print (e)
                else:
                    try:
                        self.current.append(aircraft(msg.hex_ident))
                        self.current[len(self.current)-1].add_msg(msg, self.gs)
                    except Exception as e:
                        print l
                        print (e)

            for i in range(len(self.current)):
                if self.current[i].since > self.expire:
                    self.expired.append(self.current.pop(i))
                    break

            #Print_Data(self.current, self.expired)
            #self.Print_Data()

        print "Data Server run function exited..."
        print "ran out of lines in socket buffer.......?"
        sys.exit()

    def readlines(self, recv_buffer=4096, delim='\n'):
        #self.lock.acquire()
        buffer = ''
        data = True
        while data:
            data = self.sock.recv(recv_buffer)
            buffer += data

            while buffer.find(delim) != -1:
                line, buffer = buffer.split('\n', 1)
                #self.lock.release()
                yield line
        return

    def Print_Data(self):
        #self.lock.acquire()
        os.system('clear')
        print "Current Aircraft Count: %i" % len(self.current)
        print "#\tICAO\tRange [km/mi]\tmsgs"
        for i in range(len(self.current)):
            self.current[i].since = (date.utcnow() - self.current[i].last_seen).total_seconds()
            if self.current[i].range != None:
                print "%i\t%s\t%3.1f / %3.1f\t%i\t%3.1f" % (i+1, self.current[i].icao, self.current[i].range, self.current[i].range*0.621371, len(self.current[i].msgs), self.current[i].since)
            else:
                print "%i\t%s\t%3.1f\t\t%i\t%3.1f" % (i+1, self.current[i].icao, 0, len(self.current[i].msgs), self.current[i].since)

        print "\n"
        print "Expired Count:", len(self.expired)
        #self.lock.release()

    def get_current_list(self):
        return self.current

    def get_current_count(self):
        return len(self.current)

    def get_expired_list(self):
        return self.expired

    def get_expired_count(self):
        return len(self.expired)

    def update_db(self):
        pass

    def set_gui_access(self, gui_handle):
        self.gui = gui_handle

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
