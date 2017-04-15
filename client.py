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
	def __init__(self, address, logfile=None):
		self.stopping = False
		
		self.map_ = None
		self.chunkmap = None
		self.chunkmap_active = False
		
		self.address = f"ws://{address}/"
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
			sys.stderr.write(f"Could not connect to server: {self.address!r}\n")
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
		
		# update screen until stopped
		while not self.stopping:
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
		
		if self.logfile:
			self.save_log(self.logfile)
	
	def redraw(self):
		self._drawevent.set()
	
	def log(self, message):
		if self.logfile:
			self.log_messages.append(message)
	
	def save_log(self, filename):
		with open(filename, "a") as f:
			f.write(f"[[[ {int(time.time())} ]]]\n")
			for msg in self.log_messages:
				f.write(msg + "\n")
	
	def input_thread(self, scr):
		while True:
			i = scr.get_wch()
			
			if   i == "\x1b": self.stop()
			elif i == curses.KEY_F2:
				self.chunkmap_active = not self.chunkmap_active
				self.redraw()
			elif i == curses.KEY_F3:
				self.map_.alternating_colors = not self.map_.alternating_colors
				self.redraw()
			elif i == curses.KEY_F5:
				self.map_.redraw()
			# scrolling the map (10 vertical, 20 horizontal)
			elif i in [569,566]: self.map_.scroll(0, -10) # ctrl + up
			elif i in [528,525]: self.map_.scroll(0, 10)  # ctrl + down
			elif i in [548,545]: self.map_.scroll(-20, 0) # ctrl + left
			elif i in [563,560]: self.map_.scroll(20, 0)  # ctrl + right
			
			# break here if chunkmap is shown: Don't allow for cursor movement or input
			elif self.chunkmap_active: pass
		
			# quick cursor movement (5 vertical, 10 horizontal)
			elif i == curses.KEY_SR: self.map_.move_cursor(0, -5)  # shift + up, 337
			elif i == curses.KEY_SF: self.map_.move_cursor(0, 5)   # shift + down, 336
			elif i == curses.KEY_SLEFT : self.map_.move_cursor(-10, 0) # shift + left, 393
			elif i == curses.KEY_SRIGHT: self.map_.move_cursor(10, 0)  # shift + right, 402
			# normal cursor movement
			elif i == curses.KEY_UP   : self.map_.move_cursor(0, -1)
			elif i == curses.KEY_DOWN : self.map_.move_cursor(0, 1)
			elif i == curses.KEY_LEFT : self.map_.move_cursor(-1, 0)
			elif i == curses.KEY_RIGHT: self.map_.move_cursor(1, 0)
			# edit world
			elif i == "\x7f": self.map_.delete()
			elif i == "\n":   self.map_.newline()
			#elif i in string.digits + string.ascii_letters + string.punctuation + " ":
				#self.map_.write(i)
			elif isinstance(i, str) and len(i) == 1 and ord(i) > 31 and (i not in string.whitespace or i == " "):
				self.map_.write(i)
			
			self.log(f"K: {i!r}")
	
	def connection_thread(self):
		while True:
			try:
				j = self._ws.recv()
				if j:
					self.handle_json(json.loads(j))
			except (WSException, ConnectionResetError, OSError):
				#self.stop()
				return
	
	def handle_json(self, message):
		if message["type"] == "apply-changes":
			diffs = dejsonify_diffs(message["data"])
			self.map_.commit_diffs(diffs)
	
	def stop(self):
		self.stopping = True
		self._ws.close()
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
	if len(argv) == 2:
		client = Client(argv[1])
	elif len(argv) == 3:
		client = Client(argv[1], argv[2])
	else:
		print("Usage:")
		print(f"  {argv[0]} address [logfile]")
		return
	
	os.environ.setdefault('ESCDELAY', '25') # only a 25 millisecond delay
	
	curses.wrapper(client.launch)

if __name__ == "__main__":
	main(sys.argv)
