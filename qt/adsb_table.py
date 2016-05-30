#!/usr/bin/env python

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import Qt
import PyQt4.Qwt5 as Qwt

class adsb_table(QtGui.QTableWidget):
    def __init__(self, parent):
        super(adsb_table, self).__init__()
        self.parent = parent
        self.packet_count = 0
        self.initUI()

    def initUI(self):
        #self.setRowCount(30)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["#","ICAO", "Range", "msgs", "Seen"])
        #self.horizontalHeader().setResizeMode(0,1)
        #self.horizontalHeader().setResizeMode(1,1)
        #self.horizontalHeader().setResizeMode(2,1)
        self.setStyleSheet('font-size: 6pt')#; font-family: Courier;')
        self.resizeRowsToContents()
        
    def add_msg(self, msg):
        #newitem = QtGui.QTableWidgetItem(item)
        #self.setItem(m, n, newitem)
        rowPosition = self.table.rowCount()
        table.insertRow(rowPosition)
