# -*- encoding: utf-8 -*-

import re
import sys
import os
import time
import random
import urllib.request
import pyperclip
import wget
import shutil
import ctypes
import requests
import json
import pdb
from win32com.client import Dispatch
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
import datetime
import glob
import configparser
import hashlib
#from collections import defaultdict


import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# python selenium 표준 v1.1 (190324)
# chromedriver 자동 다운로드 추가
# 190324 자체 타이틀 기능 추가



def fnFindBlogList(dr, query):

	if debugFlag : print('\nfnFindBlogList -----------------------')

	rank = 0
	blogUrlList = []
	query2 = query.replace('+', '')
	try:
		if debugFlag :
			print('fnFindBlogList  Q : {}'.format(query2))
		search_url = 'https://search.naver.com/search.naver?where=view&sm=tab_jum&query="{}"'.format(query)
		try:
			dr.get(search_url)
			dr.implicitly_wait(10)
		except Exception as e :
			errorLog('{} >> Browser Exception >> {}'.format(query, e))
			dr.quit()
			return 999, blogUrlList
			#sys.exit()

		if False :
			pageSource = dr.page_source
			soup = BeautifulSoup(pageSource, 'html.parser')
			liList = soup.find_all("ul", {"class", "lst_total._list_base"})

		try:
			pageSource = dr.page_source
			soup = BeautifulSoup(pageSource, 'html.parser')
			liList = soup.find_all("li", {"class", "bx _svp_item"})
			if len(liList) == 0 :
				outputLog('검색 : {} >> 검색 결과 없음 >> {}'.format(query, search_url))
				return 0, blogUrlList
			#liList = dr.find_elements_by_css_selector('div.total_wrap.api_ani_send')
			else:
				liList = dr.find_element_by_css_selector('ul.lst_total._list_base').find_elements_by_css_selector('li')
			if debugFlag : print('debug 1 > li {}'.format(len(liList)))
		except Exception as e :
			#debugLog('검색 : {} >> 검색 결과 없음 >> {}'.format(query, search_url))
			errorLog('검색 : {} >> {} >> 검색 오류 : {}'.format(query, search_url, e), True)
			return 0, blogUrlList

		for li_item in liList:
			rank += 1

			blogInfo = li_item.find_elements_by_css_selector('div.total_area')[0]
			#titleElement = blogInfo.find("a", {"class", "api_txt_lines total_tit"})
			#titleElement = blogInfo.find_elements_by_css_selector('a.api_txt_lines.total_tit._cross_trigger')[0]
			titleElement = blogInfo.find_elements_by_css_selector('a.api_txt_lines.total_tit')[0]

			#print('debug 2-1 >  {}'.format(rank))
			#blogUrl = titleElement['href']
			blogUrl = titleElement.get_attribute('href')
			blogTitle = titleElement.text

			if debugFlag : print('R {}, T : {}, U : {}'.format(rank, blogTitle, blogUrl))

			# 220317 test
			if False :
				#test_url = 'post.naver.com/viewer/postView.naver?volumeNo=33427089&memberNo=38070069&vType=VERTICAL'
				test_url_1 = 'post.naver.com/viewer/postView.naver?volumeNo=33337174&memberNo=35665182&vType=VERTICAL'
				test_url_2 = 'post.naver.com/viewer/postView.naver?volumeNo=32977789&memberNo=38070069&vType=VERTICAL'
				if test_url_1 not in blogUrl and test_url_2 not in blogUrl :
					continue

			if False: #debugFlag :
				print('%d T : %s ' % (rank, blogTitle))
				print(blogUrl)

			if False and '보험' not in blogTitle :
				continue

			if 'blog.naver.com/' not in blogUrl \
				and 'post.naver.com/' not in blogUrl \
				and 'adcr.naver.com/' not in blogUrl \
				and 'search.naver.com/' not in blogUrl :
				#and 'cafe.naver.com/' not in blogUrl:
				continue

			#if 'post.naver.com/' not in blogUrl : continue

			#contentElement = blogInfo.find("div", {"class", "api_txt_lines dsc_txt"})
			#contentMarks = contentElement.find_all("mark")

			contentElement = blogInfo.find_elements_by_css_selector('div.api_txt_lines.dsc_txt')[0]   #find("div", {"class", "api_txt_lines dsc_txt"})
			contentMarks = contentElement.find_elements_by_css_selector("mark")
			for mark in contentMarks:
				markText = mark.text.replace(' ','')
				if debugFlag : print('mark text : '+markText)
				if query2 in markText :
					if debugFlag : print('url push : ' + blogUrl)
					blogUrlList.append(blogUrl)

	except Exception as e:
		print('Exception -----------------------------')
		print(format(e))
		#input('Enter > ')

	if debugFlag and len(blogUrlList) > 0 :
		print('\nreturn blogUrlList {}'.format(blogUrlList))
		#input(' enter 1 >')
	return 1, blogUrlList


