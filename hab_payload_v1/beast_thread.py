#!/usr/bin/env python3
########################################################
#   Title: High Altitude Balloon ADSB Payload
#  Thread: SBS1 Thread
# Project: HAB Flights
# Version: 0.0.1
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
import errno
import json
import binascii as ba
import numpy
import datetime
from queue import Queue
from logger import *

class Beast_Thread(threading.Thread):
    """
    Title: Beast Client Thread
    Project: ADSB HAB Payload
    Version: 0.0.1
    Date: July 2021
    Author: Zach Leffke, KJ4QLP

    Purpose:
        Handles TCP Interface to ADSB Receiver for SBS1 Format

    Args:
        cfg - Configurations for thread, dictionary format.
        parent - parent thread, used for callbacks

    Format Reference
    """
    def __init__ (self, cfg, parent):
        threading.Thread.__init__(self)
        self._stop  = threading.Event()
        self.cfg    = cfg
        self.parent = parent
        self.setName(self.cfg['thread_name'])
        self.logger = logging.getLogger(self.cfg['main_log'])

        self.rx_q   = Queue()
        self.connected = False
        self.logger.info("Initializing {}".format(self.name))

        self.data_logger = None

    def run(self):
        self.logger.info('Launched {:s}'.format(self.name))
        self._init_socket()
        while (not self._stop.isSet()):
            if not self.connected:
                try:
                    self._attempt_connect()
                except socket.error as err:
                    if err.args[0] == errno.ECONNREFUSED:
                        self.connected = False
                        time.sleep(self.cfg['retry_time'])
                except Exception as e:
                    self._handle_socket_exception(e)
            else:
                try:
                    for l in self._readlines():
                        self._handle_recv_data(l)
                except socket.timeout as e: #Expected after connection
                    self._handle_socket_timeout()
                except Exception as e:
                    self._handle_socket_exception(e)
            time.sleep(0.000001)

        self.sock.close()
        self.logger.warning('{:s} Terminated'.format(self.name))

    def _readlines(self, recv_buffer=1024, delim=0x1a):
        buffer = bytearray()
        data = True
        while data:
            data = bytearray(self.sock.recv(recv_buffer))
            buffer += data
            while buffer.find(delim) != -1:
                i = buffer.find(delim)
                frame = bytearray()
                if buffer[i+1] == 0x31: #11 bytes w/delim
                    frame = buffer[i:i+11]
                    del buffer[i:i+11]
                    yield frame
                elif buffer[i+1] == 0x32: #16 bytes w/delim
                    frame = buffer[i:i+16]
                    del buffer[i:i+16]
                    yield frame
                elif buffer[i+1] == 0x33: #23 bytes w/delim
                    frame = buffer[i:i+23]
                    del buffer[i:i+23]
                    yield frame
                elif buffer[i+1] == 0x1a:
                    del buffer[i]
        return

    def _readlines_old(self, recv_buffer=4096, delim=0x1a):
        #self.lock.acquire()
        buffer = bytearray()
        data = True
        while data:
            data = self.sock.recv(recv_buffer)
            print (ba.hexlify(data))
            buffer += data
            #while buffer.find(delim) != -1:
            while buffer.find(delim) != -1:
                line, buffer = buffer.split(delim, 1)
                print(ba.hexlify(line))
                print(len(buffer))
                yield line.strip('\r')
        return

    def _start_logging(self):
        self.cfg['log']['startup_ts'] = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        print (self.cfg['log'])
        setup_logger(self.cfg['log'])
        self.data_logger = logging.getLogger(self.cfg['log']['name']) #main logger
        for handler in self.data_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                self.logger.info("Started {:s} Data Logger: {:s}".format(self.name, handler.baseFilename))

    def _stop_logging(self):
        if self.data_logger != None:
            handlers = self.data_logger.handlers[:]
            print (handlers)
            for handler in handlers:
                if isinstance(handler, logging.FileHandler):
                    self.logger.info("Stopped Logging: {:s}".format(handler.baseFilename))
                handler.close()
                self.data_logger.removeHandler(handler)
            self.data_logger = None

    #### Socket and Connection Handlers ###########
    def _handle_recv_data(self, data):
        try:
            if self.data_logger != None:
                self.data_logger.info("{:s}".format(ba.hexlify(data).decode('utf-8')))
        except Exception as e:
            self.logger.debug("Unhandled Receive Data Error")
            self.logger.debug(sys.exc_info())

    def _handle_socket_timeout(self):
        pass

    def _send_msg(self, msg):
        self.logger.info("Sending Command: {:s}".format(msg['name']))
        cmd = binascii.unhexlify(msg['hex'])
        self.sock.sendall(cmd)
        self.data_logger.info("TX: {:s}".format(cmd.hex()))

    def _reset(self):
        self.logger.info("Resetting Packet Counters")

    def get_tlm(self):
        self.tlm['connected'] = self.connected
        self.tlm_q.put(self.tlm)

    def _attempt_connect(self):
        self.logger.info("Attempting to connect to {:s}: [{:s}, {:d}]".format(self.cfg['name'],
                                                                              self.cfg['adsb_rx']['ip'],
                                                                              self.cfg['adsb_rx']['port']))
        self.sock.connect((self.cfg['adsb_rx']['ip'], self.cfg['adsb_rx']['port']))
        self.logger.info("Connected to {:s}: [{:s}, {:d}]".format(self.cfg['name'],
                                                                  self.cfg['adsb_rx']['ip'],
                                                                  self.cfg['adsb_rx']['port']))

        time.sleep(0.01)
        self.sock.settimeout(self.cfg['timeout'])   #set socket timeout
        self.connected = True
        #self.tx_q.queue.clear()
        self.parent.set_sbs1_connected_status(self.connected)
        self._start_logging()


    def _handle_socket_exception(self, e):
        self.logger.debug("Unhandled Socket error")
        self.logger.debug(sys.exc_info())
        self._reset_socket()

    def _reset_socket(self):
        self.logger.debug('resetting socket...')
        self.sock.close()
        self.connected = False
        self.parent.set_sbs1_connected_status(self.connected)
        self._stop_logging()
        self._init_socket()

    def _init_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #TCP Socket, initialize
        self.logger.debug("Setup socket")

    #### END Socket and Connection Handlers ###########
    def stop(self):
        #self.conn.close()
        self.logger.info('{:s} Terminating...'.format(self.name))
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

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
