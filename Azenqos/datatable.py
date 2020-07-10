import datetime
import threading
import sys
import os

# Adding folder path
sys.path.insert(1, os.path.dirname(os.path.realpath(__file__)))

import pyqtgraph as pg
import numpy as np
import global_config as gc

from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *  # QAbstractTableModel, QVariant, Qt, pyqtSignal, QThread
from PyQt5.QtSql import *  # QSqlQuery, QSqlDatabase
from PyQt5.QtGui import *
from qgis.core import *
from qgis.utils import *
from qgis.gui import *
from itertools import groupby
from .globalutils import Utils
from .filter_header import *
from .gsm_query import GsmDataQuery
from .cdma_evdo_query import CdmaEvdoQuery
from .lte_query import LteDataQuery
from .nr_query import NrDataQuery
from .signalling_query import SignalingDataQuery
from .wcdma_query import WcdmaDataQuery
from .worker import Worker
from .customize_properties import *


class TableWindow(QWidget):
    def __init__(self, parent, windowName):
        super().__init__(parent)
        self.title = windowName
        self.rows = 0
        self.columns = 0
        self.fetchRows = 0
        self.fetchColumns = 0
        self.tablename = ""
        self.tableHeader = None
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.dataList = []
        self.customData = []  # For customize cell with text
        self.customHeader = []  # For customize header with text
        self.appliedSchema = []  # For customize cell with schema
        self.currentRow = 0
        self.dateString = ""
        self.tableViewCount = 0
        self.parentWindow = parent
        self.setupUi()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        windowParentName = (windowName.split("_"))[0]
        if not windowParentName == "Signaling":
            self.customContextMenuRequested.connect(self.generateMenu)
        self.properties_window = PropertiesWindow(
            self,
            gc.azenqosDatabase,
            self.dataList,
            self.tableHeader,
            self.appliedSchema,
            self.customData,
        )

    def setupUi(self):
        self.setObjectName(self.title)
        self.setWindowTitle(self.title)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Init table
        self.tableView = QTableView(self)
        self.tableView.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Init filter header
        self.filterHeader = FilterHeader(self.tableView)
        self.filterHeader.setSortIndicator(-1, Qt.AscendingOrder)
        self.tableView.doubleClicked.connect(self.showDetail)
        self.tableView.clicked.connect(self.updateSlider)
        self.tableView.setSortingEnabled(True)
        self.tableView.setCornerButtonEnabled(False)
        self.tableView.setStyleSheet(
            "QTableCornerButton::section{border-width: 1px; border-color: #BABABA; border-style:solid;}"
        )
        self.specifyTablesHeader()

        # Attach header to table, create text filter
        self.tableView.setHorizontalHeader(self.filterHeader)
        self.tableView.verticalHeader().setFixedWidth(
            self.tableView.verticalHeader().sizeHint().width()
        )
        if self.tableHeader and len(self.tableHeader) > 0:
            self.filterHeader.setFilterBoxes(gc.maxColumns, self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tableView)
        # flayout = QFormLayout()
        # layout.addLayout(flayout)
        # for i in range(len(self.tableHeader)):
        #     headerText = self.tableHeader[i]
        #     if headerText:
        #         le = QLineEdit(self)
        #         flayout.addRow("Filter: {}".format(headerText), le)
        #         le.textChanged.connect(lambda text, col=i:
        #                             self.proxyModel.setFilterByColumn(QRegExp(text, Qt.CaseInsensitive, QRegExp.FixedString),
        #                                                     col))
        # self.setFixedWidth(layout.sizeHint())
        self.setLayout(layout)
        self.show()

    def updateTable(self):
        self.setTableModel(self.dataList)

    def setTableModel(self, dataList):
        if self.rows and self.columns:
            while len(dataList) < self.rows:
                dataList.append([])

            for dataRow in dataList:
                if len(dataRow) >= self.columns:
                    if self.columns < self.fetchColumns:
                        self.fetchColumns = self.columns
                    dataRow = dataRow[: self.fetchColumns]
                while len(dataRow) < self.columns:
                    dataRow.append("")

            if len(self.tableHeader) >= self.columns:
                self.tableHeader = self.tableHeader[: self.columns]
            else:
                while len(self.tableHeader) < self.columns:
                    self.tableHeader.append("")
                # self.filterHeader.setFilterBoxes(len(self.tableHeader), self)

        for customItem in self.customData:
            try:
                if customItem["text"] == '""':
                    customItem["text"] = ""
                dataList[customItem["row"]][customItem["column"]] = customItem["text"]
            except:
                self.customData.remove(customItem)

        if self.customHeader:
            self.tableHeader = self.customHeader

        self.dataList = dataList
        self.tableModel = TableModel(dataList, self.tableHeader, self)
        self.proxyModel = SortFilterProxyModel(self)
        self.proxyModel.setSourceModel(self.tableModel)
        self.tableView.setModel(self.proxyModel)
        self.tableView.setSortingEnabled(True)

        if not self.rows:
            self.rows = self.tableModel.rowCount(self)
            self.fetchRows = self.rows

        if not self.columns:
            self.columns = self.tableModel.columnCount(self)
            self.fetchColumns = self.columns
        # self.tableView.resizeColumnsToContents()

    def setDataSet(self, data_set: list):
        self.dataList = data_set

    def setTableSize(self, sizelist: list):
        if sizelist:
            self.rowCount = sizelist[0]
            self.columnCount = sizelist[1]

    def specifyTablesHeader(self):
        if self.title is not None:
            # GSM
            if self.title == "GSM_Radio Parameters":
                self.tableHeader = ["Element", "Full", "Sub"]
                self.appliedSchema = self.initializeQuerySchema(
                    GsmDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getRadioParameters()
                )
                # self.dataList = GsmDataQuery(None).getRadioParameters()
            elif self.title == "GSM_Serving + Neighbors":
                self.tableHeader = [
                    "Time",
                    "Cellname",
                    "LAC",
                    "BSIC",
                    "ARFCN",
                    "RxLev",
                    "C1",
                    "C2",
                    "C31",
                    "C32",
                ]
                self.appliedSchema = self.initializeQuerySchema(
                    GsmDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getServingAndNeighbors()
                )
            elif self.title == "GSM_Current Channel":
                self.tableHeader = ["Element", "Value"]
                self.appliedSchema = self.initializeQuerySchema(
                    GsmDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getCurrentChannel()
                )
            elif self.title == "GSM_C/I":
                self.tableHeader = ["Time", "ARFCN", "Value"]
                self.appliedSchema = self.initializeQuerySchema(
                    GsmDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getCSlashI()
                )
            # TODO: find the way to find event counter
            # elif self.title == "GSM_Events Counter":
            #     self.tableHeader = ["Event", "MS1", "MS2", "MS3", "MS4"]

            # WCDMA
            if self.title == "WCDMA_Active + Monitored Sets":
                self.tableHeader = [
                    "Time",
                    "CellName",
                    "CellType",
                    "SC",
                    "Ec/Io",
                    "RSCP",
                    "Freq",
                    "Event",
                ]
                self.appliedSchema = self.initializeQuerySchema(
                    WcdmaDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getActiveMonitoredSets()
                )
            elif self.title == "WCDMA_Radio Parameters":
                self.tableHeader = ["Element", "Value"]
                self.appliedSchema = self.initializeQuerySchema(
                    WcdmaDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getRadioParameters()
                )
            elif self.title == "WCDMA_Active Set List":
                self.tableHeader = [
                    "Time",
                    "Freq",
                    "PSC",
                    "Cell Position",
                    "Cell TPC",
                    "Diversity",
                ]
                self.appliedSchema = self.initializeQuerySchema(
                    WcdmaDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getActiveSetList()
                )
            elif self.title == "WCDMA_Monitored Set List":
                self.tableHeader = ["Time", "Freq", "PSC", "Cell Position", "Diversity"]
                self.appliedSchema = self.initializeQuerySchema(
                    WcdmaDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getMonitoredSetList()
                )
            elif self.title == "WCDMA_BLER Summary":
                self.tableHeader = ["Element", "Value"]
                self.appliedSchema = self.initializeQuerySchema(
                    WcdmaDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getBlerSummary()
                )
            elif self.title == "WCDMA_BLER / Transport Channel":
                self.tableHeader = ["Transport Channel", "Percent", "Err", "Rcvd"]
                self.appliedSchema = self.initializeQuerySchema(
                    WcdmaDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getBLER_TransportChannel()
                )
            elif self.title == "WCDMA_Line Chart":
                self.tableHeader = ["Element", "Value", "MS", "Color"]
            elif self.title == "WCDMA_Bearers":
                self.tableHeader = [
                    "N Bearers",
                    "Bearers ID",
                    "Bearers Rate DL",
                    "Bearers Rate UL",
                ]
                self.appliedSchema = self.initializeQuerySchema(
                    WcdmaDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getBearers()
                )
            elif self.title == "WCDMA_Pilot Poluting Cells":
                self.tableHeader = ["Time", "N Cells", "SC", "RSCP", "Ec/Io"]
                self.appliedSchema = self.initializeQuerySchema(
                    WcdmaDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getPilotPolutingCells()
                )
            elif self.title == "WCDMA_Active + Monitored Bar":
                self.tableHeader = ["Cell Type", "Ec/Io", "RSCP"]
                self.appliedSchema = self.initializeQuerySchema(
                    WcdmaDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getActiveMonitoredBar()
                )
            elif self.title == "WCDMA_CM GSM Reports":
                self.tableHeader = ["Time", "", "Eq.", "Name", "Info."]

            elif self.title == "WCDMA_CM GSM Cells":
                self.tableHeader = ["Time", "ARFCN", "RxLev", "BSIC", "Measure"]
                self.appliedSchema = self.initializeQuerySchema(
                    WcdmaDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getCmGsmCells()
                )
            elif self.title == "WCDMA_Pilot Analyzer":
                self.tableHeader = ["Element", "Value", "Cell Type", "Color"]

            # LTE
            elif self.title == "LTE_Radio Parameters":
                self.tableHeader = ["Element", "PCC", "SCC0", "SCC1"]
                self.appliedSchema = self.initializeQuerySchema(
                    LteDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getRadioParameters()
                )
            elif self.title == "LTE_Serving + Neighbors":
                self.tableHeader = ["Time", "EARFCN", "Band", "PCI", "RSRP", "RSRQ"]
                self.appliedSchema = self.initializeQuerySchema(
                    LteDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getServingAndNeighbors()
                )
            elif self.title == "LTE_PUCCH/PDSCH Parameters":
                self.tableHeader = ["Element", "Value"]
                self.appliedSchema = self.initializeQuerySchema(
                    LteDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getPucchPdschParameters()
                )
            elif self.title == "LTE_LTE Line Chart":
                self.tableHeader = ["Element", "Value", "MS", "Color"]
            elif self.title == "LTE_LTE RLC":
                self.tableHeader = ["Element", "Value", "", "", ""]
                self.appliedSchema = self.initializeQuerySchema(
                    LteDataQuery(gc.azenqosDatabase, gc.currentDateTimeString).getRlc()
                )
            elif self.title == "LTE_LTE VoLTE":
                self.tableHeader = ["Element", "Value"]
                self.appliedSchema = self.initializeQuerySchema(
                    LteDataQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getVolte()
                )

                
            elif self.title == "5G NR_Radio Parameters":
                self.tableHeader = ["Element", "PCC", "SCC0", "SCC1", "SCC2", "SCC3", "SCC4", "SCC5", "SCC6"]
                self.dataList = NrDataQuery(
                    gc.azenqosDatabase, gc.currentDateTimeString
                ).getRadioParameters()
            elif self.title == "5G NR_Serving + Neighbors":
                (self.tableHeader,self.dataList) = NrDataQuery(
                    gc.azenqosDatabase, gc.currentDateTimeString
                ).getServingAndNeighbors()

            # CDMA/EVDO
            elif self.title == "CDMA/EVDO_Radio Parameters":
                self.tableHeader = ["Element", "Value"]
                self.appliedSchema = self.initializeQuerySchema(
                    CdmaEvdoQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getRadioParameters()
                )
            elif self.title == "CDMA/EVDO_Serving + Neighbors":
                self.tableHeader = ["Time", "PN", "Ec/Io", "Type"]
                self.appliedSchema = self.initializeQuerySchema(
                    CdmaEvdoQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getServingAndNeighbors()
                )
            elif self.title == "CDMA/EVDO_EVDO Parameters":
                self.tableHeader = ["Element", "Value"]
                self.appliedSchema = self.initializeQuerySchema(
                    CdmaEvdoQuery(
                        gc.azenqosDatabase, gc.currentDateTimeString
                    ).getEvdoParameters()
                )

            # Data
            elif self.title == "Data_GSM Data Line Chart":
                self.tableHeader = ["Element", "Value", "MS", "Color"]
            elif self.title == "Data_WCDMA Data Line Chart":
                self.tableHeader = ["Element", "Value", "MS", "Color"]
            elif self.title == "Data_GPRS/EDGE Information":
                self.tableHeader = ["Element", "Value"]
            elif self.title == "Data_Web Browser":
                self.tableHeader = ["Type", "Object"]
                self.windowHeader = ["ID", "URL", "Type", "State", "Size(%)"]
            elif self.title == "Data_HSDPA/HSPA + Statistics":
                self.tableHeader = ["Element", "Value"]
            elif self.title == "Data_HSUPA Statistics":
                self.tableHeader = ["Element", "Value"]
            elif self.title == "Data_LTE Data Statistics":
                self.tableHeader = ["Element", "Value", "", ""]
            elif self.title == "Data_LTE Data Line Chart":
                self.tableHeader = ["Element", "Value", "MS", "Color"]
            elif self.title == "Data_Wifi Connected AP":
                self.tableHeader = ["Element", "Value"]
            elif self.title == "Data_Wifi Scanned APs":
                self.tableHeader = [
                    "Time",
                    "BSSID",
                    "SSID",
                    "Freq",
                    "Ch.",
                    "Level",
                    "Encryption",
                ]
            elif self.title == "Data_Wifi Graph":
                return False
            elif self.title == "Data_5G NR Data Line Chart":
                self.tableHeader = ["Element", "Value", "MS", "Color"]

            # Signaling
            elif self.title == "Signaling_Events":
                self.tableHeader = ["Time", "", "Eq.", "Name", "Info."]
                self.tablename = "events"
                self.dataList = SignalingDataQuery(
                    gc.azenqosDatabase, gc.currentDateTimeString
                ).getEvents()

            elif self.title == "Signaling_Layer 1 Messages":
                self.tableHeader = ["Time", "", "Eq.", "Name", "Info."]
                self.tablename = "events"
                self.dataList = SignalingDataQuery(
                    gc.azenqosDatabase, gc.currentDateTimeString
                ).getLayerOneMessages()
            elif self.title == "Signaling_Layer 3 Messages":
                self.tableHeader = ["Time", "", "Eq.", "Protocol", "Name", "Detail"]
                self.tablename = "signalling"
                self.dataList = SignalingDataQuery(
                    gc.azenqosDatabase, gc.currentDateTimeString
                ).getLayerThreeMessages()
            elif self.title == "Signaling_Benchmark":
                self.tableHeader = ["", "MS1", "MS2", "MS3", "MS4"]
                # self.tablename = 'signalling'
                self.dataList = SignalingDataQuery(
                    gc.azenqosDatabase, gc.currentDateTimeString
                ).getBenchmark()
            elif self.title == "Signaling_MM Reg States":
                self.tableHeader = ["Element", "Value"]
                self.tablename = "mm_state"
                self.dataList = SignalingDataQuery(
                    gc.azenqosDatabase, gc.currentDateTimeString
                ).getMmRegStates()
            elif self.title == "Signaling_Serving System Info":
                self.tableHeader = ["Element", "Value"]
                self.tablename = "serving_system"
                self.dataList = SignalingDataQuery(
                    gc.azenqosDatabase, gc.currentDateTimeString
                ).getServingSystemInfo()
            elif self.title == "Signaling_Debug Android/Event":
                self.tableHeader = ["Element", "Value"]
                # self.tablename = 'serving_system'
                self.dataList = SignalingDataQuery(
                    gc.azenqosDatabase, gc.currentDateTimeString
                ).getDebugAndroidEvent()

            if not self.dataList or self.title not in [
                "Signaling_Events",
                "Signaling_Layer 1 Messages",
                "Signaling_Layer 3 Messages",
            ]:
                self.queryFromSchema()

            else:
                self.setTableModel(self.dataList)

            if self.dataList is not None:
                # self.setTableModel(self.dataList)
                self.tableViewCount = self.tableView.model().rowCount()

            # if self.tablename and self.tablename != "":
            #     global gc.tableList
            #     if not self.tablename in gc.tableList:
            #         gc.tableList.append(self.tablename)

    # def mousePressEvent(self, QMouseEvent):
    #     if QMouseEvent.button() == Qt.LeftButton:
    #         pass
    #     elif QMouseEvent.button() == Qt.RightButton:
    #         self.generateMenu

    def initializeQuerySchema(self, elementDict):
        # [table,value,row,column]
        activeSchema = []
        extraRow = 0
        filteredRow = list(
            filter(
                lambda elem: "name" in elem and "column" in elem and "table" in elem,
                elementDict,
            )
        )
        self.columns = len(self.tableHeader)
        self.rows = len(filteredRow)
        for row, element in enumerate(elementDict):
            if "tableRow" in element and "tableCol" in element:
                if "name" in element:
                    rowTitle = {
                        "row": element["tableRow"],
                        "column": element["tableCol"],
                        "text": element["name"],
                    }
                    self.customData.append(rowTitle)
                else:
                    activeSchema.append(
                        {
                            "table": element["table"],
                            "field": element["column"][0],
                            "row": element["tableRow"],
                            "column": element["tableCol"],
                        }
                    )
                extraRow += 1

            else:
                shiftRight = 0
                shiftLeft = 0
                if "shiftRight" in element:
                    shiftRight = element["shiftRight"]
                if "shiftLeft" in element:
                    shiftLeft = element["shiftLeft"]
                totalShift = shiftRight - shiftLeft
                if not totalShift < 0:
                    rowTitle = {
                        "row": row - extraRow,
                        "column": 0 + totalShift,
                        "text": element["name"],
                    }
                    self.customData.append(rowTitle)

                for column, item in enumerate(element["column"]):
                    if not (totalShift + column + 1) < 0:
                        activeSchema.append(
                            {
                                "table": element["table"],
                                "field": item,
                                "row": row - extraRow,
                                "column": column + 1 + totalShift,
                            }
                        )

        return activeSchema

    def queryFromSchema(self):
        self.dataList = []
        for r in range(self.rows):
            content = []
            for c in range(self.columns):
                content.append("")
            self.dataList.append(content)

        result = CustomizeQuery(
            gc.azenqosDatabase, self.appliedSchema, self, gc.currentDateTimeString
        ).query()
        for data in result:
            self.dataList[data[1]][data[2]] = data[0]

        self.updateTable()

    def setHeader(self, headers):
        # self.tableHeader = headers
        self.customHeader = headers
        self.updateTable()
        # self.filterHeader.setFilterBoxes(len(self.tableHeader), self)

    def generateMenu(self, pos):
        menu = QMenu()
        item1 = menu.addAction(u"Customize")
        action = menu.exec_(self.mapToGlobal(pos))
        if action == item1:
            self.properties_window.customData = self.customData
            self.properties_window.customSchema = self.appliedSchema
            self.properties_window.tempHeader = self.customHeader
            self.properties_window.data_set = self.dataList
            self.properties_window.headers = self.tableHeader
            self.properties_window.setupUi()
            self.properties_window.setupComboBox()
            self.properties_window.show()

    def hilightRow(self, sampledate):
        # QgsMessageLog.logMessage('[-- Start hilight row --]', tag="Processing")
        # start_time = time.time()
        worker = None
        self.dateString = str(sampledate)
        # self.findCurrentRow()
        if not self.dataList or self.title not in [
            "Signaling_Events",
            "Signaling_Layer 1 Messages",
            "Signaling_Layer 3 Messages",
        ]:
            worker = Worker(self.queryFromSchema())
        else:
            worker = Worker(self.findCurrentRow())

        if worker:
            gc.threadpool.start(worker)
        # elapse_time = time.time() - start_time
        # del worker
        # QgsMessageLog.logMessage('Hilight rows elapse time: {0} s.'.format(str(elapse_time)), tag="Processing")
        # QgsMessageLog.logMessage('[-- End hilight row --]', tag="Processing")

    def showDetail(self, item):
        parentWindow = self.parentWindow.parentWidget()
        if self.tablename == "signalling":
            item = item.siblingAtColumn(5)
        cellContent = str(item.data())
        self.detailWidget = DetailWidget(parentWindow, cellContent)

    def updateSlider(self, item):
        cellContent = str(item.data())
        timeCell = None
        try:
            timeCell = datetime.datetime.strptime(
                str(cellContent), "%Y-%m-%d %H:%M:%S.%f"
            ).timestamp()
        except Exception as e:
            # if current cell is not Time cell
            headers = [item.lower() for item in self.tableHeader]
            try:
                columnIndex = headers.index("time")
            except Exception as e2:
                columnIndex = -1
            if not columnIndex == -1:
                timeItem = item.siblingAtColumn(columnIndex)
                cellContent = str(timeItem.data())
                try:
                    timeCell = datetime.datetime.strptime(
                        str(cellContent), "%Y-%m-%d %H:%M:%S.%f"
                    ).timestamp()
                except:
                    timeCell = None
            else:
                timeCell = timeCell
        finally:
            if timeCell is not None:
                sliderValue = timeCell - gc.minTimeValue
                sliderValue = round(sliderValue, 3)
                gc.timeSlider.setValue(sliderValue)

    def findCurrentRow(self):
        startRange = 0
        indexList = []
        timeDiffList = []

        if self.currentRow and gc.isSliderPlay == True:
            startRange = self.currentRow

        for row in range(0, self.tableViewCount):
            index = self.tableView.model().index(row, 0)
            value = self.tableView.model().data(index)
            if Utils().datetimeStringtoTimestamp(value):
                gc.currentTimestamp = datetime.datetime.strptime(
                    self.dateString, "%Y-%m-%d %H:%M:%S.%f"
                ).timestamp()
                timestamp = datetime.datetime.strptime(
                    value, "%Y-%m-%d %H:%M:%S.%f"
                ).timestamp()
                if timestamp <= gc.currentTimestamp:
                    indexList.append(row)
                    timeDiffList.append(abs(gc.currentTimestamp - timestamp))

        if not len(timeDiffList) == 0:
            if indexList[timeDiffList.index(min(timeDiffList))] < self.tableViewCount:
                currentTimeindex = indexList[timeDiffList.index(min(timeDiffList))]
                self.tableView.selectRow(currentTimeindex)
        else:
            currentTimeindex = 0
            self.tableView.selectRow(currentTimeindex)
        self.currentRow = currentTimeindex

    def closeEvent(self, QCloseEvent):
        indices = [i for i, x in enumerate(gc.openedWindows) if x == self]
        for index in indices:
            gc.openedWindows.pop(index)
        # if self.tablename and self.tablename in gc.tableList:
        #     gc.tableList.remove(self.tablename)
        self.close()
        del self