def fnBlogContentCheck(dr, findBlogList, checkText, checkFilename) :
	global duplicateContentList, checkFileBlogUrl, checkBlog, MIN_COMPARE_LINE
	global wongoFileCheckFlag, confirmLine, blogSaveFolder

	if debugFlag : print('\nfnBlogContentCheck -----------------------')

	for n, url in enumerate(findBlogList):
		try:
			if debugFlag : print('check B url : {}'.format(url))

			if url in checkFileBlogUrl :
				if debugFlag : print('skip url {}'.format(url))
				continue
			blogScore = 0
			contentText = ''
			duplicateLine = []
			confirmLine = []
			dr.get(url)
			dr.implicitly_wait(10)
			blog_title = dr.title.replace(': 네이버 포스트','').replace(': 네이버 블로그','')
			'''
			if 'memberNo=40974637' in url :
				try:
					# https://post.naver.com/viewer/postView.nhn?volumeNo=15776480&memberNo=40974637&vType=VERTICAL
					print('=' * 50)
					print('{} / {} check C url : {}'.format(n+1, len(findBlogList), url))
					cur_url = dr.current_url
					print('cur_url : {}'.format(cur_url))
				except Exception as e : print('40974637 > Exception - 1\n{}'.format(e))
			# alert 검사
			try:
				print('alert 검사 ============================')
				alert = dr.switch_to_alert()
				input('alert : {} : 확인 > '.format(alert.text))

				if '비공개' in alert.text.replace(' ', ''):
					print('{} :  비공개된 포스트입니다.'.format(url))
					continue
				else:
					alert.dismiss()
			except Exception as e:
				print('alert check Exception : {}'.format(e))
				pass
			'''

			try:
				dr.switch_to_frame("mainFrame")
			except:
				pass

			'''
			try:
				contentText = dr.find_element_by_css_selector('.se-main-container').text
			except:
				try:
					contentText = dr.find_elements_by_css_selector('.se_component_wrap')[1].text
				except:
					contentText = dr.find_elements_by_css_selector('.post-view')[0].get_attribute('outerHTML')
			'''

			pageSource = dr.page_source
			soup = BeautifulSoup(pageSource, 'html.parser')

			blogContents = []
			#if debugFlag : print('soup ------------------\n{}\n'.format(soup) )
			#blogContents = soup.find_all("div", {"class", ".se-main-container"})
			#if debugFlag : print('blogContents ------------------\n{}\n'.format(blogContents) )
			'''
			blogContent = remove_tag(pageSource)
			blogContents = blogContent.split('\n')
			# print('blogContents : {}'.format(len(blogContents)))
	
			for content in blogContents:
				# if debugFlag : print(content)
				if content == '\n' or content.replace(' ', '') == '':
					# if content == '\n' :
					continue
				contentText += content.replace('&nbsp;', ' ')
			'''

			if 'blog.naver.com' in url :
				blogContents = soup.find_all("div", {"class", "se-module se-module-text"})

				for content in blogContents:
					#if debugFlag : print(content)
					if content.text == '\n' :
						continue
					contentText += content.text

			#elif 'post.naver.com' in url :
			else:
				blogContent = remove_tag(pageSource)
				blogContents = blogContent.split('\n')
				#print('blogContents : {}'.format(len(blogContents)))
				if debugFlag : print('remove_tag =====> {}'.format(url))

				#220317
				if False :
					for content in blogContents:
						#if debugFlag : print(content)
						#220317
						#if content == '\n' or content.replace(' ','') == '' :
						if content.replace(' ','') == '' :
							continue
						contentText += content

				#if debugFlag: print('contentText : {}'.format(contentText))
				contentText = blogContent

			'''
			if 'blog.naver.com' in url :
				blogContents = soup.find_all("div", {"class", "se-module se-module-text"})
	
				for content in blogContents:
					#if debugFlag : print(content)
					if content.text == '\n' :
						continue
					contentText += content.text
	
			elif 'post.naver.com' in url :
				blogContent = remove_tag(pageSource)
				blogContents = blogContent.split('\n')
				#print('blogContents : {}'.format(len(blogContents)))
	
				for content in blogContents:
					#if debugFlag : print(content)
					if content == '\n' or content.replace(' ','') == '' :
					#if content == '\n' :
						continue
					contentText += content
			elif 'cafe.naver.com' in url :
				blogContents = soup.find_all("div", {"class", "main-area"})
				for content in blogContents:
					#if debugFlag : print(content)
					if content.text == '\n' :
						continue
					contentText += content.text
			'''

			if False :
				for content in blogContents:
					# if debugFlag : print(content)
					if content.text == '\n':
						continue
					contentText += content.text


			if False :  # False , debugFlag
				print('url : {}'.format(url))
				print(' CONTENT S ---------------------------------')
				print(contentText)
				print(' CONTENT E ---------------------------------')
			# 220317 test
			if debugFlag : print('contentText >> {}'.format(contentText))

			for line_n, checkLine in enumerate(checkText[1:]) :

				checkLine = str(checkLine).rstrip().lstrip()  # 완쪽, 오른쪽 공백제거

				# 220317 test
				if debugFlag : print('line {} >> {}'.format(line_n+1, checkLine))

				if '**' in checkLine:
					continue

				if checkLine == '':
					continue

				if '안녕하세요' in checkLine:
					continue

				if '반갑습니다' in checkLine:
					continue

				if 'http' in checkLine:
					continue

				if len(checkLine) <= 10:
					continue

				if checkLine in contentText :
					blogScore += 1
					#confirmLine.append(format(checkLine))
					duplicateLine.append('{}'.format(checkLine))
					debugLog('중복확인 >> blogScore : {} >> checkLine : {}'.format(blogScore, checkLine) )
					debugLog('중복확인 >> blogScore : {} >> duplicateLine : {}'.format(blogScore, duplicateLine))

			#if debugFlag : print('blogScore {} '.format(blogScore))
			if blogScore >= MIN_COMPARE_LINE :
				debugLog('blogScore : {} >> url : {} >> duplicateLine : {}'.format(blogScore, url, duplicateLine))

				#if len(checkFileBlogUrl) == 0 or checkFileBlogUrl.index(url) < 0 :
				if len(checkFileBlogUrl) == 0 or url not in checkFileBlogUrl :
					checkFileBlogUrl.append(url)
					duplicateContent = []
					duplicateContent.append(url)
					#duplicateContent.append('||'.join(duplicateLine))
					duplicateContent.append(duplicateLine)
					duplicateContentList.append(duplicateContent)

					# 증복 blog contents save # 220324 사용안함
					'''
					enc = hashlib.md5()
					enc.update(url.encode('utf-8'))
					encText = enc.hexdigest()
					'''
					#220325
					'''
					blogSaveFile = blogSaveFolder + '\\{}.txt'.format(encText)
					with open(blogSaveFile, 'w', encoding='utf-8') as fp:
						fp.write('{}\n'.format(url))
						fp.write(contentText)
						outputLog('blog content save file \n{}\n중복원고저장 : {}\n'.format(url, blogSaveFile))
					'''
					if debugFlag : print('check File {}'.format(checkFilename))
					if debugFlag : print('checkFileBlogUrl append url {}'.format(url))

					debugLog('원고 {} >> blogScore {} : {}'.format(checkFilename, blogScore, url))

					tempA = [checkFilename, url, blogScore, blog_title]
					checkBlog.append(tempA)
					if debugFlag :
						print('check Info : {}'.format(checkBlog))
						#print('break')

					wongoFileCheckFlag = True
					#break

					#220323
					dupCheckData = {'wongo_file': url, 'title': blog_title, 'wongo_data': contentText}
					jsonData = json.dumps(dupCheckData, ensure_ascii=False)

					postData = {'action': 'out_wongo_dup_data_save', 'outWongoData': jsonData}
					debugLog('out_wongo_dup_data_save 자료전송 >> {}'.format( postData))
					res = requests.post(serverURL, data=postData)
					debugLog('fnBlogContentCheck >> out_wongo_dup_data_save >> res.text \n{}'.format(res.text))

			if debugFlag and len(checkFileBlogUrl) > 0 :
				print('checkFileBlogUrl : {}'.format(checkFileBlogUrl))
				print('duplicateContentList : {}'.format(duplicateContentList))
		except Exception as e :
			errorLog('fnBlogContentCheck Exception : {}'.format(e), True)
			continue
	#return checkBlog

