import curses
import json
import os
import string
import sys
import threading
import time
import websocket
from websocket import WebSocketException as WSException

from maps import Map, ChunkMap
from chunks import ChunkDiff, jsonify_diffs, dejsonify_diffs
from utils import Position
from clientchunkpool import ClientChunkPool

class Client():
	MOVE_NORMAL = 0
	MOVE_FAST = 1
	MOVE_MAP = 2
	
	def __init__(self, address, port=None, logfile=None):
		self.stopping = False
		self.movement = self.MOVE_NORMAL
		
		self.map_ = None
		self.chunkmap = None
		self.chunkmap_active = False
		
		#self.address = f"ws://{address}:{port}/"
		self.address = "ws://{}:{}/".format(address, port)
		self._drawevent = threading.Event()
		self.pool = ClientChunkPool(self)
		
		self.logfile = logfile
		self.log_messages = []
	
	def launch(self, stdscr):
		# connect to server
		try:
			self._ws = websocket.create_connection(
				self.address,
				enable_multithread=True
			)
		except:
			#sys.stderr.write(f"Could not connect to server: {self.address!r}\n")
			sys.stderr.write("Could not connect to server: {!r}\n".format(self.address))
			return
		
		# create map etc.
		sizey, sizex = stdscr.getmaxyx()
		self.map_ = Map(sizex, sizey, self.pool, self)
		self.chunkmap = ChunkMap(self.map_)
		
		# start connection thread
		self.connectionthread = threading.Thread(
			target=self.connection_thread,
			name="connectionthread"
		)
		self.connectionthread.start()
		
		# start input thread
		self.inputthread = threading.Thread(
			target=self.input_thread,
			name="inputthread",
			args=(stdscr,),
			daemon=True
		)
		self.inputthread.start()
		
		while not self.stopping:
			self.update_screen()
		
		if self.logfile:
			self.save_log(self.logfile)
	
	def update_screen(self):
		self._drawevent.wait()
		self._drawevent.clear()
		
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
	
	def redraw(self):
		self._drawevent.set()
	
	def log(self, message):
		if self.logfile:
			self.log_messages.append(message)
	
	def save_log(self, filename):
		with open(filename, "a") as f:
			#f.write(f"[[[ {int(time.time())} ]]]\n")
			f.write("[[[ {} ]]]\n".format(int(time.time())))
			for msg in self.log_messages:
				f.write(msg + "\n")
	
	def move(self, x, y, mode):
		if mode == self.MOVE_NORMAL:
			self.map_.move_cursor(x, y)
		elif mode == self.MOVE_FAST:
			self.map_.move_cursor(x*10, y*5)
		elif mode == self.MOVE_MAP:
			self.map_.scroll(x*20, y*10)
	
	def handle_input(self, i):
		if   i == "\x1b": self.stop()
		elif i == curses.KEY_F1: self.movement = self.MOVE_NORMAL
		elif i == curses.KEY_F2: self.movement = self.MOVE_FAST
		elif i == curses.KEY_F3: self.movement = self.MOVE_MAP
		
		elif i == curses.KEY_F5:
			self.map_.redraw()
		elif i == curses.KEY_F6 or i == curses.KEY_F4: # real map will later toggle on F4
			self.chunkmap_active = not self.chunkmap_active
			self.redraw()
		elif i == curses.KEY_F7:
			self.map_.alternating_colors = not self.map_.alternating_colors
			self.redraw()
		elif i == curses.KEY_F10: self.map_.set_cursor(0, 0)
		
		# scrolling the map (10 vertical, 20 horizontal)
		elif i in [569,566]: self.move( 0, -1, self.MOVE_MAP) # ctrl + up
		elif i in [528,525]: self.move( 0,  1, self.MOVE_MAP)  # ctrl + down
		elif i in [548,545]: self.move(-1,  0, self.MOVE_MAP) # ctrl + left
		elif i in [563,560]: self.move( 1,  0, self.MOVE_MAP)  # ctrl + right
		
		# break here if chunkmap is shown: Don't allow for cursor movement or input
		elif self.chunkmap_active and self.movement != self.MOVE_MAP: pass
		
		# quick cursor movement (5 vertical, 10 horizontal)
		elif i == curses.KEY_SR:     self.move( 0, -1, self.MOVE_FAST)  # shift + up, 337
		elif i == curses.KEY_SF:     self.move( 0,  1, self.MOVE_FAST)   # shift + down, 336
		elif i == curses.KEY_SLEFT:  self.move(-1,  0, self.MOVE_FAST) # shift + left, 393
		elif i == curses.KEY_SRIGHT: self.move( 1,  0, self.MOVE_FAST)  # shift + right, 402
		# normal cursor movement
		elif i == curses.KEY_UP:    self.move( 0, -1, self.movement)
		elif i == curses.KEY_DOWN:  self.move( 0,  1, self.movement)
		elif i == curses.KEY_LEFT:  self.move(-1,  0, self.movement)
		elif i == curses.KEY_RIGHT: self.move( 1,  0, self.movement)
		# edit world
		elif i == "\x7f": self.map_.delete()
		elif i == "\n":   self.map_.newline()
		#elif i in string.digits + string.ascii_letters + string.punctuation + " ":
			#self.map_.write(i)
		elif isinstance(i, str) and len(i) == 1 and ord(i) > 31 and (i not in string.whitespace or i == " "):
			self.map_.write(i)
	
	def input_thread(self, scr):
		while True:
			i = scr.get_wch()
			self.handle_input(i)
			#self.log(f"K: {i!r}")
			self.log("K: {!r}".format(i))
	
	def connection_thread(self):
		try:
			while True:
				j = self._ws.recv()
				if j:
					self.handle_json(json.loads(j))
		except (WSException, ConnectionResetError, OSError):
			self._ws = None
			self.stop()
			return
	
	def handle_json(self, message):
		if message["type"] == "apply-changes":
			diffs = dejsonify_diffs(message["data"])
			self.map_.commit_diffs(diffs)
	
	def stop(self):
		self.stopping = True
		if self._ws:
			self._ws.close()
			self._ws = None
		self.redraw()

	def request_chunks(self, coords):
		message = {"type": "request-chunks", "data": coords}
		self._ws.send(json.dumps(message))
	
	def unload_chunks(self, coords):
		message = {"type": "unload-chunks", "data": coords}
		self._ws.send(json.dumps(message))
	
	def send_changes(self, diffs):
		diffs = jsonify_diffs(diffs)
		message = {"type": "save-changes", "data": diffs}
		self._ws.send(json.dumps(message))

def main(argv):
	if len(argv) == 1 or len(argv) > 4:
		print("Usage:")
		#print(f"  {argv[0]} address [port [logfile]]")
		print("  {} address [port [logfile]]".format(argv[0]))
		print("  default port: 8000")
		return
	
	address = argv[1]
	
	if len(argv) >= 3:
		try:
			port = int(argv[2])
		except ValueError:
			print("Invalid port")
			return
	else:
		port = 8000
	
	# only for debugging, will be removed later
	if len(argv) >= 4:
		logfile = argv[3]
	else:
		logfile = None
	
	os.environ.setdefault('ESCDELAY', '25') # only a 25 millisecond delay
	
	client = Client(address, port, logfile)
	curses.wrapper(client.launch)

if __name__ == "__main__":
	main(sys.argv)
