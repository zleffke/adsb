#!/usr/bin/env python3
########################################################
#   Title: High Altitude Balloon ADSB Payload
#  Thread: Main Thread
# Project: HAB Flights
# Version: 1.0
#    Date: July 2021
#  Author: Zach Leffke, KJ4QLP
# Comment:
########################################################

import threading
import os
import math
import sys
import string
import time
import socket
import json
import binascii as ba
import numpy
import datetime

from logger import *
from sbs1_thread import *
from beast_thread import *

class Main_Thread(threading.Thread):
    """ docstring """
    def __init__ (self, cfg):
        threading.Thread.__init__(self)
        threading.current_thread().name = "Main_Thread"
        self.setName("Main_Thread")
        self._stop  = threading.Event()
        self.cfg    = cfg
        #Configure which threads are enabled, development feature
        self.thread_enable = cfg['thread_enable']

        setup_logger(self.cfg['main']['log'])
        self.logger = logging.getLogger(self.cfg['main']['log']['name']) #main logger
        self.logger.info("configs: {:s}".format(json.dumps(self.cfg)))

        self.state  = 'BOOT' #BOOT, ACTIVE
        self.state_map = {
            'BOOT':0x00,        #bootup
            'IDLE':0x01,        #threads launched, no connections
            'RUN':0x02,         #client connected
        }

        self.connected = False #Connection Status, Network Thread

    def run(self):
        self.logger.info('Launched {:s}'.format(self.name))
        try:
            while (not self._stop.isSet()):
                if self.state == 'BOOT':
                    self._handle_state_boot()
                elif self.state == 'FAULT':
                    self._handle_state_fault()
                else:# NOT in BOOT or FAULT state
                    if self.state == 'IDLE':  self._handle_state_idle()
                    elif self.state == 'RUN':  self._handle_state_run()
                time.sleep(0.000001)

        except (KeyboardInterrupt): #when you press ctrl+c
            self.logger.warning('Caught CTRL-C, Terminating Threads...')
            self._stop_threads()
            self.logger.warning('Terminating Main Thread...')
            sys.exit()
        except SystemExit:
            self.logger.warning('Terminating Main Thread...')
        sys.exit()

    def set_sbs1_connected_status(self, status): #called by service thread
        #This should probably be via message queues
        self.sbs1_connected = status
        self.logger.info("SBS1 Network Connection Status: {0}".format(self.sbs1_connected))

    def set_beast_connected_status(self, status): #called by service thread
        #This should probably be via message queues
        self.beast_connected = status
        self.logger.info("Beast Network Connection Status: {0}".format(self.beast_connected))

    #---- STATE HANDLERS -----------------------------------
    def _handle_state_run(self):
        if (not self.sbs1_connected):
            self._set_state('IDLE')
        #self._check_thread_queues() #Check for messages from threads

    def _handle_state_idle(self):
        if (self.sbs1_connected): #Client and Device connected
            self._set_state('RUN')
        #self._check_thread_queues() #Check for messages from threads

    def _handle_state_boot(self):
        if self._init_threads():#if all threads activate succesfully
            self.logger.info('Successfully Launched Threads, Switching to IDLE State')
            #self._import_packets()
            self._set_state('IDLE')
            time.sleep(1)
        else:
            self.logger.info('Failed to Launched Threads...')
            self._set_state('FAULT')

    def _handle_state_fault(self):
        self.logger.warning("in FAULT state, exiting.......")
        self.logger.warning("Do Something Smarter.......")
        sys.exit()

    def _set_state(self, state):
        self.state = state
        self.logger.info('Changed STATE to: {:s}'.format(self.state))
    #---- END STATE HANDLERS -----------------------------------
    ###############################################################
    #---- MAIN THREAD CONTROLS -----------------------------------
    def _init_threads(self):
        self.logger.info("Thread enable: {:s}".format(json.dumps(self.cfg['thread_enable'])))
        try:
            #Initialize Threads
            self.logger.info("Thread enable: {:s}".format(json.dumps(self.cfg['thread_enable'])))
            for key in self.cfg['thread_enable'].keys():
                if self.cfg['thread_enable'][key]:
                    if key == 'sbs1': #Initialize SBS1 Thread
                        self.logger.info('Setting up SBS1 Thread')
                        self.sbs1_thread = SBS1_Thread(self.cfg['sbs1'], self) #SBS1 Thread
                        self.sbs1_thread.daemon = True
                    elif key == 'beast': #Initialize BEAST Thread
                        self.logger.info('Setting up Beast Thread')
                        self.beast_thread = Beast_Thread(self.cfg['beast'], self) #Beast Thread
                        self.beast_thread.daemon = True
            #Launch threads
            for key in self.cfg['thread_enable'].keys():
                if self.cfg['thread_enable'][key]:
                    if key == 'sbs1': #Launch SBS1 Thread
                        self.logger.info('Launching SBS1 Thread')
                        self.sbs1_thread.start() #non-blocking
                    elif key == 'beast': #Launch BEAST Thread
                        self.logger.info('Launching Beast Thread')
                        self.beast_thread.start() #non-blocking
            return True
        except Exception as e:
            self.logger.error('Error Launching Threads:', exc_info=True)
            self.logger.warning('Setting STATE --> FAULT')
            self._set_state('FAULT')
            return False

    def _stop_threads(self):
        for key in self.thread_enable.keys():
            if self.thread_enable[key]:
                if key == 'c2': #Initialize C2 Thread
                    self.c2_thread.stop()
                    #self.c2_thread.join() # wait for the thread to finish what it's doing
                elif key == 'radio': #Initialize Radio Thread
                    self.radio_thread.stop()
                    #self.radio_thread.join() # wait for the thread to finish what it's doing

    def set_state(self, state):
        self.state = state
        #print 'Changed STATE to: {:s}'.format(self.state)
        self.logger.info('Changed STATE to: {:s}'.format(self.state))
        if self.state == 'SAFE':
            #time.sleep(1) # Wait for flowgraphs to terminate before shutting of USRPs
            pass
        if self.state == 'ARMED':
            pass
            #time.sleep(1) #delay for USRP power up

        if self.state == 'FAULT':
            self.tm_bcn_wd.stop()
        #time.sleep(0.1)

    def get_state(self):
        return self.state

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