# 원고 파일별 중복 결과 저장
def outputSave( outputFile ):
	global checkBlog, confirmLine, duplicateFolder

	saveStr = []

	# test append
	# B1 = ['이름-0217-05-실버보험.txt', 'https://blog.naver.com/ddabi/22223352717777777', 50]
	# checkBlog.append(B1)

	#if( len(checkBlog) <= 0 ): return saveStr
	#print('outputSave  checkBlog : {}'.format(checkBlog))
	checkBlog.sort()

	A1 = checkBlog[0]
	saveStr.append(A1)

	i = 0
	for item in checkBlog :
		if A1[0] == item[0] :
			if A1[2] < item[2]:
				saveStr[i][1] = item[1]
				saveStr[i][2] = item[2]
		else :
			i += 1
			saveStr.append(item)

	if debugFlag : print('outputSave  saveStr : {}'.format(saveStr))

	with open(outputFile, 'a') as fp:
		lineNum = 0
		for line in saveStr :
			fileT = line[0].split('\\')
			if( len(fileT) > 2 ) : checkFile = fileT[2]
			else : checkFile = line[0]
			writeStr = "{}	{}	{}\n".format(checkFile, line[1], line[2])
			print(writeStr)
			fp.write(writeStr)
			for str in confirmLine :
				lineNum += 1
				fp.write('\n{}'.format(str))
				print('중복확인 {}\t{}'.format(lineNum, str))
			fp.write('\n\n')

	return saveStr


