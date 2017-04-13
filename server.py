# import from chunks, dbchunkpool
import json
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from utils import Position
from chunks import ChunkDiff
from dbchunkpool import DBChunkPool

pool = DBChunkPool()
clients = set()

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
		print(f"Message bong sent: {json.dumps(message)}")
		self.sendMessage(json.dumps(message))
	
	def handle_unload_chunks(self, coords):
		for coor in coords:
			pos = Position(coor)
			self.loaded_chunks.remove(pos)
	
	def handle_save_changes(self, dchanges):
		changes = []
		for chunk in dchanges:
			print("CHUNK!", chunk)
			pos = Position(chunk[0][0], chunk[0][1])
			change = ChunkDiff.from_dict(chunk[1])
			changes.append((pos, change))
		
		with pool:
			pool.apply_changes(changes)
		
		#with pool:
			#for chunk in changes:
				#print("changed content:", pool.get(chunk[0])._content)
		
		for client in clients:
			client.send_changes(changes)
	
	def send_changes(self, changes):
		print("NORMAL CHANGES:", changes)
		dchanges = []
		for chunk in changes:
			pos = chunk[0]
			change = chunk[1]
			if pos in self.loaded_chunks:
				dchanges.append((pos, change.to_dict()))
		print("LOADED CHANGES:", dchanges)
		
		if dchanges:
			print("Changes!")
			message = {"type": "apply-changes", "data": dchanges}
			print("Changes?")
			print(f"Message bang sent: {json.dumps(message)}")
			self.sendMessage(json.dumps(message))
	
	def handleMessage(self):
		message = json.loads(self.data)
		print(f"message arrived: {message}")
		if message["type"] == "request-chunks":
			self.handle_request_chunks(message["data"])
		elif message["type"] == "unload-chunks":
			self.handle_unload_chunks(message["data"])
		elif message["type"] == "save-changes":
			self.handle_save_changes(message["data"])
		
		print("Message received and dealt with.")
		#changes = []
		#for chunk in message["data"]:
			#pass
		#self.sendMessage(self.data)
	
	def handleConnected(self):
		print(self.address, 'connected')
		clients.add(self)
		self.loaded_chunks = set()
	
	def handleClose(self):
		print(self.address, 'closed')
		clients.remove(self)

server = SimpleWebSocketServer('', 8000, WotServer)
server.serveforever()
