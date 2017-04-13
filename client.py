import curses
import json
import os
import string
import sys
import threading
import websocket
from websocket import WebSocketException as WSException

from maps import Map, ChunkMap
from chunks import ChunkDiff
from utils import Position
from clientchunkpool import ClientChunkPool

class Client():
	def __init__(self, address):
		self.stopping = False
		self.chunkmap_active = False
		
		self.address = f"ws://{address}/"
		self._drawevent = threading.Event()
		self.pool = ClientChunkPool(self)
		#self.map_ = Map(sizex, sizey, self.pool)
		#self.chunkmap = Chunkmap(sizex, sizey, self.pool) # size changeable by +/-?
		
		#self.sock = socket.Socket(...)
	
	def launch(self, stdscr):
		# connect to server
		try:
			self._ws = websocket.create_connection(
				self.address,
				enable_multithread=True
			)
		except ConnectionRefusedError:
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
	
	def redraw(self):
		self._drawevent.set()
	
	def input_thread(self, scr):
		while True:
			i = scr.getkey()
			
			if   i == "\x1b": self.stop()
			elif i == "KEY_F(2)":
				self.chunkmap_active = not self.chunkmap_active
				self.redraw()
			elif i == "KEY_F(3)":
				self.map_.alternating_colors = not self.map_.alternating_colors
				self.redraw()
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
			
			else: sys.stderr.write(repr(i) + "\n")
	
	def connection_thread(self):
		while True:
			try:
				j = self._ws.recv()
				self.handle_json(json.loads(j))
			except (WSException, ConnectionResetError, OSError):
				#self.stop()
				return
	
	def handle_json(self, message):
		sys.stderr.write(f"message: {message}\n")
		if message["type"] == "apply-changes":
			changes = []
			for chunk in message["data"]:
				pos = Position(chunk[0][0], chunk[0][1])
				change = ChunkDiff.from_dict(chunk[1])
				changes.append((pos, change))
			
			sys.stderr.write(f"Changes to apply: {changes}\n")
			self.map_.apply_changes(changes)
	
	def stop(self):
		sys.stderr.write("Stopping!\n")
		self.stopping = True
		self._ws.close()
		self.redraw()

	def request_chunks(self, coords):
		#sys.stderr.write(f"requested chunks: {coords}\n")
		message = {"type": "request-chunks", "data": coords}
		self._ws.send(json.dumps(message))
		
		#def execute():
			#changes = [(pos, ChunkDiff()) for pos in coords]
			#with self.pool as pool:
				#pool.apply_changes(changes)
		
		#tx = threading.Timer(1, execute)
		#tx.start()
	
	def unload_chunks(self, coords):
		#sys.stderr.write(f"unloading chunks: {coords}\n")
		message = {"type": "unload-chunks", "data": coords}
		self._ws.send(json.dumps(message))
	
	def send_changes(self, changes):
		#sys.stderr.write(f"sending changes: {changes}\n")
		message = {"type": "save-changes", "data": changes}
		self._ws.send(json.dumps(message))

def main(argv):
	if len(argv) != 2:
		print("Usage:")
		print(f"  {argv[0]} address")
		return
	
	os.environ.setdefault('ESCDELAY', '25') # only a 25 millisecond delay
	
	client = Client(argv[1])
	curses.wrapper(client.launch)

if __name__ == "__main__":
	main(sys.argv)