class DetailWidget(QDialog):
    def __init__(self, parent, detailText):
        super().__init__(None)
        self.title = "Detail"
        self.detailText = detailText
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.setupUi()

    def setupUi(self):
        self.setObjectName(self.title)
        self.setWindowTitle(self.title)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.textEdit = QTextEdit()
        self.textEdit.setPlainText(self.detailText)
        self.textEdit.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.textEdit)
        self.setLayout(layout)
        self.show()
        self.raise_()
        self.activateWindow()


class TableModel(QAbstractTableModel):
    def __init__(self, inputData, header, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.headerLabels = header
        self.dataSource = inputData
        # self.testColumnValue()

    def rowCount(self, parent):
        rows = 0
        if self.dataSource:
            rows = len(self.dataSource)
        return rows

    def columnCount(self, parent):
        columns = 0
        if self.headerLabels:
            columns = len(self.headerLabels)
        return columns

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            row = index.row()
            column = index.column()
            return "{}".format(self.dataSource[row][column])
        else:
            return None

    def dataString(self, index):
        return self.dataSource[index.row()][index.column()]

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headerLabels[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)


class CustomizeQuery:
    def __init__(self, database, inputData: list, window, globalTime: str):
        self.db = database
        self.inputData = inputData[:]
        self.tableWindow = window
        self.globalTime = globalTime
        self.allSelectedColumns = []
        self.queryString = []
        self.queryTable = []

    def split(self, arr, size):
        arrs = []
        while len(arr) > size:
            pice = arr[:size]
            arrs.append(pice)
            arr = arr[size:]
        arrs.append(arr)
        return arrs

    def query(self):
        MAX_INGROUP = 64
        self.allSelectedColumns = []
        self.queryString = []
        self.queryTable = []
        uniqueTables = []
        condition = ""
        result = []
        # inputdata = ['table','field','row',column']

        for item in self.inputData:
            if item["table"] == "global_time":
                self.tableWindow.dataList[item["row"]][
                    item["column"]
                ] = gc.currentDateTimeString
                self.inputData.remove(item)
                break

        key_func = lambda x: x["table"]
        self.inputData = sorted(self.inputData, key=key_func)
        self.groupedSchema = [list(j) for i, j in groupby(self.inputData, key_func)]

        for group in self.groupedSchema:
            if len(group) > MAX_INGROUP:
                oldIndex = self.groupedSchema.index(group)
                tempGroups = self.split(group, MAX_INGROUP)
                self.groupedSchema.remove(group)
                for newIndex, newGroup in enumerate(tempGroups):
                    self.groupedSchema.insert(newIndex + oldIndex, newGroup)
        pass

        for tableIndex, schema in enumerate(self.groupedSchema):

            if self.globalTime:
                condition = "WHERE time <= '%s'" % (self.globalTime)

            selectedColumns = []
            uniqueColumns = []
            thirdLvSub = []
            tableData = None
            for uniqueCol, data in enumerate(schema):
                if len(data["field"]) > 0:
                    selectedColumns.append(data["field"])
                    uniqueColumns.append(data["field"] + "_%d" % uniqueCol)
                    if not tableData:
                        tableData = data["table"]
                        self.queryTable.append(tableData)
                        uniqueTables.append(tableData + "_%d" % tableIndex)
                else:
                    schema.remove(data)
                    continue
            self.allSelectedColumns += uniqueColumns

            for indexCol, col in enumerate(selectedColumns):
                innerSubQuery = (
                    " IFNULL(( SELECT %s FROM %s %s ORDER BY time DESC LIMIT 1),NULL) AS %s "
                    % (col, tableData, condition, uniqueColumns[indexCol])
                )
                thirdLvSub.append(innerSubQuery)

            uniqueColumns = ",".join(uniqueColumns)
            fullSubQuery = "(SELECT %s)" % (",".join(thirdLvSub))
            queryString = "( SELECT * FROM %s LIMIT 1 ) %s " % (
                fullSubQuery,
                uniqueTables[tableIndex],
            )
            if not tableIndex == 0:
                queryString = ", %s " % (queryString)

            self.queryString.append(queryString)

        columnString = ",".join(self.allSelectedColumns)
        joinString = " ".join(self.queryString)
        queryAll = "SELECT %s FROM  %s" % (columnString, joinString)

        if not self.db.isOpen():
            self.db.open()

        query = QSqlQuery()
        query.exec_(queryAll)
        field_key = lambda x: x["field"]
        if query.first():
            for i in range(len(self.inputData)):
                output = [
                    str(query.value(i)),
                    self.inputData[i]["row"],
                    self.inputData[i]["column"],
                ]
                result.append(output)
        else:
            for i in range(len(self.inputData)):
                output = ["", self.inputData[i]["row"], self.inputData[i]["column"]]
                result.append(output)
        self.db.close()

        return result
