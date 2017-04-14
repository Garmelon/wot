import threading
from chunks import ChunkPool

class ClientChunkPool(ChunkPool):
	"""
	A ChunkPool that requests/loads chunks from a client.
	"""
	
	def __init__(self, client):
		super().__init__()
		
		self._client = client
		self._save_thread = None
	
	def set(self, pos, chunk):
		super().set(pos, chunk)
	
	def apply_changes(self, changes):
		super().apply_changes(changes)
		
		self._client.redraw()
	
	def save_changes_delayed(self):
		if not self._save_thread:
			def threadf():
				self.save_changes()
				self._save_thread = None
			self._save_thread = threading.Timer(.25, threadf)
			self._save_thread.start()
	
	def save_changes(self):
		changes = self.commit_changes()
		changes = [chunk for chunk in changes if not chunk[1].empty()]
		
		if changes:
			self._client.send_changes(changes)
	
	def load(self, pos):
		raise Exception
	
	def load_list(self, coords):
		coords = [pos for pos in coords if pos not in self._chunks]
		if coords:
			self._client.request_chunks(coords)
	
	def unload_list(self, coords):
		if coords:
			#self.save_changes()
			self._client.unload_chunks(coords)
			super().unload_list(coords)
