import sys
import threading

class Client():
	def __init__(self, address):
		self.address = address
		self.clock = threading.RLock()
		#self.pool = Chunkpool()
		#self.map_ = Map(sizex, sizey, self.pool)
		#self.chunkmap = Chunkmap(sizex, sizey, self.pool) # size changeable by +/-?
		
		#self.sock = socket.Socket(...)
	
	def launch(self):
		# try to connect
		# launch socket thread
		# update display
		# -> launch input thread
	
	def get_input(self, scr):
		pass
	
	def stop(self):
		pass

def main(argv):
	if len(argv) != 2:
		print("Usage:")
		print("  {} address".format(argv[0]))
		return
	
	client = Client(argv[1])
	client.launch()

if __name__ == "__main__":
	main(sys.argv)
