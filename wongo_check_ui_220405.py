# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import datetime
import paramiko
import json
#import pymysql
import threading
#import pandas
import configparser
import hashlib
import requests
import shutil
from collections import OrderedDict
import subprocess
from bs4 import BeautifulSoup
import pyperclip

from PyQt5 import uic
#from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWidgets import QTableWidget

from PyQt5.QtWidgets import QHBoxLayout

__author__ = '이광헌'
__registration_date__   = '220317'
__latest_update_date__  = '220404'
__version__ = 'ver 1.0'
__program_name__ = '내부/외부 원고 중복 확인 및 처리'


#main_window = uic.loadUiType("mainWindow.ui")[0]
debugFlag = True
#debugFlag = False

uifile_1 = 'mainWindow.ui'
main_window, base_1 = uic.loadUiType(uifile_1)

uifile_2 = 'subWindow.ui'
sub_window, window2 = uic.loadUiType(uifile_2)

# class ------------------------ #QMainWindow
class MyWindowClass(QMainWindow, main_window):
    signal_search_send_th1 = pyqtSignal(str)

    def __init__(self, parent=None):

        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.checked_list = []
        self.aws_ip = []
        self.searchWongoList = []
        #self.backupAwsist = []
        self.searchWongoType = ""
        self.inLogFile  = ""
        self.inLogFile1 = ""
        self.inLogFile2 = ""
        self.outLogFile = ""
        self.dup_content = []  # 선택원고의 중복 내용
        self.in_dup_list = []
        self.subWindow = None

        # 내부원고 기본선택
        #self.btn_radio_1.setChecked(True)

        # table
        self.table1_columns = 7
        self.table1.setColumnCount(7)
        self.table1.setHorizontalHeaderLabels(["", "원고 종류", "검사일", "제출 원고", "비교 원고", "중복 개수", "결과"])

        self.table1.setEditTriggers(QTableWidget.NoEditTriggers) # not edit

        self.table1.setSortingEnabled(False)
        self.table1.setColumnWidth(0, 15)
        self.table1.setColumnWidth(1, 70)
        self.table1.setColumnWidth(2, 100)
        self.table1.setColumnWidth(3, 340)
        self.table1.setColumnWidth(4, 340)
        self.table1.setColumnWidth(5, 70)
        self.table1.setColumnWidth(6, 80)
        self.table1.itemClicked.connect(self.tableItemClicked)
        self.table1.doubleClicked.connect(self.tableDoubleClicked)
        self.table1.keyPressEvent = self.tableKeyPressEvent

        # click button
        self.btn_wogoSearch.clicked.connect(self.wogoSearchDate)
        self.input_find.returnPressed.connect(self.wongoFind)
        self.btn_find.clicked.connect(self.wongoFind)
        #self.btn_wogoSearch.keyPressEvent = self.wogoSearchKeyPressEvent

        #self.btn_backup_action.clicked.connect(self.backupAction)
        self.btn_wongoMove.clicked.connect(self.normalWongoMove)  # 정상 원고 이동
        self.btn_asRequest.clicked.connect(self.wongo_asRequest)  # AS 요청
        self.btn_wongoDupListAll.clicked.connect(self.wongoDupListAll)  # 중복 내역 전체 보기
        self.btn_textAreaClear.clicked.connect(self.textAreaClear)  # 중복 내역 지우기
        self.btn_wongoDupListSelected.clicked.connect(self.wongoDupListSelected)  # 중복 내역 전체 보기

        self.logMessageBox.setReadOnly(True)

        # set the title
        self.setWindowTitle('{} {}'.format(__program_name__, __version__))
        self.setGeometry(50, 100, 1100, 900)

    # 중복 내역 Clear
    def textAreaClear(self):
        print('textAreaClear')
        self.logMessageBox.clear()

    # 중복 내역 선택 보기
    def wongoDupListSelected(self):
        selectedList = self.table1.selectedIndexes()
        selectSeqList = []
        for i, rowItem in enumerate(selectedList):
            colNum = rowItem.column()
            if colNum != 5 : continue
            rowNum = rowItem.row()
            #if debugFlag : print('{} / {} : {}'.format(i+1, rowNum, colNum))
            dupWongoData = self.searchWongoList[rowNum]
            selectSeqList.append(dupWongoData['검사결과번호'])

        json_data = OrderedDict()
        json_data['seqList'] = selectSeqList
        jsonData = json.dumps(json_data, ensure_ascii=False)
        if debugFlag: print('jsonData : {}'.format(jsonData))

        postData = {'action': 'get_dupList_action', 'dupSeqList': jsonData}
        debugLogSave('wongoDupListAll >> 중복 내역 요청 >> {}'.format(postData))
        res = requests.post(serverURL, data=postData)
        debugLogSave('wongoDupListAll >> 중복 내역 요청 >> res.text : {}'.format(res.text))
        jsonData = res.json()  # json.load(res.text)
        debugLogSave('wongoDupListAll >> 중복 내역 요청 >> jsonData : {}'.format(jsonData))
        dataCount = jsonData['count']
        dataList = jsonData['data']
        if debugFlag: print('dataCount : {}'.format(dataCount))

        for i, line in enumerate(dataList):
            dupList = ''
            dupCount = 0
            req_file = line['req_file']
            dup_file = line['dup_file']
            checkLine = []
            for j, dupData in enumerate(line['dup_list']):
                dupData = str(dupData).rstrip()
                #if debugFlag: print('j {} > dupData : {} > checkLine : {}'.format(j + 1, dupData, checkLine))
                checkLine.append(dupData)
                # if dupData not in checkLine:
                #    checkLine.append(dupData)
                # else: continue
                dupCount += 1
            dupList = '\n'.join(checkLine)
            dupWongoInfo = '{}\t{}\t{}\n{}\n'.format(req_file, dup_file, dupCount, dupList)
            if debugFlag: print('i {} > {}'.format(i + 1, dupWongoInfo))
            self.logOutput(dupWongoInfo)


    # 중복 내역 전체 보기
    def wongoDupListAll(self):
        print('wongoDupListAll')
        tableCount = self.table1.rowCount()
        if tableCount == 0 :
            QMessageBox.critical(self, "Noti", "원고 검색 결과가 없습니다.\n")
            return
        seqList = []
        #if debugFlag : print('self.searchWongoList : {}'.format(self.searchWongoList))
        for rowNum in range(tableCount) :
            dupWongoData = self.searchWongoList[rowNum]
            seqList.append(dupWongoData['검사결과번호'])
        if debugFlag : print('seqList : {}'.format(seqList))

        json_data = OrderedDict()
        json_data['seqList'] = seqList
        jsonData = json.dumps(json_data, ensure_ascii=False)
        if debugFlag : print('jsonData : {}'.format(jsonData))

        postData = {'action': 'get_dupList_action', 'dupSeqList':jsonData}
        debugLogSave('wongoDupListAll >> 중복 내역 요청 >> {}'.format(postData))
        res = requests.post(serverURL, data=postData)
        debugLogSave('wongoDupListAll >> 중복 내역 요청 >> res.text : {}'.format(res.text))
        jsonData = res.json()#json.load(res.text)
        debugLogSave('wongoDupListAll >> 중복 내역 요청 >> jsonData : {}'.format(jsonData))
        dataCount= jsonData['count']
        dataList = jsonData['data']
        if debugFlag: print('dataCount : {}'.format(dataCount))

        for i, line in enumerate(dataList) :
            dupList = ''
            dupCount = 0
            req_file = line['req_file']
            dup_file = line['dup_file']
            checkLine = []
            for j, dupData in enumerate(line['dup_list']) :
                dupData = str(dupData).rstrip()
                if debugFlag : print('j {} > dupData : {} > checkLine : {}'.format(j+1, dupData, checkLine))
                checkLine.append(dupData)
                #if dupData not in checkLine:
                #    checkLine.append(dupData)
                #else: continue
                dupCount += 1
            dupList = '\n'.join(checkLine)
            dupWongoInfo = '{}\t{}\t{}\n{}\n'.format(req_file, dup_file, dupCount, dupList)
            if debugFlag : print('i {} > {}'.format(i+1, dupWongoInfo))
            self.logOutput(dupWongoInfo)

    # AS 요청
    def wongo_asRequest(self):
        global asURL

        if debugFlag : print('원고 AS 요청 ------------------------')
        tableCount = self.table1.rowCount()
        if tableCount <= 0 :
            QMessageBox.critical(self, "Noti", "원고 검색 결과가 없습니다.\n")
            return
        as_total_count = len(self.checked_list)
        if as_total_count <= 0 :
            QMessageBox.critical(self, "Noti", "AS 요청할 원고를 선택하세요.\n")
            return

        answer = QMessageBox.question(self, 'Noti', '체크한 원고를 AS 요청 하겠습니까? ',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.No:
            return # event.ignore()

        as_file_list = []
        json_data = OrderedDict()

        if debugFlag : print('self.checked_list : {}'.format(self.checked_list))

        for rowNum in self.checked_list :
            wongo_file = self.table1.item(rowNum, 3).text().replace(".txt","")
            if wongo_file not in as_file_list :
                as_file_list.append(wongo_file)

        as_file_count = len(as_file_list)
        debugLogSave('AS요청 파일목록 {} : {}'.format(as_file_count, as_file_list))

        json_data['fileList'] = as_file_list
        debugLogSave('as_file_list : {}\njson_data : {}'.format(as_file_list, json_data))
        sendJsonData = json.dumps(json_data, ensure_ascii=False)
        #sendJsonData = json.dumps(json_data, ensure_ascii=False, indent="\t")
        #sendJsonData = json.dumps(json_data)
        if debugFlag : print('sendJsonData : {}'.format(sendJsonData))

        postData = {'AS_Data': sendJsonData}
        if debugFlag : print('postData : {}'.format(postData))
        ##input('enter >> ')
        #res = requests.get(URL, params=postData)
        res = requests.post(asURL, data=postData)
        debugLogSave('wongo_asRequest >> res.text : {}'.format(res.text))

        jsonObject = json.loads(res.text)
        successCount  = jsonObject['successCount']
        asSuccessList = jsonObject['successList']
        errorCount    = jsonObject['errorCount']
        asErrorList   = jsonObject['errorList']

        if debugFlag : print('as request success : {}'.format(asSuccessList))
        #debugLogSave('wongo_asRequest >> asURL : {}'.format(asURL))
        debugLogSave('wongo_asRequest >> jsonObject : {}'.format(jsonObject))

        if int(errorCount) > 0 :
            QMessageBox.warning(self, "Warning", "원고 AS 요청 결과 ( 총 {} 개 )\n성공 : {} 개\n오류 : {} 개\nAS오류 : {}\n".format(as_total_count, successCount, errorCount, ','.join(asErrorList)))
        elif int(successCount) > 0 :
            QMessageBox.information(self, "Noit", "원고 AS 요청 결과 ( 총 {} 개 )\n성공 :  {} 개\n".format(as_total_count, successCount))

        outputLogSave("원고 AS 요청 결과 ( 총 {} 개 ) >> 성공 : {} 개 >> 성공 리스트 : {}".format(as_total_count, successCount, asSuccessList))
        outputLogSave("원고 AS 요청 결과 ( 총 {} 개 ) >> 오류 : {} 개 >> AS오류 : {}".format(as_total_count, errorCount, asErrorList))

        sendDataList = []
        try:
            # AS요청 성공 : 색상변경 및 체크박스 unchecked
            if int(successCount) > 0 :
                rowList = self.findWongoRow(asSuccessList)
                #self.logOutput('AS요청 성공 : {}'.format(','.join(asSuccessList)))
                errorList = []
                for rowNum in rowList:
                    self.table1.setItem(rowNum, 6, QTableWidgetItem('AS요청'))
                    self.table1.item(rowNum, 6).setTextAlignment(Qt.AlignCenter)
                    wongo_type = self.table1.item(rowNum, 1).text()
                    req_file = self.table1.item(rowNum, 3).text()

                    for col in range(self.table1_columns):
                        cell = self.table1.item(rowNum, col)
                        cell.setBackground(QColor(245, 169, 169))
                    try:
                        self.checked_list.remove(rowNum)
                    except Exception as e :
                        errorLogSave('wongo_asRequest >> self.checked_list.remove({}) >> {}'.format(rowNum, e))

                    checkBox = self.table1.item(rowNum, 0)
                    checkBox.setCheckState(0)

                    # 220328
                    dupWongoData = self.searchWongoList[rowNum]
                    if debugFlag: print('wongo_asRequest >> dupWongoData : {}'.format(dupWongoData))

                    dup_result_no = dupWongoData['검사결과번호']
                    req_wongo = dupWongoData['검사원고']
                    tempA = {'wongo_no': dup_result_no, 'wongo_file': req_wongo}
                    sendDataList.append(tempA)
                    if debugFlag : print('wongo_asRequest >> D1> sendDataList : {}'.format(sendDataList))

                    # AS요청 성공 원고 삭제 기능
                    del_file_path = ''
                    if wongo_type == '내부원고' :
                        del_file_path = in_wongo_folder
                    elif wongo_type == '외부원고' :
                        del_file_path = out_wongo_folder

                    deleteFile = del_file_path + req_file
                    debugLogSave('AS요청 완료 >> file delete >> {}'.format(deleteFile))
                    if not os.path.isfile(deleteFile):
                        errorList.append(deleteFile)
                        #self.logOutput_Error('파일을 찾을 수 없습니다. >> {}'.format(deleteFile))
                        errorLogSave('파일을 찾을 수 없습니다. >> {}'.format(deleteFile))
                        continue
                    try:
                        #self.checked_list.remove(rowNum)
                        os.remove(deleteFile)
                        #self.logOutput('파일삭제 완료 : {}'.format(req_file))
                        outputLogSave('파일삭제 완료 : {}'.format(req_file))
                    except Exception as e:
                        errorList.append(deleteFile)
                        #self.logOutput_Error('파일 삭제 오류 >> {} >> {}'.format(deleteFile, e))
                        errorLogSave('파일 삭제 오류 >> {} >> {}'.format(deleteFile, e))

                if debugFlag: print('normalWongoMove >> D2> sendDataList : {}'.format(sendDataList))

                # AS요청 DB 처리 220328
                wongoData = {'wongoWork': 'AS요청', 'wongoListCount': len(sendDataList), 'wongoList': sendDataList}
                jsonData = json.dumps(wongoData, ensure_ascii=False)

                postData = {'action': 'wongo_confirm_action', 'confirmWongoData': jsonData}
                debugLogSave('wongo_asRequest >> AS원고 DB처리 >> {}'.format(postData))
                res = requests.post(serverURL, data=postData)
                debugLogSave('wongo_asRequest >> AS원고 DB처리 >> res.text : {}'.format(res.text))


                '''
                # AS요청 성공 원고 삭제 기능  old
                tempArray = []
                for file in asSuccessList :
                    for line in self.in_dup_list:
                        if str(line).startswith(file+".txt"):
                            pass
                        else:
                            tempArray.append(line)
                    self.in_dup_list = tempArray

                debugLogSave('wongo_asRequest >> self.in_dup_list : {}'.format(self.in_dup_list))
                '''
            if int(errorCount) > 0 :
                #self.logOutput_Error('AS요청 오류 >> {}'.format(','.join(asErrorList)))
                errorLogSave('AS요청 오류 >> {}'.format(','.join(asErrorList)))

            if len(errorList) > 0 :
                errorFile = '\n'.join(errorList)
                errMessage = "파일을 찾을 수 없습니다.\n{}\n".format(errorFile)
                QMessageBox.critical(self, "Error", errMessage)

        except Exception as e :
            errorLogSave('wongo_asRequest >> Exception : {}'.format(e))

        self.checked_list = []
        self.all_unChecked()

        #self.inDupInfoSave()

        # 로그파일에 AS요청 공라인 as요청시간 추가
        # self.inDupInfoAsSave(asSuccessList)

    # 로그 출력
    def logOutput(self, msg):
        colorvar = QColor(0, 0, 0)
        self.logMessageBox.setTextColor(colorvar)
        self.logMessageBox.append('{}'.format(msg))
        outputLogSave(msg)

    def logOutput_Error(self, msg):
        colorvar = QColor(255,0,0)
        self.logMessageBox.setTextColor(colorvar)
        self.logMessageBox.append('{}'.format(msg))
        errorLogSave(msg)

    def all_unChecked(self):
        checkState = 0
        try:
            for rowNum in range(table1):
                checkBox = self.table1.item(rowNum, 0)
                #checkState1 = checkBox.checkState()
                checkBox.setCheckState(checkState)
        except Exception as e :
            errorLogSave('all_unChecked >> exception : {}'.format(e))

    # 정상 원고 이동
    def normalWongoMove(self):
        global use_wongo_Folder, wongo_Folder, in_wongo_folder, out_wongo_folder

        if debugFlag : print('정상 원고 이동 ------------------------')
        tableCount = self.table1.rowCount()
        if tableCount <= 0 :
            QMessageBox.critical(self, "Noti", "원고 검색 결과가 없습니다.\n")
            return

        move_total_count = len(self.checked_list)
        if move_total_count <= 0 :
            QMessageBox.critical(self, "Noti", "이동할 원고를 선택하세요.\n")
            return

        answer = QMessageBox.question(self, 'Noti', '정상 원고 이동하겠습니까? ( 복구할 수 없습니다. )',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.No: return #event.ignore()


        move_file_list = []
        move_success = 0
        move_error = 0
        move_error_list = []


        check_data = []
        sendDataList = []
        checkCount = len(self.checked_list)
        for rowNum in self.checked_list :
            wongo_file = self.table1.item(rowNum, 3).text()
            colData2 = self.table1.item(rowNum, 4).text()
            colData3 = self.table1.item(rowNum, 5).text()
            check_data.append('{}\t{}\t{}'.format(wongo_file, colData2, colData3))
            if wongo_file not in move_file_list :
                move_file_list.append(wongo_file)


        debugLogSave('normalWongoMove >> check_data : {}'.format(check_data))
        debugLogSave('move_file_list {} : {}'.format(len(move_file_list), move_file_list))

        debugLogSave('원고이동 : {}'.format(move_file_list))
        if debugFlag : print('checked_list : {}'.format(self.checked_list))

        rowList = self.findWongoRowNormal(move_file_list)
        if debugFlag : print('rowList : {}'.format(rowList))
        #for move_file in move_file_list :
        #for rowNum in self.checked_list :
        moveSuccessList = []
        for rowNum in rowList :
            move_file = self.table1.item(rowNum, 3).text()
            try:
                if debugFlag : print('moveSuccessList : {}'.format(moveSuccessList))
                if move_file in moveSuccessList :
                    dupWongoData = self.searchWongoList[rowNum]
                    if debugFlag: print('dupWongoData : {}'.format(dupWongoData))

                    dup_result_no = dupWongoData['검사결과번호']
                    req_wongo = dupWongoData['검사원고']
                    tempA = {'wongo_no': dup_result_no, 'wongo_file': req_wongo}
                    sendDataList.append(tempA)
                    if debugFlag : print('D1> sendDataList : {}'.format(sendDataList))

                    #self.checked_list.remove(rowNum)
                    try:
                        self.checked_list.remove(rowNum)
                    except Exception as e :
                        errorLogSave('normalWongoMove >> self.checked_list.remove({}) >> {}'.format(rowNum, e))

                    self.table1.setItem(rowNum, 6, QTableWidgetItem('정상원고'))
                    self.table1.item(rowNum, 6).setTextAlignment(Qt.AlignCenter)

                    for col in range(self.table1_columns):
                        cell = self.table1.item(rowNum, col)
                        # cell.setBackground(QColor(135, 206, 235))
                        cell.setBackground(QColor(176, 224, 230))
                    checkBox = self.table1.item(rowNum, 0)
                    checkBox.setCheckState(0)
                    continue

                filePath = out_wongo_folder
                searchWongoType = self.table1.item(rowNum, 1).text()
                if searchWongoType == "내부원고":
                    filePath = in_wongo_folder

                wongo_move_file = filePath + move_file
                if os.path.isfile(wongo_move_file) :
                    # 원고이동
                    shutil.move(wongo_move_file, use_wongo_Folder)
                    outputLogSave('원고 이동 완료 >> {} ==> {}'.format(wongo_move_file, use_wongo_Folder))
                    #self.logOutput('정상원고 이동 완료 : {}'.format(move_file))
                    outputLogSave('정상원고 이동 완료 : {}'.format(move_file))
                    move_success += 1

                    # 220325
                    dupWongoData = self.searchWongoList[rowNum]
                    if debugFlag: print('dupWongoData : {}'.format(dupWongoData))

                    dup_result_no = dupWongoData['검사결과번호']
                    req_wongo = dupWongoData['검사원고']
                    tempA = {'wongo_no': dup_result_no, 'wongo_file': req_wongo}
                    sendDataList.append(tempA)
                    if debugFlag : print('D1> sendDataList : {}'.format(sendDataList))

                    self.table1.setItem(rowNum, 6, QTableWidgetItem('정상원고'))
                    self.table1.item(rowNum, 6).setTextAlignment(Qt.AlignCenter)

                    for col in range(self.table1_columns):
                        cell = self.table1.item(rowNum, col)
                        # cell.setBackground(QColor(135, 206, 235))
                        cell.setBackground(QColor(176, 224, 230))
                    checkBox = self.table1.item(rowNum, 0)
                    checkBox.setCheckState(0)
                    moveSuccessList.append(move_file)

                else :
                    #self.logOutput_Error('이동 오류 >> 파일없음 >> {}'.format(wongo_move_file))
                    errorLogSave('이동 오류 >> 파일없음 >> {}'.format(wongo_move_file))
                    #errorLogSave('파일없음 >> {}'.format(wongo_move_file))
                    move_error += 1
                    move_error_list.append(move_file)
            except Exception as e:
                #self.logOutput_Error('{} >> 원고이동 오류 : {}'.format(move_file, e))
                errorLogSave('{} >> 원고이동 오류 : {}'.format(move_file, e))
                #errorLogSave('{} >> 원고이동 오류 : {}'.format(move_file, e))
                move_error += 1
                move_error_list.append(move_file)

        if debugFlag: print('normalWongoMove >> D2> sendDataList : {}'.format(sendDataList))
        if len(move_error_list) > 0 :
            debugLogSave('move_error_list >> {}'.format(move_error_list))

        # 정상원고 DB 처리 220325
        wongoData = {'wongoWork': '정상원고', 'wongoListCount': len(sendDataList), 'wongoList': sendDataList}
        jsonData = json.dumps(wongoData, ensure_ascii=False)

        postData = {'action': 'wongo_confirm_action', 'confirmWongoData':jsonData}
        debugLogSave('normalWongoMove >> 정상원고 DB처리 >> {}'.format(postData))
        res = requests.post(serverURL, data=postData)
        debugLogSave('normalWongoMove >> 정상원고 DB처리 >> res.text : {}'.format(res.text))

        # self.in_dup_list  ??
        #debugLogSave('wongoMove >> self.in_dup_list : {}'.format(self.in_dup_list))
        #self.inDupInfoSave()  # 중복검사결과에서 이동원고 부분 제거후 저장

        if move_error > 0 :
            QMessageBox.warning(self, "Warning", "원고 이동 결과 ( 총 {} 개 )\n성공 : {} 개\n오류 : {} 개\n".format(move_total_count, move_success,move_error))
        elif move_success > 0 :
            QMessageBox.information(self, "Noit", "원고 이동 결과 ( 총 {} 개 )\n성공 :  {} 개\n".format(move_total_count, move_success))

        outputLogSave("원고 이동 결과 ( 총 {} 개 )\n성공 : {} 개\n오류 : {} 개\n".format(move_total_count, move_success,move_error))

        self.checked_list = []
        self.all_unChecked()

    # 로그파일에 AS요청 성공라인 as요청시간 추가
    '''
    def inDupInfoAsSave(self, asFileList):
        # self.in_dup_list 저장
        if debugFlag : print('inDupInfoAsSave ---------------')
        now = datetime.datetime.now()
        asTime = now.strftime('%y-%m-%d %H:%M:%S')
        tempArray = []

        debugLogSave('원고 AS 요청 : {}'.format(asFileList))
        for file in asFileList :
            if debugFlag : print('file : {}'.format(file))
            for line in self.in_dup_list :
                if debugFlag: print('line : {}'.format(line))
                if line.startswith(file) :
                    tempLine = '{}\t{}'.format(line, asTime)
                    if tempLine not in tempArray :
                        tempArray.append(tempLine)
                elif line not in tempArray :
                    tempArray.append(line)
        if debugFlag : print('tempArray : {}'.format(tempArray))
        self.in_dup_list = tempArray

        #self.inDupInfoSave()
    '''
    '''
    def inDupInfoSave(self):
        # self.in_dup_list 저장
        if debugFlag :
            print('inDupInfoSave() ' + '-'*20)
            print('{} 저장 --------------\nself.in_dup_list : {}'.format(self.inLogFile, self.in_dup_list))

        if self.searchWongoType == "내부원고":
            logFile = self.inLogFile
        elif self.searchWongoType == "외부원고":
            logFile = self.outLogFile
        else:
            QMessageBox.critical(self, 'Error', '원고 종류 오류')
            return

        with open(logFile, 'a') as fp:
            for line in self.in_dup_list :
                fp.write('{}\n'.format(line))
    '''

    def findWongoRow(self, wongoList):
        debugLogSave('findWongoRow >> wongoList : {}'.format(wongoList))

        totalRowNum = self.table1.rowCount()
        find_row_list = []
        for rowNum in range(totalRowNum) :
            beforeResult = self.table1.item(rowNum, 6).text()
            if beforeResult != '중복원고' : continue

            req_file = str(self.table1.item(rowNum, 3).text()).replace('.txt','')
            if req_file in wongoList : find_row_list.append(rowNum)

            debugLogSave('findWongoRow >> 원고파일 row {} : {}'.format(req_file, find_row_list))

        debugLogSave('findWongoRow >> find_row_list : {}'.format(find_row_list))
        return find_row_list

    def findWongoRowNormal(self, wongoList):
        debugLogSave('findWongoRowNormal >> wongoList : {}'.format(wongoList))

        totalRowNum = self.table1.rowCount()
        find_row_list = []
        for rowNum in range(totalRowNum) :
            beforeResult = self.table1.item(rowNum, 6).text()
            if beforeResult != '중복원고' : continue

            req_file = str(self.table1.item(rowNum, 3).text())
            if req_file in wongoList : find_row_list.append(rowNum)

            debugLogSave('findWongoRowNormal >> 원고파일 row {} : {}'.format(req_file, find_row_list))

        debugLogSave('findWongoRowNormal >> find_row_list : {}'.format(find_row_list))
        return find_row_list

    # table checkbox check
    def tableItemClicked(self, item):

        colNum = item.column()
        rowNum = item.row()
        itemText = item.text()
        wongoResult = self.table1.item(rowNum, 6).text()

        if colNum == 0 : # checkbox check
            checkBox = self.table1.item(rowNum, 0)
            if debugFlag : print('tableItemClicked >> {} : {} ? {}'.format(rowNum, colNum, checkBox.checkState() ))
            if 'AS요청' in wongoResult or '정상원고' in wongoResult :
                checkBox.setCheckState(0)
                return

            if False : # 빈영역 클릭 처리
                print('D1 > row checked {}'.format(item.checkState()))
                if item.checkState() == Qt.Checked :
                    checkBox.setCheckState(0)
                else :
                    checkBox.setCheckState(2)
                print('D2 > row checked {}'.format(item.checkState()))

            if item.checkState() == Qt.Checked:
                if debugFlag : print('checked %d : "%s" Checked' % (rowNum, itemText))
                self.checked_list.append(rowNum)
                if debugFlag : print('체크 : {}'.format(self.checked_list))

                for col in range(self.table1_columns):
                    cell = self.table1.item(rowNum, col)
                    cell.setBackground(QColor(255, 242, 204))
                    # cell.setBackground(QColor(255, 128, 128))

                # self.table.removeRow(item.row()) # row delete
            else:
                if debugFlag : print('unchecked %d : "%s" Clicked' % (rowNum, itemText))
                for col in range(self.table1_columns):
                    cell = self.table1.item(rowNum, col)
                    cell.setBackground(QColor(255, 255, 255))
                if rowNum in self.checked_list:
                    #self.checked_list.remove(rowNum)
                    try:
                        self.checked_list.remove(rowNum)
                        if debugFlag: print('check List : "%s" ' % (self.checked_list))
                    except Exception as e :
                        errorLogSave('wongo_asRequest >> self.checked_list.remove({}) >> {}'.format(rowNum, e))

    '''
    def wogoSearchKeyPressEvent(self, event):

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            print('wogoSearchKeyPressEvent Enter key press ')
            self.wogoSearchDate()
    '''

    def tableKeyPressEvent(self, event):

        current = self.table1.currentIndex()
        curRow = current.row()
        curCol = current.column()
        #print('table {} : {}'.format(curRow, curCol))

        currentMove = False

        if event.key() == Qt.Key_Down:
            currentMove = True
            nextIndex = current.sibling(curRow + 1, curCol)
        elif event.key() == Qt.Key_Up:
            currentMove = True
            nextIndex = current.sibling(curRow - 1, curCol)
        elif event.key() == Qt.Key_Left:
            currentMove = True
            nextIndex = current.sibling(curRow, curCol - 1)
        elif event.key() == Qt.Key_Right:
            currentMove = True
            nextIndex = current.sibling(curRow, curCol + 1)
        elif event.key() == Qt.Key_C:
            #print('Key C')
            selectedList = self.table1.selectedIndexes()
            #print('selectedList : {}'.format(len(selectedList)))
            copyData = ''
            checkRowNum = 0
            for i, rowItem in enumerate(selectedList):
                colNum = rowItem.column()
                rowNum = rowItem.row()
                #print('{} / {} : {}'.format(i+1, rowNum, colNum))
                data = self.table1.item(rowNum, colNum).text()

                if i == 0 :
                    checkRowNum = rowNum
                #print('rowNum : {} / checkRowNum : {}'.format(rowNum, checkRowNum))
                if copyData == '' :
                    copyData = '{}'.format(data)
                else:
                    if checkRowNum != rowNum:
                        checkRowNum = rowNum
                        copyData = '{}\r\n{}'.format(copyData,data)
                    else:
                        copyData = '{}\t{}'.format(copyData,data)

            #print('copyData : {}'.format(copyData))
            pyperclip.copy(copyData)

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            print('table Enter key press ')
            #nextIndex = current.sibling(curRow + 1, curCol)
            #self.table1.setCurrentIndex(nextIndex)
            curItem = self.table1.item(curRow, curCol)
            self.tableDoubleClicked(curItem)

        '''
        selectedList = self.table1.selectedIndexes()
        selectSeqList = []
        for i, rowItem in enumerate(selectedList):
            colNum = rowItem.column()
            if colNum != 5 : continue
            rowNum = rowItem.row()
            print('{} / {} : {}'.format(i+1, rowNum, colNum))
            dupWongoData = self.searchWongoList[rowNum]
            selectSeqList.append(dupWongoData['검사결과번호'])
        '''

        if currentMove and nextIndex.isValid():
            self.table1.setCurrentIndex(nextIndex)

    def tableDoubleClicked(self, item):

        colNum = item.column()
        rowNum = item.row()
        if debugFlag : print('tableDoubleClicked > colNum {} >> searchWongoType : {}'.format(colNum, self.searchWongoType))
        if colNum == 0 : return

        dupCount = self.table1.item(rowNum, 5).text()
        req_file = self.table1.item(rowNum, 3).text()

        row = self.table1.currentIndex().row()
        #col = self.table1.currentIndex().column()

        dupWongoData = self.searchWongoList[row]
        if debugFlag : print('dupWongoData : {}'.format(dupWongoData))

        wongo_type = dupWongoData['원고종류']
        dup_result_no = dupWongoData['검사결과번호']
        req_wongo = dupWongoData['검사원고']
        dup_wongo = dupWongoData['중복원고']

        #wongo_1 = self.table1.item(row, 1).text()
        #wongo_2 = self.table1.item(row, 2).text()
        if debugFlag :
            print('req_wongo : {}'.format(req_wongo))
            print('dup_wongo : {}'.format(dup_wongo))


        #검사요청원고
        postData = {'action': 'get_wongoData', 'wongoName': req_wongo}
        debugLogSave('tableDoubleClicked >> req_wongo 자료 요청 >> {}'.format(postData))
        res = requests.post(serverURL, data=postData)
        if debugFlag: print('get_wongoData req_wongo >> res.text : {}'.format(res.text))
        jsonData = res.json()#json.load(res.text)
        if debugFlag: print('req_wongo >> jsonData : {}'.format(jsonData))
        req_wongo_title = jsonData['title']
        req_wongo_data  = jsonData['content']
        if req_wongo_data == '' : req_wongo_data = '원고 자료가 없습니다.'
        if debugFlag: print('req_wongo_data : {}'.format(len(req_wongo_data)))

        # 중복확인원고
        postData = {'action': 'get_wongoData', 'wongoName': dup_wongo}
        debugLogSave('tableDoubleClicked >> dup_wongo 자료 요청 >> {}'.format(postData))
        res = requests.post(serverURL, data=postData)
        if debugFlag: print('get_wongoData dup_wongo >> res.text : {}'.format(res.text))
        jsonData = res.json()#json.load(res.text)
        if debugFlag: print('dup_wongo >> jsonData : {}'.format(jsonData))
        dup_wongo_title = jsonData['title']
        dup_wongo_data  = jsonData['content']
        if dup_wongo_data == '' : dup_wongo_data = '원고 자료가 없습니다.'
        if debugFlag: print('dup_wongo_data : {}'.format(len(dup_wongo_data)))

        # 중복 리스트
        postData = {'action': 'get_wongoDupList', 'req_wongo': req_wongo, 'dup_result_no': dup_result_no}
        debugLogSave('tableDoubleClicked >> get_wongoDupList 자료 요청 >> {}'.format(postData))
        res = requests.post(serverURL, data=postData)
        if debugFlag: print('get_wongoDupList >> res.text : {}'.format(res.text))
        jsonData = res.json()  # json.load(res.text)
        if debugFlag: print('get_wongoDupList >> jsonData : {}'.format(jsonData))
        dup_wongoLineList_temp = jsonData['content']
        if debugFlag: print('dup_wongoLineList_temp : {}'.format(dup_wongoLineList_temp))
        dup_wongoLineList = []
        for dupLine in dup_wongoLineList_temp :
            dupLine = str(dupLine).rstrip()
            if dupLine == '' : continue
            dup_wongoLineList.append(dupLine)
            #if dupLine not in dup_wongoLineList :
            #    dup_wongoLineList.append(dupLine)
        if debugFlag: print('dup_wongoLineList : {}'.format(dup_wongoLineList))

        #if int(dupCount) != len(dup_wongoLineList):
        #    QMessageBox.critical(self, "Error", "{}\n\n중복 검사 결과 > 중복목록에 오류가 있습니다. {} / {}".format(req_file, dupCount, len(dup_wongoLineList)))

        self.dup_content = dup_wongoLineList

        if colNum >= 1 and  colNum <= 4 :
            self.subWindow = subWindow(wongo_type, req_wongo, req_wongo_data, dup_wongo, dup_wongo_data, self.dup_content)
            self.subWindow.show()
        if colNum == 5 :
            dupList = ''
            dupListCount = 0
            for i, line in enumerate(dup_wongoLineList) :
                dupList += '{}\n'.format(line)
                dupListCount += 1
            dupList = '{}\t{}\t{}\n{}\n'.format(req_wongo, dup_wongo, dupListCount, dupList)
            #QMessageBox.warning(self, "중복 내역 ".format(dupCount))
            self.logOutput(dupList)


    def in_duplicate_content(self, wongo1, wongo2):

        c_flag = False
        self.dup_content = []

        if debugFlag : print('in_duplicate_content -----------------------')
        if wongo1 == wongo2 :
            if debugFlag : print('wongo1 == wongo2')
            try:
                in_log_list = open(self.inLogFile1).read().splitlines()
            except Exception as e:
                QMessageBox.critical(self, "Noti", "{}\n\n원고 분석 정보 파일이 없습니다.".format(self.inLogFile1))
                return

            for i, line in enumerate(in_log_list) :
                if debugFlag : print('{} in_log_list : {}'.format(i+1, line))
                if line == '': continue
                if line[-1] == ' ' : line = line[:-1]
                if c_flag:
                    if '============' in line or '중복 확인수 :' in line:
                        c_flag = False
                    else:
                        if line not in self.dup_content : self.dup_content.append(line)

                dataSplit = line.split('\t')
                if len(dataSplit) < 2: continue
                data1 = dataSplit[0]
                data2 = dataSplit[1]
                if wongo1 == data1 and '중복 확인수 :' in data2:
                    c_flag = True
        else:
            if debugFlag : print('wongo1 != wongo2\nself.inLogFile2 : {}'.format(self.inLogFile2))
            try:
                in_log_list = open(self.inLogFile2).read().splitlines()
            except Exception as e:
                QMessageBox.critical(self, "Noti", "{}\n\n원고 분석 정보 파일이 없습니다.".format(self.inLogFile2))
                return

            for i, line in enumerate(in_log_list) :
                if debugFlag : print('{} in_log_list : {}'.format(i+1, line))
                if line == '': continue
                if line[-1] == ' ' : line = line[:-1]
                if c_flag:
                    if '중복확인 :' in line:
                        c_flag = False
                    else:
                        if line not in self.dup_content : self.dup_content.append(line)

                dataSplit = line.split('\t')
                if len(dataSplit) < 2: continue
                data1 = dataSplit[0]
                data2 = dataSplit[1]
                if wongo1 == data1 and wongo2 == data2:
                    c_flag = True

        if debugFlag:
            print('in_duplicate_content\n{}\t{}'.format(wongo1, wongo2))
            print('중복 내용 {}\n{}'.format(len(self.dup_content), self.dup_content))


    def out_duplicate_content(self, wongo, url):

        try:
            out_log_list = open(self.outLogFile).read().splitlines()
        except Exception as e:
            QMessageBox.critical(self, "Noti", "{}\n\n원고 분석 정보 파일이 없습니다.".format(self.outLogFile))
            return

        c_flag = False
        self.dup_content = []
        for line in out_log_list :
            if line == '' : continue
            if c_flag :
                if '.txt' in line and 'http' in line :
                    c_flag = False
                else:
                    self.dup_content.append(line)

            dataSplit = line.split('\t')
            if len(dataSplit) < 2 : continue
            data1 = dataSplit[0]
            data2 = dataSplit[1]
            if wongo == data1 and url == data2 :
                c_flag = True
        if debugFlag :
            print('\n{}\t{}'.format(wongo, url))
            print('중복 내용 {}\n{}'.format(len(self.dup_content), self.dup_content))

    def closeEvent(self, QCloseEvent):
        try:
            self.close()
            if self.subWindow != None :
                self.subWindow.close()
                print(' sub_window close ')
        except: pass

    def wogoSearchDate(self):
        global wongo_Folder, in_wongo_folder, out_wongo_folder

        serverURL = 'http://aaa.e-e.kr/article-list/wongoDuplicateCheckAction.php'

        now = datetime.datetime.now()
        curDate = now.strftime('%y%m%d')
        cal_date = self.calendarWidget.selectedDate()
        selectDate = cal_date.toString('yyMMdd')  # QDate 를 str 로 변환
        selectDate2 = cal_date.toString('yyyy-MM-dd')  # QDate 를 str 로 변환
        if debugFlag: print('select Date {}'.format(selectDate))

        postData = {'action': 'get_wongoDupResultList', 'searchDate': selectDate2}
        debugLogSave('wogoSearch >> get_wongoDupResultList 자료 요청 >> {}'.format(postData))
        res = requests.post(serverURL, data=postData)
        if debugFlag: print('res.text : {}'.format(res.text))
        jsonData = res.json()#json.load(res.text)
        if debugFlag: print('jsonData : {}'.format(jsonData))
        dataCount= jsonData['count']
        dataList = jsonData['data']
        if debugFlag: print('dataCount : {}'.format(dataCount))

        if dataCount == 0 :
            QMessageBox.warning(self, "Noti", "{}  원고 중복 검사 자료가 없습니다.".format(selectDate2))
            return

        self.searchWongoList = []
        self.checked_list = []

        #self.searchWongoType = searchWongoType
        #if debugFlag : print('searchWongoType : {}'.format(self.searchWongoType))

        row_count = self.table1.rowCount()
        del_row = row_count
        for num in range(row_count):
            del_row -= 1
            self.table1.removeRow(del_row)  # row delete

        for rowNum, wData in enumerate(dataList) :
            self.searchWongoList.append(wData)
            rowPosition = self.table1.rowCount()
            self.table1.insertRow(rowPosition)

            itemCheckbox = QTableWidgetItem()
            itemCheckbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            itemCheckbox.setCheckState(Qt.Unchecked)

            '''
            # checkbox cell 중앙으로 보이게 처리
            # 참고 : https://curioso365.tistory.com/90
            # 문제 : 체크 변경 > row 배경색 변경
            #       체크 클릭 이벤트 처리 ??
            
            ckbox = QCheckBox()

            cellWidget = QWidget()
            layoutCB = QHBoxLayout(cellWidget)
            layoutCB.addWidget(ckbox)
            layoutCB.setAlignment(Qt.AlignCenter)
            layoutCB.setContentsMargins(0, 0, 0, 0)
            cellWidget.setLayout(layoutCB)
            self.table1.setCellWidget(rowPosition, 0, cellWidget)
            '''
            self.table1.setItem(rowPosition, 0, itemCheckbox)
            self.table1.setItem(rowPosition, 1, QTableWidgetItem(wData['원고종류']))
            self.table1.setItem(rowPosition, 2, QTableWidgetItem(wData['검사일']))
            self.table1.setItem(rowPosition, 3, QTableWidgetItem(wData['검사원고']))
            self.table1.setItem(rowPosition, 4, QTableWidgetItem(wData['중복원고']))
            self.table1.setItem(rowPosition, 5, QTableWidgetItem(wData['중복수']))
            self.table1.setItem(rowPosition, 6, QTableWidgetItem(wData['업무처리']))
            self.table1.item(rowPosition, 1).setTextAlignment(Qt.AlignCenter)
            self.table1.item(rowPosition, 2).setTextAlignment(Qt.AlignCenter)
            self.table1.item(rowPosition, 5).setTextAlignment(Qt.AlignCenter)
            self.table1.item(rowPosition, 6).setTextAlignment(Qt.AlignCenter)

            rowColor = '' # '255,255,255' #white
            if wData['업무처리'] == 'AS요청' :
                rowColor = QColor(245,169,169) # rowColor = '245,169,169' #F5A9A9
            if wData['업무처리'] == '정상원고':
                rowColor = QColor(176,224,230) # '176,224,230' #B0E0E6

            if rowColor != '' :
                for col in range(self.table1_columns):
                    #if col == 0 : continue
                    cell = self.table1.item(rowNum, col)
                    cell.setBackground(rowColor)

    def wongoFind(self):
        global wongo_Folder, in_wongo_folder, out_wongo_folder

        searchStr = self.input_find.text()
        if searchStr == '' :
            QMessageBox.critical(self, "Error", "검색어를 입력하세요.")
            return

        serverURL = 'http://aaa.e-e.kr/article-list/wongoDuplicateCheckAction.php'

        if debugFlag: print('searchStr {}'.format(searchStr))

        postData = {'action': 'get_wongoDupResultFind', 'findStr': searchStr}
        debugLogSave('wogoSearch >> get_wongoDupResultFind 자료 요청 >> {}'.format(postData))
        res = requests.post(serverURL, data=postData)
        if debugFlag: print('res.text : {}'.format(res.text))
        jsonData = res.json()#json.load(res.text)
        if debugFlag: print('jsonData : {}'.format(jsonData))
        dataCount= jsonData['count']
        dataList = jsonData['data']
        if debugFlag: print('dataCount : {}'.format(dataCount))

        if dataCount == 0 :
            QMessageBox.warning(self, "Noti", "{}  >> 원고 중복 검사 자료가 없습니다.".format(searchStr))
            return

        self.searchWongoList = []
        self.checked_list = []

        #self.searchWongoType = searchWongoType
        #if debugFlag : print('searchWongoType : {}'.format(self.searchWongoType))

        row_count = self.table1.rowCount()
        del_row = row_count
        for num in range(row_count):
            del_row -= 1
            self.table1.removeRow(del_row)  # row delete

        for rowNum, wData in enumerate(dataList) :
            self.searchWongoList.append(wData)
            rowPosition = self.table1.rowCount()
            self.table1.insertRow(rowPosition)

            itemCheckbox = QTableWidgetItem()
            itemCheckbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            itemCheckbox.setCheckState(Qt.Unchecked)

            self.table1.setItem(rowPosition, 0, itemCheckbox)
            self.table1.setItem(rowPosition, 1, QTableWidgetItem(wData['원고종류']))
            self.table1.setItem(rowPosition, 2, QTableWidgetItem(wData['검사일']))
            self.table1.setItem(rowPosition, 3, QTableWidgetItem(wData['검사원고']))
            self.table1.setItem(rowPosition, 4, QTableWidgetItem(wData['중복원고']))
            self.table1.setItem(rowPosition, 5, QTableWidgetItem(wData['중복수']))
            self.table1.setItem(rowPosition, 6, QTableWidgetItem(wData['업무처리']))
            self.table1.item(rowPosition, 1).setTextAlignment(Qt.AlignCenter)
            self.table1.item(rowPosition, 2).setTextAlignment(Qt.AlignCenter)
            self.table1.item(rowPosition, 5).setTextAlignment(Qt.AlignCenter)
            self.table1.item(rowPosition, 6).setTextAlignment(Qt.AlignCenter)

            rowColor = '' # '255,255,255' #white
            if wData['업무처리'] == 'AS요청' :
                rowColor = QColor(245,169,169) # rowColor = '245,169,169' #F5A9A9
            if wData['업무처리'] == '정상원고':
                rowColor = QColor(176,224,230) # '176,224,230' #B0E0E6

            if rowColor != '' :
                for col in range(self.table1_columns):
                    cell = self.table1.item(rowNum, col)
                    cell.setBackground(rowColor)

#  subWindow 검색
from PyQt5 import QtCore, QtGui, QtWidgets, QtWebEngineWidgets

class SearchPanel(QtWidgets.QWidget):
    searched = QtCore.pyqtSignal(str, QtWebEngineWidgets.QWebEnginePage.FindFlag)
    view1_searched = QtCore.pyqtSignal(str, QtWebEngineWidgets.QWebEnginePage.FindFlag)
    view2_searched = QtCore.pyqtSignal(str, QtWebEngineWidgets.QWebEnginePage.FindFlag)
    closed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(SearchPanel, self).__init__(parent)
        lay = QtWidgets.QHBoxLayout(self)
        done_button = QtWidgets.QPushButton('Find Close')
        #self.case_button = QtWidgets.QPushButton('Match &Case', checkable=True)
        view1_next_button = QtWidgets.QPushButton('제출원고 > 다음')
        view1_prev_button = QtWidgets.QPushButton('이전 < 제출원고')
        view2_next_button = QtWidgets.QPushButton('비교원고 > 다음')
        view2_prev_button = QtWidgets.QPushButton('이전 < 비교원고')
        self.search_le = QtWidgets.QLineEdit()
        self.setFocusProxy(self.search_le)
        done_button.clicked.connect(self.closed)

        view2_next_button.clicked.connect(self.view2_update_searching)
        view2_prev_button.clicked.connect(self.view2_on_preview_find)

        view1_next_button.clicked.connect(self.view1_update_searching)
        view1_prev_button.clicked.connect(self.view1_on_preview_find)
        #self.case_button.clicked.connect(self.update_searching)

        for btn in (view1_prev_button, view1_next_button, self.search_le, view2_prev_button, view2_next_button, done_button, done_button):
            lay.addWidget(btn)
            if isinstance(btn, QtWidgets.QPushButton): btn.clicked.connect(self.setFocus)

        self.search_le.textChanged.connect(self.update_searching)
        self.search_le.returnPressed.connect(self.update_searching)
        self.closed.connect(self.search_le.clear)

        print('SearchPanel - 11 ')
        #QtWidgets.QShortcut(QtGui.QKeySequence.FindNext, self, activated=next_button.animateClick)
        #print('SearchPanel - 12 ')
        #QtWidgets.QShortcut(QtGui.QKeySequence.FindPrevious, self, activated=prev_button.animateClick)
        #print('SearchPanel - 13 ')
        #QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Escape), self.search_le, activated=self.closed)


    @QtCore.pyqtSlot()
    def on_preview_find(self):
        self.update_searching(QtWebEngineWidgets.QWebEnginePage.FindBackward)
    @QtCore.pyqtSlot()
    def view1_on_preview_find(self):
        print('view1_on_preview_find')
        self.view1_update_searching(QtWebEngineWidgets.QWebEnginePage.FindBackward)

    @QtCore.pyqtSlot()
    def view2_on_preview_find(self):
        print('view2_on_preview_find')
        self.view2_update_searching(QtWebEngineWidgets.QWebEnginePage.FindBackward)

    @QtCore.pyqtSlot()
    def update_searching(self, direction=QtWebEngineWidgets.QWebEnginePage.FindFlag()):
        print('update_searching')
        flag = direction
        #if self.case_button.isChecked():
        #    flag |= QtWebEngineWidgets.QWebEnginePage.FindCaseSensitively
        self.searched.emit(self.search_le.text(), flag)

    @QtCore.pyqtSlot()
    def view1_update_searching(self, direction=QtWebEngineWidgets.QWebEnginePage.FindFlag()):
        print('view1_update_searching')
        flag = direction
        #if self.case_button.isChecked():
        #    flag |= QtWebEngineWidgets.QWebEnginePage.FindCaseSensitively
        self.view1_searched.emit(self.search_le.text(), flag)

    @QtCore.pyqtSlot()
    def view2_update_searching(self, direction=QtWebEngineWidgets.QWebEnginePage.FindFlag()):
        print('view2_update_searching')
        flag = direction
        #if self.case_button.isChecked():
        #    flag |= QtWebEngineWidgets.QWebEnginePage.FindCaseSensitively
        self.view2_searched.emit(self.search_le.text(), flag)

    def showEvent(self, event):
        super(SearchPanel, self).showEvent(event)
        self.setFocus(True)


# 원고 비교 창
class subWindow(window2, sub_window):

    def __init__(self, searchWongoType, req_wongo, req_wongo_data, dup_wongo, dup_wongo_data, dup_content):
        #global in_wongo_folder, out_wongo_folder, htmlFolder
        if debugFlag : print('\nsubWindow Start ------------------------------')

        super(window2, self).__init__()
        self.setupUi(self)
        #super().__init__()
        self.req_wongo = req_wongo
        self.req_wongo_data = req_wongo_data
        self.dup_wongo = dup_wongo
        self.dup_wongo_data = dup_wongo_data
        self.searchWongoType = searchWongoType
        self.dup_content = dup_content

        self.out_url = ''

        #self.btn_search.clicked.connect(self.view_search)

        self.initUI()

        self._search_panel = SearchPanel()
        self.search_toolbar = QtWidgets.QToolBar()
        self.search_toolbar.addWidget(self._search_panel)
        self.addToolBar(Qt.BottomToolBarArea, self.search_toolbar)
        self.search_toolbar.hide()
        self._search_panel.searched.connect(self.on_searched)
        self._search_panel.view1_searched.connect(self.view1_searched)
        self._search_panel.view2_searched.connect(self.view2_searched)
        self._search_panel.closed.connect(self.search_toolbar.hide)
        self.create_menus()


    @QtCore.pyqtSlot(str, QtWebEngineWidgets.QWebEnginePage.FindFlag)
    def on_searched(self, text, flag):
        def callback(found):
            if text and not found:
                self.statusBar().show()
                self.statusBar().showMessage('Not found')
            else:
                self.statusBar().hide()
        self.browser1.findText(text, flag, callback)
        self.browser2.findText(text, flag, callback)

    @QtCore.pyqtSlot(str, QtWebEngineWidgets.QWebEnginePage.FindFlag)
    def view1_searched(self, text, flag):
        def view1_callback(found):
            if text and not found:
                self.statusBar().show()
                self.statusBar().showMessage('Not found')
            else:
                self.statusBar().hide()
        self.browser1.findText(text, flag, view1_callback)

    @QtCore.pyqtSlot(str, QtWebEngineWidgets.QWebEnginePage.FindFlag)
    def view2_searched(self, text, flag):
        def view2_callback(found):
            if text and not found:
                self.statusBar().show()
                self.statusBar().showMessage('Not found')
            else:
                self.statusBar().hide()
        self.browser2.findText(text, flag, view2_callback)

    def create_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        file_menu.addAction('&Find...', self.search_toolbar.show, shortcut=QKeySequence.Find)

    def initUI(self):
        global in_wongo_folder, out_wongo_folder, htmlFolder

        self.setWindowTitle('원고 중복 확인')
        #self.setGeometry(650, 100, 1200, 800)
        #if debugFlag : print('in_wongo_folder : {}'.format(in_wongo_folder))
        #if debugFlag : print('out_wongo_folder : {}'.format(out_wongo_folder))

        if debugFlag : print('원고 보기 subWindow : {} / {} / {}'.format(self.searchWongoType, self.req_wongo, self.dup_wongo))

        try:
            data1 = self.req_wongo_data
            data2 = self.dup_wongo_data
            data2 = data2.replace('읽음비밀글팔로우통계','<br><br>')
            data2 = data2.replace('이웃추가 본문 기타 기능 공유하기','<br><br>')
            #if debugFlag : print('data2 : {}'.format(data2))

            self.out_url = ''
            if self.searchWongoType == "외부원고" :
                self.out_url = self.dup_wongo

            wonStr = 9312 # 숫자 원문자 표시
            for i, dup_content in enumerate(self.dup_content) :
                if dup_content == '' : continue
                while dup_content[-1] == ' ' :
                    if dup_content[-1] == ' ' : dup_content = dup_content[:-1]

                if self.searchWongoType == "외부원고" or self.searchWongoType == "다른내부원고":
                    if dup_content in data1:
                        data2_dup_count = len(data2.split(dup_content)) - 1
                        if debugFlag: print(
                            ' {} >> {} data2_dup_count : {}'.format(self.searchWongoType, dup_content, data2_dup_count))
                        data1 = self.findStringFirst(data1, dup_content, wonStr + i)
                        if data2_dup_count > 1:
                            data1 = self.findStringSecound(data1, dup_content, wonStr + i)

                        # data1 = data1.replace(dup_content, '<small>&#{};</small><span style="background-color:yellow">{}</span>'.format(wonStr+i, dup_content))
                    if dup_content in data2:
                        data2 = data2.replace(dup_content, '<span style="background-color:#F5A9F2"><small>&#{};</small></span><span style="background-color:yellow">{}</span>'.format(wonStr+i, dup_content))
                elif self.searchWongoType == "내부원고":
                    data2_dup_count = len(data2.split(dup_content)) - 1
                    if debugFlag : print(' {} >> {} data2_dup_count : {}'.format(self.searchWongoType, dup_content, data2_dup_count))
                    if dup_content in data1 :
                        data1 = self.findStringFirst(data1, dup_content, wonStr+i)
                        #data1 = data1.replace(dup_content, '<small>&#{};</small><span style="background-color:yellow">{}</span>'.format(wonStr+i, dup_content))
                    if data2_dup_count == 1 :
                        data2 = self.findStringFirst(data2, dup_content, wonStr+i)
                    elif data2_dup_count > 1 :
                        data2 = self.findStringSecound(data2, dup_content, wonStr+i)
                        #data2 = data2.replace(dup_content, '<small>&#{};</small><span style="background-color:yellow">{}</span>'.format(wonStr+i, dup_content))

            data1 = data1.replace('\n', '\n<br>')
            data2 = data2.replace('\n', '\n<br>')

            html1 =  htmlFolder.replace("\\","/") + "/wongo_1.html"
            html2 =  htmlFolder.replace("\\","/") + "/wongo_2.html"

            with open(html1, 'w', encoding='utf-8') as fp :
                fp.write(data1)

            if self.searchWongoType == "외부원고" :
                data2 = data2.replace('안녕하세요', '<br><br>안녕하세요').replace('다.', '다.<br><br>').replace('<br><br><br>', '<br><br>')
            with open(html2, 'w', encoding='utf-8') as fp :
                fp.write(data2)

            if debugFlag :
                print('html1 : {}'.format(html1))
                print('html2 : {}'.format(html2))

            # test html
            #url1 = 'file:///D:/work/220124 원고중복 확인 (UI)/html/test1.html'
            #url2 = 'file:///D:/work/220124 원고중복 확인 (UI)/html/test2.html'

            self.title1.setText(self.req_wongo)
            self.title2.setText(self.dup_wongo)

            lay1 = QVBoxLayout(self.widget1)
            lay2 = QVBoxLayout(self.widget2)

            self.browser1 = QWebEngineView()
            self.browser1.load(QUrl(html1))
            lay1.addWidget(self.browser1)

            self.browser2 = QWebEngineView()
            self.browser2.load(QUrl(html2))
            lay2.addWidget(self.browser2)

            self.chrome_exe.clicked.connect(self.fn_chrome_browser)

            #self.setGeometry(800, 100, 1000, 700)
            self.setWindowTitle('원고 중복 비교 > {}'.format(self.searchWongoType))
            #self.setFixedSize(1000, 700)

        except Exception as e :
            print('subWindow initUI Exception : {}'.format(e))
            return False
    '''
    def view_search(self):
        findStr = self.input_search.text()
        direction = QtWebEngineWidgets.QWebEnginePage.FindFlag()
        self.search_action(findStr, direction)

    def search_action(self, text, direction) :
        def callback(found):
            if text and not found:
                self.statusBar().show()
                self.statusBar().showMessage('Not found')
            else:
                self.statusBar().hide()
        print('subWindow > view_search')
        if findStr == '' :
            print('검색 입력 누락')
            return
        #direction = QtWebEngineWidgets.QWebEnginePage.FindFlag()
        print('direction : {}'.format(direction))
        self.browser1.findText(findStr, direction, callback)
    '''

    def fn_chrome_browser(self):

        if self.searchWongoType != "외부원고" :
            QMessageBox.warning(self, 'Noti', '외부중복 원고에서 사용하는 기능입니다.')
            return

        url = self.out_url
        debugLogSave('fn_chrome_browser / url : {}'.format(url))

        chrome_filepath = 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
        if os.path.exists(chrome_filepath):
            pass
        else:
            chrome_filepath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'

        chromeExec = chrome_filepath + " {}".format(url)
        if debugFlag: print(chromeExec)

        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        # si.wShowWindow = subprocess.SW_HIDE # default
        subprocess.call(chromeExec, startupinfo=si)


    def findStringFirst(self, data, findStr, num):
        dataSplit = data.split(findStr)
        retStr = ''
        for i, s in enumerate(dataSplit) :
            if i == 0 :
                retStr = s + '<span style="background-color:#F5A9F2"><small>&#{};</small></span><span style="background-color:yellow">{}</span>'.format(num, findStr)
            elif i < len(dataSplit) -1 :
                retStr += s + findStr
            else:
                retStr += s

        return  retStr

    def findStringSecound(self, data, findStr, num):
        dataSplit = data.split(findStr)
        retStr = ''
        for i, s in enumerate(dataSplit) :
            if i == 0 :
                retStr = s + findStr
            elif i < len(dataSplit) - 1:
                retStr += s + '<span style="background-color:#F5A9F2"><small>&#{};</small></span><span style="background-color:yellow">{}</span>'.format(num, findStr)
            else:
                retStr += s

        return  retStr


    def remove_tag(self, content):
        cleantext = ''
        try:
            content = content.replace('\n\n', '||nn||')
            content = content.replace('\n', '')

            if False:
                with open('cleantext0.txt', 'a') as fp0:
                    cleantext = content.replace('&nbsp;', ' ')
                    fp0.write('{}'.format(cleantext))

            if True:
                cleanr = re.compile('<script.*?</script>')
                cleantext1 = re.sub(cleanr, '', content)
                cleanr = re.compile('<style.*?</style>')
                cleantext1 = re.sub(cleanr, '', cleantext1)

                cleantext1 = cleantext1.replace('<img', '<br><br><img')

                cleantext1 = cleantext1.replace('<br>', '||br||')

                cleanr = re.compile('<.*?>')
                cleantext = re.sub(cleanr, '', cleantext1)
                cleantext = cleantext.replace('&nbsp;', ' ').replace('\t', ' ')

                cleantext = cleantext.replace('||nn||', '\n')
                cleantext = cleantext.replace('||br||', '\n')
                cleantext = cleantext.replace(' \n', '\n')

                for i in range(10):
                    cleantext = cleantext.replace('  ', ' ')

                for i in range(10):
                    cleantext = cleantext.replace('\n\n', '\n')
        except Exception as e :
            errorLogSave('remove_tag Exception : {}'.format(e))
        return cleantext



def deleteHtml():
    global htmlFolder
    print('view html file delete')
    html_list = os.listdir(htmlFolder)
    for file in html_list :
        print(htmlFolder + '\\'+ file)

def outputLogSave(msg) :
    global logFolder
    now = datetime.datetime.now()
    logDate = now.strftime('%y%m%d')
    logTime = now.strftime('%y-%m-%d %H:%M:%S')
    logFile = '{}/output_{}.txt'.format(logFolder, logDate)
    with open(logFile,'a') as fp:
        fp.write('{}\t{}\n'.format(logTime, msg))
    print('outputLog >> {}\t{}'.format(logTime, msg))


def debugLogSave(msg) :
    global logFolder
    now = datetime.datetime.now()
    logDate = now.strftime('%y%m%d')
    logTime = now.strftime('%y-%m-%d %H:%M:%S')
    logFile = '{}/debug_{}.txt'.format(logFolder, logDate)
    with open(logFile,'a') as fp:
        fp.write('{}\t{}\n'.format(logTime, msg))

    if debugFlag : print('debugLog >> {}\t{}'.format(logTime, msg))


def errorLogSave(msg) :
    global logFolder
    now = datetime.datetime.now()
    logDate = now.strftime('%y%m%d')
    logTime = now.strftime('%y-%m-%d %H:%M:%S')
    logFile = '{}/error_{}.txt'.format(logFolder, logDate)
    with open(logFile,'a') as fp:
        fp.write('{}\t{}\n'.format(logTime, msg))

    if debugFlag : print('errorLog >> {}\t{}'.format(logTime, msg))


# MAIN --------------------------------------------
if __name__ == '__main__':

    serverURL = 'http://aaa.e-e.kr/article-list/wongoDuplicateCheckAction.php'
    asURL = "http://aaa.e-e.kr/article-list/wongo_as_request.php"

    logFolder = './log'
    if not os.path.exists(logFolder):
        os.makedirs(logFolder)

    htmlFolder = os.getcwd() + '\\html'
    if not os.path.exists(htmlFolder):
        os.makedirs(htmlFolder)

    in_check_list_file = ''
    in_merge_file  = '@내부중복.txt'
    out_merge_file = '@외부중복.txt'

    config = configparser.ConfigParser()
    try:
        config.read('config_wongo_check_ui.ini', encoding='utf-8')
        wongo_Folder  = config['DEFAULT']['중복원고'] #+ "\\"
        use_wongo_Folder  = config['DEFAULT']['사용원고폴더'] #+ "\\"

        #out_wongo_Folder = config['DEFAULT']['외부중복원고'] + "\\"
    except Exception as e:
        print('config.ini file Exception : {}'.format(e))
        sys.exit()

    in_wongo_folder = '{}\\내부중복\\'.format(wongo_Folder)
    out_wongo_folder = '{}\\외부중복\\'.format(wongo_Folder)

    print('wongo_Folder (중복원고) : {}'.format(wongo_Folder))
    #input('enter > ')
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    myWindow = MyWindowClass()
    myWindow.show()
    app.exec_()

    #deleteHtml()

