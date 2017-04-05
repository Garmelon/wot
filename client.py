import curses
import sys
import threading
from maps import Map
from chunks import ChunkPool

# import fron chunks, maps, clientchunkpool

class Client():
	def __init__(self, address):
		self.address = address
		self.pool = ChunkPool()
		#self.map_ = Map(sizex, sizey, self.pool)
		#self.chunkmap = Chunkmap(sizex, sizey, self.pool) # size changeable by +/-?
		
		#self.sock = socket.Socket(...)
	
	def launch(self, stdscr):
		sizey, sizex = stdscr.getmaxyx()
		self.map_ = Map(sizex, sizey, self.pool)
		
		stdscr.noutrefresh()
		self.map_.draw()
		curses.doupdate()
		stdscr.getkey()
		self.map_.worldx += 1
		self.map_.cursorx += 2
		self.map_.cursory += 1
		stdscr.noutrefresh()
		self.map_.draw()
		curses.doupdate()
		stdscr.getkey()
	
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
	curses.wrapper(client.launch)

if __name__ == "__main__":
	main(sys.argv)
