#!/usr/bin/env python

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import Qt
import PyQt4.Qwt5 as Qwt

class adsb_table(QtGui.QTableWidget):
    def __init__(self, parent):
        super(adsb_table, self).__init__()
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setColumnCount(9)
        
        self.setHorizontalHeaderLabels(["ICAO", "Altitude [ft]", "Speed [kt]", "Track [deg]", "Range [km/mi]", "Az [deg]", "El [deg]", "msgs", "Seen"])
        self.horizontalHeader().setStyleSheet('font-size: 6pt; font-weight: bold')# font-family: Courier;')

        self.setStyleSheet('font-size: 6pt')#; font-family: Courier;')
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        
    def add_msg(self, aircraft):
        #newitem = QtGui.QTableWidgetItem(item)
        #self.setItem(m, n, newitem)
        rowPosition = self.rowCount()
        self.insertRow(rowPosition)
        # .setItem(row, column, item)

        #ICAO
        icao = QtGui.QTableWidgetItem(aircraft.icao)
        self.setItem(rowPosition, 0, icao)

        #Altitude
        alt = QtGui.QTableWidgetItem()
        if aircraft.alt != None: alt.setText("%5i"%aircraft.alt)
        else: alt.setText('')
        self.setItem(rowPosition, 1, alt)

        #Speed
        speed = QtGui.QTableWidgetItem()
        if aircraft.speed != None: speed.setText("%3.1f"%aircraft.speed)
        else: speed.setText('')
        self.setItem(rowPosition, 2, speed)

        #Track
        trk = QtGui.QTableWidgetItem()
        if aircraft.track != None: trk.setText("%3.1f"%aircraft.track)
        else: trk.setText('')
        self.setItem(rowPosition, 3, trk)

        #RAZEL
        rho = QtGui.QTableWidgetItem()
        az = QtGui.QTableWidgetItem()
        el = QtGui.QTableWidgetItem()
        if (aircraft.pos_valid):
            rho.setText("%3.2f / %3.2f"% (aircraft.range, aircraft.range*0.621371))
            az.setText("%3.1f"%aircraft.az) 
            el.setText("%3.1f"%aircraft.el)
        else:                       
            rho.setText('')
            az.setText('')
            el.setText('')
        self.setItem(rowPosition, 4, rho)
        self.setItem(rowPosition, 5, az)
        self.setItem(rowPosition, 6, el)
        
        #Message Count
        msgs = QtGui.QTableWidgetItem(("%i"%len(aircraft.msgs)))
        self.setItem(rowPosition, 7, msgs)

        #Time Since Last Message
        since = QtGui.QTableWidgetItem(("%2.3f"%aircraft.since))
        self.setItem(rowPosition, 8, since)

        self.resizeRowsToContents()
        self.resizeColumnsToContents()

    def updateTable(self, current):
        current.sort(key=lambda aircraft:aircraft.range, reverse=True)
        self.setRowCount(0)
        #self.setColumnCount(0)
        for a in current:
            self.add_msg(a)
