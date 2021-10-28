import sys, socket

from ServerWorker import ServerWorker

class Server:	
	
	def main(self):
		try:
			SERVER_PORT = int(sys.argv[1])
		except:
			print("[Usage: Server.py Server_port]\n")
		rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		rtspSocket.bind(('', SERVER_PORT))
		rtspSocket.listen(5)        

		# Receive client info (address,port) through RTSP/TCP session
		while True:
			clientInfo = {}	#Dictionary
			clientInfo['rtspSocket'] = rtspSocket.accept()
			# Return value of rtspSocket.accept() is a pair (conn, address)
			# conn is a new socket object usable to send and receive data on the connection
			# address is the address bound to the socket on the other end of the connection
			ServerWorker(clientInfo).run()

if __name__ == "__main__":
	(Server()).main()


