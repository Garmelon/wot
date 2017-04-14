# import from chunks, dbchunkpool
import json
import sys
import threading
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from utils import Position
from chunks import ChunkDiff, jsonify_diffs, dejsonify_diffs
from dbchunkpool import DBChunkPool

pool = DBChunkPool()
clients = []

class WotServer(WebSocket):
	def handle_request_chunks(self, coords):
		diffs = []
		with pool:
			for coor in coords:
				pos = Position(coor[0], coor[1])
				chunk = pool.get(pos) or pool.create(pos)
				diffs.append((pos, chunk.as_diff()))
				
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
		legitimate_diffs = []
		illegitimate_diffs = []
		for dchunk in diffs:
			if dchunk[1].legitimate():
				legitimate_diffs.append(dchunk)
			else:
				illegitimate_diffs.append(dchunk)
		
		if legitimate_diffs:
			with pool:
				pool.apply_diffs(legitimate_diffs)
			
			for client in clients:
				if client:
					client.send_changes(legitimate_diffs)
		
		if illegitimate_diffs:
			reverse_diffs = self.reverse_diffs(illegitimate_diffs)
			reverse_ddiffs = jsonify_diffs(reverse_diffs)
			message = {"type": "apply-changes", "data": reverse_ddiffs}
			self.sendMessage(json.dumps(message))
	
	def reverse_diffs(self, diffs):
		with pool:
			reverse_diffs = []
			for dchunk in diffs:
				pos = dchunk[0]
				diff = dchunk[1]
				chunk = pool.get(pos) or pool.create(pos)
				reverse_diff = diff.diff(chunk.as_diff())
				reverse_diffs.append((pos, reverse_diff))
		
		return reverse_diffs
	
	def send_changes(self, diffs):
		diffs = [dchunk for dchunk in diffs if dchunk[0] in self.loaded_chunks]
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
			i = clients.index(None)
			clients[i] = self
		except ValueError:
			clients.append(self)
			i = len(clients) - 1
		
		graphstr = "".join(["┯" if j == i else ("│" if v else " ") for j, v in enumerate(clients)])
		print(f"{graphstr}   {self.address[0]}")
	
	def handleClose(self):
		i = clients.index(self)
		
		graphstr = "".join(["┷" if j == i else ("│" if v else " ") for j, v in enumerate(clients)])
		print(graphstr)
		#print(f"{graphstr}   {self.address[0]}")
		
		clients[i] = None
		while clients and not clients[-1]:
			clients.pop()

def main(argv):
	if len(argv) > 2:
		print("Usage:")
		print(f"  {argv[0]} [port]")
		print("  default port: 8000")
		return
	elif len(argv) > 1:
		try:
			port = int(argv[1])
		except ValueError:
			print("Invalid port")
			return
	else:
		port = 8000
	
	server = SimpleWebSocketServer('', port, WotServer)
	try:
		server.serveforever()
	except KeyboardInterrupt:
		print("Stopped.")

if __name__ == "__main__":
	main(sys.argv)