def remove_tag(content):

	content = content.replace('\n\n','||nn||')
	content = content.replace('\n','')

	if False :
		with open('cleantext0.txt', 'a') as fp0:
			cleantext = content.replace('&nbsp;',' ')
			fp0.write('{}'.format(cleantext))

	if True:
		cleanr = re.compile('<script.*?</script>')
		cleantext1 = re.sub(cleanr, '', content)
		cleanr = re.compile('<style.*?</style>')
		cleantext1 = re.sub(cleanr, '', cleantext1)
		cleantext1 = cleantext1.replace('<br>','||br||')

		cleanr = re.compile('<.*?>')
		cleantext = re.sub(cleanr, '', cleantext1)
		cleantext = cleantext.replace('&nbsp;',' ').replace('\t',' ')

		cleantext = cleantext.replace('||nn||','\n')
		cleantext = cleantext.replace('||br||','\n')
		cleantext = cleantext.replace(' \n','\n')

		for i in range(10) :
			cleantext = cleantext.replace('  ', ' ')
		
		for i in range(10) :
			cleantext = cleantext.replace('\n\n', '\n')

		# 220317 test
		if False:
			with open('cleantext1.txt', 'a') as fp1:
				fp1.write('{}'.format(cleantext))
			print('=='*100 + '\n')
			print('cleantext1.txt write')
			print( '\n'+ '==' * 100 + '\n'*3)

	return cleantext


def outputLog(log_msg):
	global logFile
	try:
		now = datetime.datetime.now()
		logDate = now.strftime('%y%m%d')
		checkTime = now.strftime('%m.%d %H:%M:%S')
		with open(logFile, 'a') as fp:
			fp.write('{}\t{}\n'.format(checkTime, log_msg))

		print('log >> {}'.format(log_msg))
	except Exception as e :
		print('outputLog >> {} >> Exception : {}'.format(log_msg, e))

def debugLog(log_msg):
	global debugLogFile
	try:
		now = datetime.datetime.now()
		logDate = now.strftime('%y%m%d')
		checkTime = now.strftime('%m.%d %H:%M:%S')
		with open(debugLogFile, 'a', encoding='utf-8') as fp:
			fp.write('{}\t{}\n'.format(checkTime, log_msg))

		if debugFlag : print('log >> {}'.format(log_msg))
	except Exception as e :
		print('debugLog >> {} >> Exception : {}'.format(log_msg, e))

def errorLog(log_msg , outFlag):
	global errorLogFile
	try:
		now = datetime.datetime.now()
		checkTime = now.strftime('%m.%d %H:%M:%S')
		with open(errorLogFile, 'a', encoding='utf-8') as fp:
			fp.write('{}\t{}\n'.format(checkTime, log_msg))

		if outFlag : print('error_log >> {}'.format(log_msg))
	except Exception as e :
		print('errorLog >> {} >> Exception : {}'.format(log_msg, e))

def chrome_driver(cacheFolder) :

	chrome_options = Options()
	chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
	chrome_options.add_argument('--user-data-dir=' + cacheFolder)

	if headless == 'N' : #debugFlag:
		chrome_options.add_argument('--window-position=850,0')
	else:
		chrome_options.add_argument('--window-position=850,5000')

	driver = webdriver.Chrome('c:\\chromedriver\\chromedriver.exe', chrome_options=chrome_options)

	debugLog('chrome start')

	return driver


