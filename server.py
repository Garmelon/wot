# import from chunks, dbchunkpool
import json
import sys
import threading
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from utils import Position
from chunks import ChunkDiff, jsonify_diffs, dejsonify_diffs
from dbchunkpool import DBChunkPool

from chunks import ChunkPool

class WotServer(WebSocket):
	def handle_request_chunks(self, coords):
		diffs = {}
		coords = [Position(coor[0], coor[1]) for coor in coords]
		
		with self.pool as pool:
			pool.load_list(coords)
			
			for pos in coords:
				chunk = pool.get(pos)
				diff = chunk.as_diff()
				diffs[pos] = diff
				
				self.loaded_chunks.add(pos)
		
		ddiffs = jsonify_diffs(diffs)
		message = {"type": "apply-changes", "data": ddiffs}
		self.sendMessage(json.dumps(message))
	
	def handle_unload_chunks(self, coords):
		for coor in coords:
			pos = Position(coor[0], coor[1])
			if pos in self.loaded_chunks:
				self.loaded_chunks.remove(pos)
	
	def handle_save_changes(self, ddiffs):
		diffs = dejsonify_diffs(ddiffs)
		
		# check whether changes are correct (exclude certain characters)
		# if not correct, send corrections them back to sender
		legitimate_diffs = {}
		illegitimate_diffs = {}
		for pos, diff in diffs.items():
			if diff.legitimate():
				legitimate_diffs[pos] = diff
			else:
				illegitimate_diffs[pos] = diff
		
		if legitimate_diffs:
			with self.pool as pool:
				pool.load_list(legitimate_diffs.keys())
				pool.apply_diffs(legitimate_diffs)
			
			for client in self.clients:
				if client:
					client.send_changes(legitimate_diffs)
		
		if illegitimate_diffs:
			reverse_diffs = self.reverse_diffs(illegitimate_diffs)
			reverse_ddiffs = jsonify_diffs(reverse_diffs)
			message = {"type": "apply-changes", "data": reverse_ddiffs}
			self.sendMessage(json.dumps(message))
	
	def reverse_diffs(self, diffs):
		with self.pool as pool:
			pool.load_list(diffs.keys())
			
			reverse_diffs = {}
			for pos, diff in diffs.items():
				chunk = pool.get(pos)
				reverse_diff = diff.diff(chunk.as_diff())
				reverse_diffs[pos] = reverse_diff
		
		return reverse_diffs
	
	def send_changes(self, diffs):
		diffs = {pos: diff for pos, diff in diffs.items() if pos in self.loaded_chunks}
		ddiffs = jsonify_diffs(diffs)
		
		if ddiffs:
			message = {"type": "apply-changes", "data": ddiffs}
			self.sendMessage(json.dumps(message))
	
	def handleMessage(self):
		message = json.loads(self.data)
		if message["type"] == "request-chunks":
			self.handle_request_chunks(message["data"])
		elif message["type"] == "unload-chunks":
			self.handle_unload_chunks(message["data"])
		elif message["type"] == "save-changes":
			self.handle_save_changes(message["data"])
	
	def handleConnected(self):
		self.loaded_chunks = set()
		
		try:
			i = self.clients.index(None)
			self.clients[i] = self
		except ValueError:
			self.clients.append(self)
			i = len(self.clients) - 1
		
		graphstr = "".join(["┯" if j == i else ("│" if v else " ") for j, v in enumerate(self.clients)])
		print(f"{graphstr}  {self.address[0]}")
	
	def handleClose(self):
		i = self.clients.index(self)
		
		graphstr = "".join(["┷" if j == i else ("│" if v else " ") for j, v in enumerate(self.clients)])
		print(graphstr)
		#print(f"{graphstr}   {self.address[0]}")
		
		self.clients[i] = None
		while self.clients and not self.clients[-1]:
			self.clients.pop()

def main(argv):
	if len(argv) == 1 or len(argv) > 3:
		print("Usage:")
		print(f"  {argv[0]} dbfile [port]")
		print("  default port: 8000")
		return
	
	dbfile = argv[1]
	
	if len(argv) >= 3:
		try:
			port = int(argv[2])
		except ValueError:
			print("Invalid port")
			return
	else:
		port = 8000
	
	print("Connecting to db")
	WotServer.pool = DBChunkPool(dbfile)
	WotServer.clients = []
	
	server = SimpleWebSocketServer('', port, WotServer)
	try:
		server.serveforever()
	except KeyboardInterrupt:
		print("")
		print("Saving recent changes.")
		WotServer.pool.save_changes()
		print("Cleaning up empty chunks from db.")
		WotServer.pool.remove_empty()
		print("Stopped.")

if __name__ == "__main__":
	main(sys.argv)
