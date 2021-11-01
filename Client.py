from tkinter import *
import tkinter.messagebox
import time
tkinter.messagebox
from tkinter import messagebox 
tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

from RtpPacket import RtpPacket
from VideoStream import  VideoStream
from datetime import timedelta

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"
CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:

	SETUP_STR = 'SETUP'
	PLAY_STR = 'PLAY'
	PAUSE_STR = 'PAUSE'
	TEARDOWN_STR = 'TEARDOWN'
	FASTFORWARD_STR = 'FASTFORWARD'
	BACKWARD_STR = 'BACKWARD'

	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	
	FASTFORWARD = 4
	BACKWARD = 5
	
	RTSP_VER = "RTSP/1.0"
	TRANSPORT = "RTP/UDP"
	
	second = 0
	minute = 0
	hour = 0
	totalTime = 0
	
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		
	def createWidgets(self):
		"""Build GUI."""

		# Create Previous button
		self.previd = PhotoImage(file ="icon/previous_video.png")
		self.start = Button(self.master, width=100, padx=3, pady=3, bd= 0)
		self.start['image'] = self.previd
		self.start["command"] = self.preMovie
		self.start.grid(row=0, column=0, columnspan = 1, padx=2, pady=2)


		# Create FastBackward button
		self.imageleft = PhotoImage(file ="icon/left.png")
		self.start = Button(self.master, width=100, padx=3, pady=3, bd= 0)
		self.start['image'] = self.imageleft
		self.start["command"] = self.fastBackward
		self.start.grid(row=1, column=0, columnspan = 1, padx=2, pady=2)
		
		# Create Time increase button
		self.Timelabel = Label(self.master, width = 5, padx=3, pady=3, bd = 0, text = "00: 00")
		self.Timelabel.grid(row=1, column=1, columnspan=1, padx=2, pady=2) 
		
		# Create Play button		
		self.image = PhotoImage(file ="icon/play.png")
		self.pause = Button(self.master, width=100, padx=2, pady=3, bd = 0)
		self.pause['image'] = self.image
		self.pause["command"] = self.setupAndPlay
		self.pause.grid(row=1, column=2, columnspan = 2, padx=2, pady=2)
		

		# Create Total time button
		self.Totallabel = Label(self.master,width = 5, padx=3, pady=3, bd = 0, text = "00:00")
		self.Totallabel.grid(row=1, column=4, columnspan=1, padx=2, pady=2) 

		# Create Fastforward button
		self.imageright = PhotoImage(file ="icon/right.png")
		self.teardown = Button(self.master,width=100, padx=3, pady=3, bd = 0)
		self.teardown['image'] = self.imageright
		self.teardown["command"] =  self.fastForward
		self.teardown.grid(row=1, column=5, columnspan = 1, padx=2, pady=2)

		# Create Next button
		self.nextvid = PhotoImage(file ="icon/next_video.png")
		self.start = Button(self.master, width=100, padx=5, pady=5, bd= 0)
		self.start['image'] = self.nextvid
		self.start["command"] = self.nextMovie
		self.start.grid(row=0, column=5,columnspan = 1,  padx=2, pady=2)

		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=1, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
	

	def showtime(self):
		# self.second = time.strftime("%S")
		if self.state == self.PLAYING:
			self.second +=1
			self.Timelabel.config(text = "00 :" + self.second)
		self.totalTime = self.getDurationTime()
		self.Totallabel = self.config(text = "00 :" + self.totalTime)

	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)
	
	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)		
		self.master.destroy() # Close the gui window
		os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	
	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			self.threadlisten = threading.Thread(target=self.listenRtp)
			self.threadlisten.start()
			self.playEvent = threading.Event()
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)
	
	def listenRtp(self):		
		"""Listen for RTP packets."""
		while True:
			try:
				print("LISTENING...")
				data = self.rtpSocket.recv(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					
					currFrameNbr = rtpPacket.seqNum()
					print ("CURRENT SEQUENCE NUM: " + str(currFrameNbr))
										
					if currFrameNbr > self.frameNbr: # Discard the late packet
						self.frameNbr = currFrameNbr
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
			except:
				# Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet(): 
					break
				
				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		
		return cachename
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile))

		if self.state == self.PLAYING:
			self.second +=1
			self.second_ = int(self.second/25)
			if(self.second_ >60):
				self.second_ = 0
				self.minutes += 1
				if(self.minute > 60):
					self.hour += 1
			


			self.Timelabel.config(text = "00 :"+ str(self.second_))

		self.totalTime =self.getDurationTime()
		self.Totallabel.config(text = self.totalTime)

		self.label.configure(image = photo, height=288) 
		self.label.image = photo
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		#-------------
		# TO COMPLETE
		#-------------
		
		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			self.threadrecv = threading.Thread(target=self.recvRtspReply)
			self.threadrecv.start()
				
			# Update RTSP sequence number.
			self.rtspSeq+=1
			
			# Write the RTSP request to be sent.
			request = "%s %s %s" % (self.SETUP_STR,self.fileName,self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nTransport: %s; client_port= %d" % (self.TRANSPORT,self.rtpPort)
			
			# Keep track of the sent request.
			self.requestSent = self.SETUP
			
			# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP sequence number.
			self.rtspSeq+=1
		
			# Write the RTSP request to be sent.
			request = "%s %s %s" % (self.PLAY_STR,self.fileName,self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d"%self.sessionId
				
			
			# Keep track of the sent request.
			self.requestSent = self.PLAY
			
			
			# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
		
			# Update RTSP sequence number.
			self.rtspSeq+=1
			
			request = "%s %s %s" % (self.PAUSE_STR,self.fileName,self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d"%self.sessionId
			
			self.requestSent = self.PAUSE
			
			# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
		
			# Update RTSP sequence number.
			self.rtspSeq+=1
			
			# Write the RTSP request to be sent.
			request = "%s %s %s" % (self.TEARDOWN_STR, self.fileName, self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d" % self.sessionId
			
			self.requestSent = self.TEARDOWN

		else:
			return
		
		# Send the RTSP request using rtspSocket.
		self.rtspSocket.send(request.encode())
		
		print ('\nData Sent:\n' + request)
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)
			
			if reply: 
				self.parseRtspReply(reply)
			
			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		lines = data.decode().split('\n')
		seqNum = int(lines[1].split(' ')[1])
		
		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session
			
			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200: 
					if self.requestSent == self.SETUP:
						
						# Update RTSP state.
						self.state = self.READY
						print("state in parse reply_rtsp is", self.state)
						
						# Open RTP port.
						self.openRtpPort() 
						threading.Thread(target=self.playMovie).start()
					elif self.requestSent == self.PLAY:
						self.state = self.PLAYING
					elif self.requestSent == self.PAUSE:
						self.state = self.READY
						# The play thread exits. A new thread is created on resume.
						self.playEvent.set()
					elif self.requestSent == self.TEARDOWN:
						self.state = self.INIT
						
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1 
	
	def openRtpPort(self):
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.rtpSocket.settimeout(0.5)
		
		try:
			self.state=self.READY
			self.rtpSocket.bind(('',self.rtpPort))
		except:
			messagebox.showwarning('Lỗi', 'Không thể kết nối với PORT=%d' %self.rtpPort)

	def handler(self):
		self.pauseMovie()
		if messagebox.askokcancel("Quit ?", "Are you sure want to quit ? "):
			self.exitClient()
		else: 
			self.playMovie()

	def setupAndPlay(self):
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)
		elif self.state ==  self.READY:
			self.playMovie()
		elif self.state == self.PLAYING:
			self.pauseMovie()

	def getNextFileName(self, oldFileName):
		nextFileName = oldFileName
		firstFileName = oldFileName
		list_file = os.listdir()
		flag = False
		first = False
		for fileNamee in list_file:
			if(".Mjpeg" in fileNamee and first == False):
				firstFileName = fileNamee
				first = True
			if(".Mjpeg" in fileNamee and fileNamee == oldFileName):
				flag = True
			elif(".Mjpeg" in fileNamee and flag == True):
				nextFileName = fileNamee
				break
		if nextFileName == oldFileName:
			return firstFileName
		return nextFileName

	def getPreFileName(self, oldFileName):
		nextFileName = oldFileName
		firstFileName = oldFileName
		list_file = os.listdir()
		list_file.reverse()
		flag = False
		first = False
		for fileNamee in list_file:
			if(".Mjpeg" in fileNamee and first == False):
				firstFileName = fileNamee
				first = True
			if(".Mjpeg" in fileNamee and fileNamee == oldFileName):
				flag = True
			elif(".Mjpeg" in fileNamee and flag == True):
				nextFileName = fileNamee
				break
		if nextFileName == oldFileName:
			return firstFileName
		return nextFileName

	def nextMovie(self):
		if self.state != self.INIT:
			self.pauseMovie()
			self.sendRtspRequest(self.TEARDOWN)
			self.state = self.INIT
			self.threadlisten.join()
			self.threadrecv.join()
			os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)
			self.fileName = self.getNextFileName(self.fileName)
			self.rtspSeq = 0
			self.sessionId = 0
			self.requestSent = -1
			self.teardownAcked = 0
			self.connectToServer()
			self.frameNbr = 0
			self.totalTime = 0
			self.second = 0 
		else:
			self.fileName = self.getNextFileName(self.fileName)

	def preMovie(self):
		if self.state != self.INIT:
			self.pauseMovie()
			self.sendRtspRequest(self.TEARDOWN)
			self.state = self.INIT
			self.threadlisten.join()
			self.threadrecv.join()
			os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)
			self.fileName = self.getPreFileName(self.fileName)
			self.rtspSeq = 0
			self.sessionId = 0
			self.requestSent = -1
			self.teardownAcked = 0
			self.totalTime = 0
			self.second = 0 
			self.connectToServer()
			self.frameNbr = 0
		else:
			self.fileName = self.getPreFileName(self.fileName)

	def getDurationTime(self):
		# Get duration of video
		video = VideoStream(self.fileName)
		while video.nextFrame():
			pass
		totalFrame = video.frameNbr()
		fps = 25 # Declare in ServerWorker.py sendRtp() function | fps = 1/0.04
		seconds = totalFrame / fps
		video_time = str(timedelta(seconds=seconds))
		return video_time

	def fastForward(self):
		# default is fastForward 3s
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.FASTFORWARD)

	def fastBackward(self):
		# default is fastBackward 3s
		frame_return = 3 * 25
		if self.state == self.PLAYING:
			if self.frameNbr <= frame_return:
				self.frameNbr = 0
			else:
				self.frameNbr -= frame_return
			self.sendRtspRequest(self.BACKWARD)

			