# MAIN --------------------------------------------
if __name__ == '__main__':

	debugFlag = False
	#debugFlag = True

	MIN_COMPARE_LINE = 10
	WongoFolder = 'W:\\3_사용가능\\'
	#if debugFlag : 	WongoFolder = 'C:\\3_사용가능\\'
	#WongoFolder = 'C:\\3_사용가능\\'
	##WongoFolder = 'W:\\3_사용가능\\' ##'C:\\3_사용가능\\'

	serverURL = 'http://aaa.e-e.kr/article-list/wongoDuplicateCheckAction.php'
	getUseFolder = '중복검사'
	getRandom = ''
	configFile = "config.txt"
	'''
	if os.path.isfile(configFile):
		try:
			config_list = open(configFile).read().splitlines()
		except:
			config_list = open(configFile, encoding='utf-8-sig').read().splitlines()
	else:
		print('환경파일 config.txt 없습니다.')
		sys.exit()
	'''
	run_type = ''
	headless = 'Y'
	if len(sys.argv) == 2:
		run_type = sys.argv[1]
	elif len(sys.argv) == 3:
		run_type = sys.argv[1]
		headless = sys.argv[2]
	else:
		if debugFlag : run_type = 'RUN_1'
		else :
			#run_type = 'RUN_3'
			print('배치파일을 실행하세요.  run1 또는 run2 또는 run3 실행 !!')
			sys.exit()

	program_title = '원고 중복 검사 프로그램 V2.0.0'  # 폴더 나누어서 사용 버전
	ctypes.windll.kernel32.SetConsoleTitleW(run_type + " - " + program_title)
	print(run_type + " - " + program_title +"\n")

	if os.path.isfile(configFile):
		try:
			config = configparser.ConfigParser()
			config.read('config.txt', encoding='utf-8-sig')
			WongoFolder = config[run_type]['작업기본폴더명']
			getFolder = config[run_type]['원고폴더명']
			# getRandom = config[run_type]['랜덤라인']
			getCheckLine = config[run_type]['중복검사기준']
			getNormalSaveFolder = config[run_type]['정상원고저장폴더']
			getDuplicateSaveFolder = config[run_type]['중복원고저장폴더']
			'''
			if run_type == 'RUN_1' :
			elif run_type == 'RUN_2' :
				config = configparser.ConfigParser()
				config.read('config.txt', encoding='utf-8-sig')
				WongoFolder = config['DEFAULT']['작업기본폴더명'] + '\\'
				getFolder = config['DEFAULT']['폴더명']
				#getRandom = config['DEFAULT']['랜덤라인']
				getCheckLine = config['DEFAULT']['중복검사기준']
				getDuplicateSaveFolder = config['DEFAULT']['중복원고저장폴더']
			elif run_type == 'RUN_3' :
				config = configparser.ConfigParser()
				config.read('config.txt', encoding='utf-8-sig')
				WongoFolder = config['DEFAULT']['작업기본폴더명'] + '\\'
				getFolder = config['DEFAULT']['폴더명']
				#getRandom = config['DEFAULT']['랜덤라인']
				getCheckLine = config['DEFAULT']['중복검사기준']
				getDuplicateSaveFolder = config['DEFAULT']['중복원고저장폴더']
			'''
			#if getFolder != '' : getUseFolder += '\\' + getFolder
			if getCheckLine != '' : MIN_COMPARE_LINE = int(getCheckLine)
		except Exception as e :
			print(format(e))
			print('환경파일 config.txt 내용을 확인하세요.')
			sys.exit()
	else:
		print('환경파일 config.txt 없습니다.')
		sys.exit()

	'''
	for cLine in config_list :
		cLine = cLine.replace(' ', '')
		cLine = cLine.replace('\t', '')
		if '폴더명=' in cLine :
			getFolder = cLine.replace('폴더명=','')
			if getFolder != '' : getUseFolder += '\\' + getFolder
		if '랜덤라인=' in cLine :
			getRandom = cLine.replace('랜덤라인=','')
		if '중복검사기준=' in cLine :
			getCheckLine = cLine.replace('중복검사기준=','')
			if getCheckLine != '' : MIN_COMPARE_LINE = int(getCheckLine)
	'''

	run_type = run_type.lower()
	now = datetime.datetime.now()
	curDate = now.strftime('%y%m%d')
	#checkTime = now.strftime('%m.%d %H:%M:%S')

	#duplicateFolder = WongoFolder + getUseFolder + '\\'
	#getRandom = int(getRandom)
	useFolder = WongoFolder + '\\' + getUseFolder + '\\'+ getFolder
	#duplicateFolder =  WongoFolder + '\\' + getUseFolder + '\\' + getDuplicateSaveFolder
	duplicateFolder =  getDuplicateSaveFolder
	WongoUseFolder = getNormalSaveFolder # WongoFolder
	cacheFolder = os.getcwd() + '\\browser_cache\\'+ run_type
	logFolder = os.getcwd() + '\\log'
	logFile = os.getcwd() + '\\log\\'+ run_type +'_log_{}.txt'.format(curDate)
	debugLogFile = os.getcwd() + '\\log\\'+ run_type +'_debug_log_{}.txt'.format(curDate)
	errorLogFile = os.getcwd() + '\\log\\'+ run_type +'_errorLog_{}.txt'.format(curDate)


	print('config type : {}'.format(run_type))
	print('작업 기본 폴더 : {}'.format(WongoFolder))
	print('원고 검사 폴더 : {}'.format(useFolder))
	#print('랜덤 라인 : {}'.format(getRandom))
	print('중복 검사 기준 : {}'.format(MIN_COMPARE_LINE))
	print('중복원고 저장 폴더 : {}'.format(duplicateFolder))
	print('정상원고 저장 폴더 : {}'.format(WongoUseFolder))
	print('\nBrowser Cache : {}'.format(cacheFolder))
	print('log file : {}'.format(logFile))

	# 220325 삭제
	# -----------------------------------------
	blogSaveFolder = duplicateFolder +'\\blog'
	outFile = duplicateFolder +'\\'+ run_type +'_output_'+curDate+'.txt'
	print('output file : {}'.format(outFile))
	try:
		if not os.path.exists(blogSaveFolder):
			os.makedirs(blogSaveFolder)
	except : pass
	# -----------------------------------------

	if not os.path.isdir(WongoUseFolder) :
		print('{}  폴더 접근 확인이 필요합니다'.format(WongoUseFolder))
		sys.exit()
	if not os.path.isdir(duplicateFolder) :
		print('{}  폴더 접근 확인이 필요합니다'.format(duplicateFolder))
		sys.exit()

	try:
		if not os.path.exists(logFolder):
			os.makedirs(directory)
	except:
		pass


	# if debugFlag : input('\nstart enter > ')

	if False :
		for dir in os.listdir("./"):
			if os.path.isdir(dir) :
				print ("{}===".format(dir) )
			if dir == getUseFolder :
				print('---------------------- {} '.format(getUseFolder))

	if( not os.path.isdir(useFolder) ) :
		print("{} 원고 폴더가 없습니다.".format(useFolder))
		sys.exit()

	#txtFileList = glob.glob(useFolder+'/*.txt')
	fileList = os.listdir(useFolder)
	txtFileList = [file for file in fileList if file.endswith(".txt")]

	if( len(txtFileList) < 1 ):
		print('\n{} 원고 파일이 없습니다.'.format(useFolder))
		sys.exit()

	# 220325
	'''
	if not os.path.isfile(outFile) :
		fp = open(outFile, "w")
		fp.close()
	'''

	#checkFileBlogUrl = []
	#checkBlog = []
	retBlog = []
	outputArray = []

	#check_chromedriver()	# 크롬드라이버 최신 확인 및 다운로드 모듈

	#cacheFolder = os.getcwd() + '\\cache'

	try:
		if not os.path.isdir(cacheFolder):
			os.mkdir(cacheFolder)
	except Exception as e :
		print(format(e))
		time.sleep(5)
		#sys.exit()

	driver = chrome_driver(cacheFolder)
	'''
	chrome_options = Options()
	chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
	chrome_options.add_argument('--user-data-dir=' + cacheFolder)

	if headless == 'N' : #debugFlag:
		chrome_options.add_argument('--window-position=850,0')
	else:
		chrome_options.add_argument('--window-position=850,5000')

	driver = webdriver.Chrome('c:\\chromedriver\\chromedriver.exe', chrome_options=chrome_options)
	'''
	try:
		checkFileCount = 0
		checkFileCount2 = 0
		for txtFile in txtFileList:
			outputLog('원고 : ' + txtFile)
			now = datetime.datetime.now()
			#curDate = now.strftime('%y%m%d')
			checkTime1 = now.strftime('%m.%d %H:%M:%S')
			print('{}  원고 check Start Time : {}'.format(txtFile, checkTime1))

			if debugFlag : print('txtFile : {}'.format(txtFile))
			confirmLine = []
			findBlogList = []
			checkFileBlogUrl = []
			duplicateContentList = []
			checkBlog = []
			wongoFileCheckFlag = False
			tempFile = txtFile.split('\\')

			if len(tempFile) > 2 : fileName = tempFile[2]
			else : fileName = txtFile

			if '@' in txtFile:
				continue
			if 'config.txt' in txtFile:
				continue
			if '설명서' in txtFile:
				continue
			if 'output_' in txtFile:
				continue

			checkFileCount += 1
			if debugFlag : print('\n원고 검사 : {} '.format(txtFile))
			#print(useFolder+'\\'+txtFile)
			try :
				text = open(useFolder+'\\'+txtFile).read().splitlines()
			except Exception as e :
				if debugFlag : print(format(e))
				try:
					print('file open try utf8')
					text = open(useFolder + '\\' + txtFile, 'rt', encoding='utf8').read().splitlines()
				except Exception as e :
					if debugFlag : print(format(e))
					try:
						print('file open try ISO-8859-1')
						text = open(useFolder + '\\' + txtFile, 'rt', encoding='ISO-8859-1').read().splitlines()
					except Exception as e:
						print(format(e))
						driver.quit()
						sys.exit()

			lineNum = 0
			contentTemp = []
			for line in text[1:] :
				# print(line)

				if '**' in line:
					continue
				elif '제목:' in line:
					continue
				elif line == '':
					continue
				elif '안녕하세요' in line:
					continue
				elif '반갑습니다' in line:
					continue
				elif 'http' in line:
					continue
				elif len(line) <= 10:
					continue
				else:
					if line[-1] == ' ': line = line[:-1]
					contentTemp.append(line)
			#contentCheck = random.sample(contentTemp, getRandom)
			if debugFlag : print('contentTemp {} : {}'.format(len(contentTemp), contentTemp))

			#for line in contentCheck :
			for line in contentTemp :
				lineNum += 1
				#if wongoFileCheckFlag :  ## 원고에서 중복 기준값이 넘은 경우
				#	break

				if ' ' in line:
					line2 = line.replace(' ', '+')
				else:
					line2 = line

				now = datetime.datetime.now()
				checkLineTime = now.strftime('%m.%d %H:%M:%S')
				#print('{} check {} : {}'.format(checkLineTime, lineNum, line))
				outputLog('check {} : {}'.format(lineNum, line))

				'''
				blogList = fnFindBlogList(driver, line2)
				if len(findBlogList) > 0 :
					for bUrl in blogList :
						findBlogList.append(bUrl)
				'''
				if debugFlag :
					now = datetime.datetime.now()
					# curDate = now.strftime('%y%m%d')
					checkTime = now.strftime('%m.%d %H:%M:%S')
					print('{} line {}, checkTime 1 : {}'.format(txtFile, lineNum, checkTime))

				try:
					# 0303 수정
					result, findBlogList = fnFindBlogList(driver, line2)
					if result == 999 :
						driver =  chrome_driver(cacheFolder)
						print('chrome start')

					if len(findBlogList) > 0 :
						fnBlogContentCheck(driver, findBlogList, text, txtFile)
						if debugFlag and len(checkBlog) > 0 : print('0 >> checkBlog {}'.format(checkBlog))
				except Exception as e :
					print('오류 발생 --------------------\n{}'.format(e))
					sys.exit()

				if debugFlag :
					now = datetime.datetime.now()
					# curDate = now.strftime('%y%m%d')
					checkTime = now.strftime('%m.%d %H:%M:%S')
					print('{} line {}, checkTime 2 : {}'.format(txtFile, lineNum, checkTime))

			if debugFlag : print('checkFileBlogUrl {}'.format(checkFileBlogUrl))
			if debugFlag : print('1 >> checkBlog {}'.format(checkBlog))
			'''
			if len(checkBlog) > 0 :
				outputArray = outputSave(outFile)
				shutil.move(useFolder+'\\'+fileName, duplicateFolder+'\\'+fileName)
			else:
				print('\n{}  원고에서 중복을 찾지 못했습니다. File Move'.format(fileName))
				shutil.move(useFolder+'\\'+fileName, WongoFolder+fileName)
			'''
			if len(checkBlog) == 0 :
				#print('\n{}  원고에서 중복을 찾지 못했습니다. 원고사용폴더로 이동'.format(fileName))
				shutil.move(useFolder+'\\'+fileName, WongoUseFolder+'\\'+fileName)
				outputLog('{}  원고에서 중복을 찾지 못했습니다. 원고사용폴더로 이동'.format(fileName))
			else:
				checkFileCount2 += 1
				if debugFlag:
					debugLog('total checkBlog \n{}'.format(checkBlog))
					# print('total outputArray \n{}'.format(outputArray))

					print('F1 >> duplicateContentList {}'.format(duplicateContentList))
					print('F1 >> checkFileBlogUrl {}'.format(checkFileBlogUrl))

				for data in duplicateContentList:
					d_url = data[0]
					d_line = data[1]
					#print('중복 확인 url : {}, 중복갯수 : {}'.format(d_url, len(d_line)))
					debugLog('중복 확인 url : {}, 중복갯수 : {}'.format(d_url, len(d_line)))
					if debugFlag : print('d_line : {}'.format(d_line))

				sendData = []

				for i, checkData in enumerate(checkBlog):
					file_name = checkData[0]
					check_blog = checkData[1]
					dup_cnt = checkData[2]
					dup_lineList = duplicateContentList[i][1]
					debugLog('중복 {} >> {} >> {}'.format(i+1, checkData, dup_lineList))

					dup_lines = []
					for line in dup_lineList:
						if line not in dup_lines:
							dup_lines.append(str(line).rstrip().lstrip())

					dupCheckData = {'dup_file': check_blog, 'dupCount': dup_cnt, 'dupList': dup_lines}
					sendData.append(dupCheckData)
					debugLog('sendData {} >> {} >> {}'.format(i+1, checkData, dup_lineList))

					# outFile 중복 결과 저장
					# 220325
					'''
					with open(outFile, 'a') as fp:
						fp.write('{}\t{}\t{}\n'.format(file_name, check_blog, dup_cnt))
						for d_line in dup_lines:
							fp.write('{}\n'.format(d_line))
						fp.write('\n')
					'''
					outputLog('중복 검사 결과 >> {}\t{}\t{}\n'.format(file_name, check_blog, dup_cnt))

				#220323
				dupCheckData = {'req_file': txtFile, 'dupDataCount': len(sendData),'dupDataList': sendData}
				jsonData = json.dumps(dupCheckData, ensure_ascii=False)

				postData = {'action': 'out_wongo_dupDataList_multi', 'wongoDupDataList': jsonData}
				debugLog('out_wongo_dupDataList_multi 자료전송 >> {}'.format(postData))
				res = requests.post(serverURL, data=postData)
				debugLog('out_wongo_dupDataList_multi >> res.text >> {}'.format(res.text))

				#wongo_data = open(useFolder + '\\' + txtFile).read()
				wongo_data = '\n'.join(text)
				debugLog('txtFile >> {}'.format(useFolder + '\\' + txtFile))
				dupCheckData = {'wongo_file': txtFile, 'title': '', 'wongo_data': wongo_data}
				jsonData = json.dumps(dupCheckData, ensure_ascii=False)

				postData = {'action': 'out_wongo_dup_data_save', 'outWongoData': jsonData}
				debugLog('out_wongo_dup_data_save 자료전송 >> {}'.format(postData))
				res = requests.post(serverURL, data=postData)
				debugLog('out_wongo_dup_data_save >> {} >> res.text >> {}'.format(txtFile, res.text))

				# 220325
				'''
				with open(outFile, 'a') as fp:
					fp.write('-' * 90)
					fp.write('\n')
				'''

				shutil.move(useFolder + '\\' + file_name, duplicateFolder + '\\' + file_name)
				#print('파일 이동 : {}'.format(duplicateFolder + '\\' + file_name))
				debugLog('중복원고 파일 이동 >> ' + useFolder + '\\' + file_name +' ===> '+  duplicateFolder + '\\' + file_name)
				outputLog('원고 중복 확인, 중복원고 저장폴더로 파일 이동 : {}'.format(duplicateFolder + '\\' + file_name))

			if True :
				now = datetime.datetime.now()
				checkTime2 = now.strftime('%m.%d %H:%M:%S')
				print('원고  : {}'.format(txtFile))
				print('{} check Start Time : {}'.format(txtFile, checkTime1))
				print('{} check end   Time : {}'.format(txtFile, checkTime2))
				#input('2 enter >')

		# for txtFileList end

		now = datetime.datetime.now()
		# curDate = now.strftime('%y%m%d')
		checkTime = now.strftime('%m.%d %H:%M:%S')
		print('checkTime : {}'.format(checkTime))

		if checkFileCount <= 0 :
			print("\n{} 원고가 없습니다.".format(useFolder))
		else :
			#print('\n{} 원고폴더, {} 개 원고 검사, {} 개 원고 중복 '.format(getUseFolder, checkFileCount, checkFileCount2) )
			outputLog('중복 확인된 원고 결과 확인 : {}'.format(outFile))
			#print('원고 파일에서 랜덤으로 %d 개 라인을 추출해서 검사' % getRandom )
			outputLog('{} 원고폴더, {} 개 원고 검사, {} 개 원고 중복 '.format(getUseFolder, checkFileCount, checkFileCount2) )

		driver.quit()
	except Exception as e:
		print('Exception 99 -----------\n{}'.format(e) )
		driver.quit()

	print('\n프로그램 종료 !!\n\n')

