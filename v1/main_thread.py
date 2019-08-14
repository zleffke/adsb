#!/usr/bin/env python
#############################################
#   Title: Data Recorder Main Thread        #
# Project: CYBORG                           #
# Version: 1.0                              #
#    Date: July 2019                        #
#  Author: Zach Leffke, KJ4QLP              #
# Comment:                                  #
#############################################

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

from optparse import OptionParser
import datetime

from logger import *
from data_handler import *
from watchdog_timer import *
from radio_thread import *

class Main_Thread(threading.Thread):
    def __init__ (self, cfg):
        threading.Thread.__init__(self, name = 'Main_Thread')
        self._stop      = threading.Event()
        self.cfg = cfg
        #Configure which threads are enabled, development feature
        self.thread_enable = cfg['thread_enable']

        setup_logger(self.cfg['main']['log'])
        self.logger = logging.getLogger(self.cfg['main']['log']['name']) #main logger
        self.logger.info("configs: {:s}".format(json.dumps(self.cfg)))

        self.state  = 'BOOT' #BOOT, ACTIVE
        self.state_map = {
            'BOOT':0x00,
            'SAFE':0x01,
            'ARMED':0x02,
            'FAULT':0x80
        }
        #Data Recorder TLM Beacon
        self.tm_bcn_rate = self.cfg['main']['tm_bcn_rate']
        self.tm_bcn_wd = Watchdog(self.tm_bcn_rate, 'tlm_bcn', self._tm_watchdog_event)

        self.c2_opcode = self.cfg['main']['c2_opcode']
        self.msg_types = {
            "tlm":0x01,
            "fft":0x02
        }

        #Recording Thread States
        self.rec_state_map = {
            'STANDBY':0x01,
            'STARTUP':0x02,
            'RECORD' :0x04,
            'DONE'   :0x08,
            'FAULT'  :0x80
        }

    def run(self):
        print "Main Thread Started..."
        self.logger.info('Launched main thread')
        try:
            while (not self._stop.isSet()):
                if self.state == 'BOOT':
                    #recorder activating for the first time
                    #Activate all threads
                    #State Change:  BOOT --> SAFE
                    if self._init_threads():#if all threads activate succesfully
                        self.logger.info('Successfully Launched Threads, Switching to SAFE State')
                        self.set_state('SAFE')
                        time.sleep(1)
                        self.logger.info('Starting Telemetry Watchdog')
                        self.tm_bcn_wd.start()
                    else:
                        self.set_state('FAULT')
                    pass
                else: # NOT IN BOOT State
                    #Always check for C2 Message
                    #print 'c2 queue', self.c2_thread.rx_q.empty()
                    if self.thread_enable['c2']:
                        if (not self.c2_thread.rx_q.empty()): #Received a message from flight computer
                            c2_msg = self.c2_thread.rx_q.get()
                            #print c2_msg.strip()
                            #HAve to typecast to string for JSON/Dict key comparisons.....
                            self._process_c2_message(c2_msg.strip())
                            #self.radio_thread.cmd_q.put(str(c2_msg.strip()))
                    if self.thread_enable['radio']:
                        if (not self.radio_thread.fft_q.empty()):
                            fft_msg = self.radio_thread.fft_q.get()
                            self._process_fft_snapshot(fft_msg)
                            #self.radio_thread._fft_snapshot()
                    #self._process_c2_message('fft')
                time.sleep(0.1)

        except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
            print "\nCaught CTRL-C, Killing Threads..."
            self.logger.warning('Caught CTRL-C, Terminating Threads...')
            self.tm_bcn_wd.stop() #Stop TM Beacon
            self._stop_threads()
            self.logger.warning('Terminating Main Thread...')
            sys.exit()
        sys.exit()



    def _process_c2_message(self, cmd):
        print "Received Command: {:s}".format(cmd)
        self.logger.info("Received Command: {:s}".format(cmd))
        #if ((cmd =="stop") and (self.state == "RECORD")):
        #    self.radio_thread._stop_flowgraph()
        if (cmd == 'tlm'):
            tlm_msg = self._generate_tlm_msg()
            self._send_tlm_bcn(tlm_msg)
        if (cmd == 'reset'):
            self.radio_thread.cmd_q.put(cmd)
        if self.state == 'SAFE':
            if (cmd =="ARM"):
                self.set_state('ARMED')
        if self.state == 'ARMED':
            if (cmd == 'auto') or (cmd == 'stop') or (cmd == 'next') or (cmd == 'fft'):
                self.radio_thread.cmd_q.put(cmd)
            elif ('opcode' in cmd):
                self.radio_thread.cmd_q.put(cmd)
            elif (cmd == 'SAFE'):
                self.radio_thread.cmd_q.put('stop')
                self.set_state('SAFE')

    def _tm_watchdog_event(self):
        #print 'TLM Beacon Watchdog fired'
        self.logger.info('TLM Beacon Watchdog fired')
        self.tm_bcn_wd.reset()
        tlm_msg = self._generate_tlm_msg()
        self._send_tlm_bcn(tlm_msg)

    def _generate_tlm_msg(self):
        #Generate Telemetry Beacon Message (Dictionary)
        #returns dictionary to calling thread
        #print 'Generating TLM Beacon'
        self.logger.info('Generating TLM Beacon')

        tlm_msg = {}
        tlm_msg['datetime'] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        #tlm_msg['msg_type'] = self.msg_types['tlm']
        tlm_msg['msg_type'] = 'Telemetry'

        #----MAIN STATE TM----------------------------
        #tlm_msg['main_state'] = self.state_map[self.state]
        tlm_msg['main_state'] = self.state
        #--------------------------------------------

        #--RADIO TM------------------------------
        if self.thread_enable['radio']:
            self.radio_thread.get_tlm()
            time.sleep(0.005)
            rec_status = None
            if (not self.radio_thread.status_q.empty()):
                rec_status = self.radio_thread.status_q.get()
                #rec_status['state'] = self.rec_state_map[rec_status['state']]#map to byte code
            tlm_msg['record'] = rec_status
        else:
            tlm_msg['record'] = {}
            tlm_msg['record'].update({
                'state': 0,
                'cycle': 1,
                'opcode': 1,
                'inhibit': False
            })
            pass
        #-------------------------------------------
        #print "TLM Beacon: {:s}".format(json.dumps(tlm_msg))
        self.logger.info('TLM Beacon: {:s}'.format(json.dumps(tlm_msg)))
        return tlm_msg

    def _send_tlm_bcn(self, msg):
        #Data Recorder Telemetry
        # input: dictionary of telemetry message
        # converts to bytearray, sends to C2 thread
        # bcn = bytearray()
        # bcn = struct.pack('<B', msg['msg_type'])            #1 byte, uint8, type==TLM: should be 0x01
        # bcn += struct.pack('<B', msg['main_state'])         #1 byte, uint8, main state
        # #Recording / RADIO
        # bcn += struct.pack('<B', msg['record']['state'])    #1 byte, uint8, recording state
        # bcn += struct.pack('<B', msg['record']['cycle'])    #1 byte, uint8, record cycle
        # bcn += struct.pack('<B', msg['record']['opcode'])   #1 byte, uint8, record opcode
        # bcn += struct.pack('<B', int(msg['record']['inhibit']))  #1 byte, uint8, record inhibit, 0=false, 1 = true
        #Relay States

        #print ba.hexlify(bytearray(bcn))
        #self.logger.info('Queueing DR Telemetry Beacon (0x01) for Transmission')
        #self.c2_thread.tx_q.put(bytearray(bcn))
        self.c2_thread.tx_q.put(json.dumps(msg, indent=4))
        #self._decode_dr_tlm_bcn(bcn)

    def _decode_dr_tlm_bcn(self, bcn):
        msg = {}
        msg['msg_type']         = int(struct.unpack('<B',bcn[0:1])[0])
        msg['main_state']       = int(struct.unpack('<B',bcn[1:2])[0])
        #Recording / RADIO
        msg['record'] = {}
        msg['record']['state']  = int(struct.unpack('<B',bcn[2:3])[0])
        msg['record']['cycle']  = int(struct.unpack('<B',bcn[3:4])[0])
        msg['record']['opcode'] = int(struct.unpack('<B',bcn[4:5])[0])
        msg['record']['inhibit']= bool(struct.unpack('<B',bcn[5:6])[0])
        print "TLM DECODER:", json.dumps(msg)

    def _init_threads(self):
        try:
            #Initialize Threads
            print 'thread_enable', self.thread_enable.keys(), self.thread_enable['c2']
            self.logger.info("Thread enable: {:s}".format(json.dumps(self.thread_enable)))
            for key in self.thread_enable.keys():
                if self.thread_enable[key]:
                    if key == 'c2': #Initialize C2 Thread
                        self.logger.info('Setting up C2 Thread')
                        self.c2_thread = Data_Handler(self.cfg['c2'], self) #C2 Thread
                        self.c2_thread.daemon = True
                    elif key == 'radio': #Initialize Radio Thread
                        self.logger.info('Setting up GNU Radio Thread')
                        self.radio_thread = Radio_Thread(self.cfg['radio'], self) #GNU Radio Thread
                        self.radio_thread.daemon = True

            #Launch threads
            for key in self.thread_enable.keys():
                if self.thread_enable[key]:
                    if key == 'c2': #Initialize C2 Thread
                        self.logger.info('Launching C2 Thread')
                        self.c2_thread.start() #non-blocking
                    elif key == 'radio': #Initialize Radio Thread
                        self.logger.info('Launching GNU Radio Thread')
                        self.radio_thread.start() #non-blocking
            time.sleep(2)#wait for thread spinup
            return True
        except Exception as e:
            self.logger.warning('Error Launching Threads:')
            self.logger.warning(e, exc_info=True)
            self.logger.warning('Setting STATE --> FAULT')
            self.state = 'FAULT'
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

    #---Data Recorder STATE FUNCTIONS----
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
    #---END C2 STATE FUNCTIONS----

    def utc_ts(self):
        return str(date.utcnow()) + " UTC | "

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
