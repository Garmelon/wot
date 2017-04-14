# import from chunks, dbchunkpool
import json
import threading
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from utils import Position
from chunks import ChunkDiff
from dbchunkpool import DBChunkPool

pool = DBChunkPool()
clients = []

class WotServer(WebSocket):
	def handle_request_chunks(self, coords):
		changes = []
		with pool:
			for coor in coords:
				pos = Position(coor[0], coor[1])
				change = pool.get(pos) or pool.create(pos)
				dchange = change.as_diff().to_dict()
				changes.append((pos, dchange))
				
				self.loaded_chunks.add(pos)
		
		message = {"type": "apply-changes", "data": changes}
		self.sendMessage(json.dumps(message))
	
	def handle_unload_chunks(self, coords):
		for coor in coords:
			pos = Position(coor[0], coor[1])
			if pos in self.loaded_chunks:
				self.loaded_chunks.remove(pos)
	
	def handle_save_changes(self, dchanges):
		changes = []
		for chunk in dchanges:
			#print("CHUNK!", chunk)
			pos = Position(chunk[0][0], chunk[0][1])
			change = ChunkDiff.from_dict(chunk[1])
			changes.append((pos, change))
		
		with pool:
			pool.apply_changes(changes)
		
		for client in clients:
			if client:
				client.send_changes(changes)
	
	def send_changes(self, changes):
		dchanges = []
		for chunk in changes:
			pos = chunk[0]
			change = chunk[1]
			if pos in self.loaded_chunks:
				dchanges.append((pos, change.to_dict()))
		
		if dchanges:
			message = {"type": "apply-changes", "data": dchanges}
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
		print(f"{graphstr}   {self.address[0]}")
		
		clients[i] = None
		while clients and not clients[-1]:
			clients.pop()

server = SimpleWebSocketServer('', 8000, WotServer)
server.serveforever()
