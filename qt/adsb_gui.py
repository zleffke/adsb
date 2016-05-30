#!/usr/bin/env python

import numpy as np
import sys

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import Qt
import PyQt4.Qwt5 as Qwt
from adsb_table import *
from adsb_utilities import *

class main_widget(QtGui.QWidget):
    def __init__(self):
        super(main_widget, self).__init__()
        self.initUI()
        
    def initUI(self):
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        #self.grid.setColumnStretch(0,1)
        #self.grid.setColumnStretch(1,1)

class adsb_gui(QtGui.QMainWindow):
    def __init__(self, lock):
        super(adsb_gui, self).__init__()
        self.resize(1000,1000)
        #self.move(50,50)
        self.setWindowTitle('ADS-B Decoder')
        self.setAutoFillBackground(True)
        #self.ants_static_labels = []
        self.main_window = main_widget()

        self.callback    = None   #Callback accessor for tracking control
        self.update_rate = 500    #Feedback Query Auto Update Interval in milliseconds
        self.lock = lock
        self.current = []
        self.expired = []
        self.cur_cnt = 0
        self.exp_cnt = 0

        self.initUI()
        self.darken()
        self.setFocus()
        
    def initUI(self): 
        self.initMainWindow()
        self.initCurrentTable()
        self.initTimers()
        self.connectSignals()

        self.show()

    def initTimers(self):
        self.updateTimer = QtCore.QTimer(self)
        self.updateTimer.setInterval(self.update_rate)
        self.updateTimer.start()

    def connectSignals(self):
        QtCore.QObject.connect(self.updateTimer, QtCore.SIGNAL('timeout()'), self.updateTable)

    def updateTable(self):
        #self.lock.acquire()
        self.current = self.callback.get_current_list()
        self.expired = self.callback.get_expired_list()

        self.cur_cnt = self.callback.get_current_count()
        self.exp_cnt = self.callback.get_expired_count()

        #self.callback.Print_Data()
        #Print_ADSB_Data(current, expired)

        #self.Print_Data()
        #print len(self.current)
        statusmsg = ("| Current Count: %3i | Expired Count: %3i |" % (self.cur_cnt, self.exp_cnt))
        self.statusBar().showMessage(statusmsg)

        self.current_table.updateTable(self.current)
        #self.lock.release()

    def Print_Data(self):
        #self.lock.acquire()
        #os.system('clear')
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

    def get_current_data(self):
        pass

    def initCurrentTable(self):
        #create Current list table
        self.current_table=adsb_table(self.main_window)
        self.main_window.grid.addWidget(self.current_table, 0,0,1,1)

    def initMainWindow(self):
        self.setCentralWidget(self.main_window)
        exitAction = QtGui.QAction('Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(QtGui.qApp.quit)

        exportAction = QtGui.QAction('Export', self)
        exportAction.setShortcut('Ctrl+E')
        exportAction.triggered.connect(QtGui.qApp.quit)

        menubar = self.menuBar()
        self.fileMenu = menubar.addMenu('&File')
        self.fileMenu.addAction(exitAction)
        self.fileMenu.addAction(exportAction)
  
        self.statusBar().showMessage("| Disconnected | Current Count: 000 |")

    def set_callback(self, callback):
        self.callback = callback

    def darken(self):
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Background,QtCore.Qt.black)
        palette.setColor(QtGui.QPalette.WindowText,QtCore.Qt.black)
        palette.setColor(QtGui.QPalette.Text,QtCore.Qt.white)
        self.setPalette(palette)

    def utc_ts(self):
        return str(date.utcnow()) + " UTC | "

        
def main():
    app = QtGui.QApplication(sys.argv)
    ex = funcube_tlm_gui()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
