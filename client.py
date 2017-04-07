import curses
import string
import sys
import threading
from maps import Map, ChunkMap
from clientchunkpool import ClientChunkPool

# import fron chunks, maps, clientchunkpool

class Client():
	def __init__(self, address):
		self.stopping = False
		self.chunkmap_active = False
		
		self.address = address
		self.drawevent = threading.Event()
		self.pool = ClientChunkPool()
		#self.map_ = Map(sizex, sizey, self.pool)
		#self.chunkmap = Chunkmap(sizex, sizey, self.pool) # size changeable by +/-?
		
		#self.sock = socket.Socket(...)
	
	def launch(self, stdscr):
		sizey, sizex = stdscr.getmaxyx()
		self.map_ = Map(sizex, sizey, self.pool, self.drawevent)
		self.chunkmap = ChunkMap(self.map_)
		
		# start input thread
		self.inputthread = threading.Thread(
			target=self.input_thread,
			name="inputthread",
			args=(stdscr,),
			daemon=True
		)
		self.inputthread.start()
		
		while not self.stopping:
			self.drawevent.wait()
			stdscr.noutrefresh()
			with self.map_ as m:
				m.draw()
				
				if self.chunkmap_active:
					self.chunkmap.draw()
					curses.curs_set(False)
				else:
					curses.curs_set(True)
				
				#m.update_cursor()
				#m.noutrefresh()
			
			curses.doupdate()
			self.drawevent.clear()
	
	def input_thread(self, scr):
		while True:
			i = scr.getkey()
			
			if   i == "\x1b": self.stop()
			elif i == "KEY_F(2)":
				self.chunkmap_active = not self.chunkmap_active
				self.drawevent.set()
			elif i == "KEY_F(5)": self.map_.redraw()
			# scrolling the map (10 vertical, 20 horizontal)
			elif i == "kUP5":  self.map_.scroll(0, -10)
			elif i == "kDN5":  self.map_.scroll(0, 10)
			elif i == "kLFT5": self.map_.scroll(-20, 0)
			elif i == "kRIT5": self.map_.scroll(20, 0)
			
			# break here if chunkmap is shown: Don't allow for cursor movement or input
			elif self.chunkmap_active: pass
		
			# quick cursor movement (5 vertical, 10 horizontal)
			elif i == "KEY_SR":     self.map_.move_cursor(0, -5)
			elif i == "KEY_SF":     self.map_.move_cursor(0, 5)
			elif i == "KEY_SLEFT":  self.map_.move_cursor(-10, 0)
			elif i == "KEY_SRIGHT": self.map_.move_cursor(10, 0)
			# normal cursor movement
			elif i == "KEY_UP":     self.map_.move_cursor(0, -1)
			elif i == "KEY_DOWN":   self.map_.move_cursor(0, 1)
			elif i == "KEY_LEFT":   self.map_.move_cursor(-1, 0)
			elif i == "KEY_RIGHT":  self.map_.move_cursor(1, 0)
			# edit world
			elif i in string.digits + string.ascii_letters + string.punctuation + " ":
				self.map_.write(i)
			elif i == "\x7f": self.map_.delete()
			elif i == "\n":   self.map_.newline()
			
			else: sys.stdout.write(repr(i) + "\n")
	
	def stop(self):
		self.stopping = True
		self.drawevent.set()

def main(argv):
	if len(argv) != 2:
		print("Usage:")
		print("  {} address".format(argv[0]))
		return
	
	client = Client(argv[1])
	curses.wrapper(client.launch)

if __name__ == "__main__":
	main(sys.argv)
