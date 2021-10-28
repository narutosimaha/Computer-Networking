from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, os
from RtpPacket import RtpPacket
from VideoStream import  VideoStream
from datetime import timedelta
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

    # Initiation
    # THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI
    def createWidgets(self):
        """Build GUI."""
        # Create Setup button
        self.setup = Button(self.master, width=20, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.setupMovie
        self.setup.grid(row=1, column=0, padx=2, pady=2)

        # Create Play button
        self.start = Button(self.master, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)

        # Create Pause button
        self.pause = Button(self.master, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=2, padx=2, pady=2)

        # Create Teardown button
        self.teardown = Button(self.master, width=20, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] = self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        self.fastfoward = Button(self.master, width=20, padx=3, pady=3)
        self.fastfoward["text"] = "FastForward"
        self.fastfoward["command"] = self.fastForward
        self.fastfoward.grid(row=1, column=4, padx=2, pady=2)

        self.backward = Button(self.master, width=20, padx=3, pady=3)
        self.backward["text"] = "Backward"
        self.backward["command"] = self.fastBackward
        self.backward.grid(row=1, column=5, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W + E + N + S, padx=5, pady=5)

    def setupMovie(self):
        """Setup button handler."""
        # TODO
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        """Teardown button handler."""
        # TODO
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy() # Exit GUI window
        os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete cache

    def pauseMovie(self):
        """Pause button handler."""
        # TODO
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        # TODO
        if self.state == self.READY:
            threading.Thread(target = self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)

    def listenRtp(self):
        """Listen for RTP packets."""
        # TODO
        while True:
            try:
                print("LISTENING...")
                reply = self.rtpSocket.recv(20480)
                if reply:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(reply)
                    currFrameNum = rtpPacket.seqNum()
                    print("CURRENT FRAME NUMBER: " + str(currFrameNum))

                    if currFrameNum > self.frameNbr:
                        self.frameNbr = currFrameNum
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
            except:
                # Stop listening when requesting PAUSE or TEARDOWN
                if self.playEvent.isSet():
                    break
                # Upon receiving ACK for TEARDOWN request, close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        # TODO
        """Write the received frame to a temp image file. Return the image file."""
        cache_name = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(cache_name, "wb")
        file.write(data)
        file.close()
        return cache_name

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        # TODO
        photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image=photo, height=288)
        self.label.image = photo

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        # TODO
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET: ipv4, SOCK_STREAM: TCP
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            tkinter.messagebox.showwarning('Connection Failed', "Connection to '%s' failed" % self.serverAddr)

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""

        # -------------
        # TO COMPLETE
        # -------------

        # 1.SETUP REQUEST
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(name='Setup_thread', target=self.recvRtspReply).start()
            # Update RTSP sequence number
            self.rtspSeq += 1
            # Display the RTSP request
            disp = "%s %s %s" % (self.SETUP_STR, self.fileName, self.RTSP_VER)
            disp += "\nCSeq: %d" % self.rtspSeq
            disp += "\nTransport: %s; client_port= %d" % (self.TRANSPORT, self.rtpPort)
            # Keep track of sent request
            self.requestSent = self.SETUP
        # 2.PLAY REQUEST
        elif requestCode == self.PLAY and self.state == self.READY:
            # Update RTSP sequence number
            self.rtspSeq += 1
            # Display the RTSP request
            disp = "%s %s %s" % (self.PLAY_STR, self.fileName, self.RTSP_VER)
            disp += "\nCSeq: %d" % self.rtspSeq
            disp += "\nSession: %d" % self.sessionId
            # Keep track of sent request
            self.requestSent = self.PLAY
        # 3.PAUSE REQUEST
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            # Update RTSP sequence number
            self.rtspSeq += 1
            # Display the RTSP request
            disp = "%s %s %s" % (self.PAUSE_STR, self.fileName, self.RTSP_VER)
            disp += "\nCSeq: %d" % self.rtspSeq
            disp += "\nSession: %d" % self.sessionId
            # Keep track of sent request
            self.requestSent = self.PAUSE
        # 4.TEARDOWN REQUEST
        elif requestCode == self.TEARDOWN and self.state != self.INIT:
            # Update RTSP sequence number
            self.rtspSeq += 1
            # Display the RTSP request
            disp = "%s %s %s" % (self.TEARDOWN_STR, self.fileName, self.RTSP_VER)
            disp += "\nCSeq: %d" % self.rtspSeq
            disp += "\nSession: %d" % self.sessionId
            # Keep track of sent request
            self.requestSent = self.TEARDOWN
        # 5. FASTFORWARD REQUEST
        elif requestCode == self.FASTFORWARD and self.state == self.PLAYING:
            # Update RTSP sequence number
            self.rtspSeq += 1
            # Display the RTSP request
            disp = "%s %s %s" % (self.FASTFORWARD_STR, self.fileName, self.RTSP_VER)
            disp += "\nCSeq: %d" % self.rtspSeq
            disp += "\nSession: %d" % self.sessionId
            # Keep track of sent request
            self.requestSent = self.FASTFORWARD
        # 6. BACKWARD REQUEST
        elif requestCode == self.BACKWARD and self.state == self.PLAYING:
            # Update RTSP sequence number
            self.rtspSeq += 1
            # Display the RTSP request
            disp = "%s %s %s" % (self.BACKWARD_STR, self.fileName, self.RTSP_VER)
            disp += "\nCSeq: %d" % self.rtspSeq
            disp += "\nSession: %d" % self.sessionId
            # Keep track of sent request
            self.requestSent = self.BACKWARD
        else:
            return
        self.rtspSocket.send(disp.encode())
        print('\nClient->Sever: \n' + disp)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        # TODO
        while True:
            reply = self.rtspSocket.recv(1024)  # 1024: Maximum amount of data to be received at once
            # return value is a bytes object representing the data received
            if reply:
                self.parseRtspReply(reply)
            # Close RTSP socket when requesting TEARDOWN
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        info = data.decode().split('\n')
        seqNum = int(info[1].split(' ')[1])
        # Check if reply seqNum same as rtspSeq request
        if seqNum == self.rtspSeq:
            session = int(info[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session
            # If sessionID is same as session
            if self.sessionId == session:
                if int(info[0].split(' ')[1]) == 200:
                    if self.requestSent == self.SETUP:
                        self.state = self.READY
                        self.openRtpPort()
                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        # Create new thread on resume
                        self.playEvent.set()
                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        # Flag to close the socket
                        self.teardownAcked = 1
                    elif self.requestSent == self.FASTFORWARD:
                        self.state = self.PLAYING
                    elif self.requestSent == self.BACKWARD:
                        self.state = self.PLAYING

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
    # -------------
    # TO COMPLETE
    # -------------
    # Create a new datagram socket to receive RTP packets from the server
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # AF_INET: ipv4, SOCK_DGRAM: UDP
    # Set the timeout value of the socket to 0.5sec
        self.rtpSocket.settimeout(0.5)
        try:
            # Bind the socket to the address using the RTP port given by the client user.
            self.state = self.READY
            self.rtpSocket.bind(('', self.rtpPort))
        except:
            tkinter.messagebox.showwarning('Bind Failed', 'Unable to bind PORT = %d' % self.rtpPort)


    def handler(self):
        """Handler on explicitly closing the GUI window."""
    # TODO
        self.pauseMovie()
        if tkinter.messagebox.askokcancel('Quit?', 'Do you want to quit?'):
            self.exitClient()
        else: # User press "cancel", resume playing
            self.playMovie()

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
