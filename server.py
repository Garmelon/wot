# import from chunks, dbchunkpool
import json
import sys
import threading
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from utils import Position
from chunks import ChunkDiff, jsonify_changes, dejsonify_changes
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
				changes.append((pos, change.as_diff()))
				
				self.loaded_chunks.add(pos)
		
		dchanges = jsonify_changes(changes)
		message = {"type": "apply-changes", "data": dchanges}
		self.sendMessage(json.dumps(message))
	
	def handle_unload_chunks(self, coords):
		for coor in coords:
			pos = Position(coor[0], coor[1])
			if pos in self.loaded_chunks:
				self.loaded_chunks.remove(pos)
	
	def handle_save_changes(self, dchanges):
		changes = dejsonify_changes(dchanges)
		
		with pool:
			pool.apply_changes(changes)
		
		for client in clients:
			if client:
				client.send_changes(changes)
	
	def send_changes(self, changes):
		changes = [chunk for chunk in changes if chunk[0] in self.loaded_chunks]
		dchanges = jsonify_changes(changes)
		
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
