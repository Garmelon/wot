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
	
	def commit_diffs(self, diffs):
		super().commit_diffs(diffs)
		
		self._client.redraw()
	
	def save_changes_delayed(self):
		if not self._save_thread:
			def threadf():
				self.save_changes()
				self._save_thread = None
			self._save_thread = threading.Timer(.25, threadf)
			self._save_thread.start()
	
	def save_changes(self):
		diffs = self.commit_changes()
		# filter out empty changes/chunks
		diffs = [dchunk for dchunk in diffs if not dchunk[1].empty()]
		
		if diffs:
			self._client.send_changes(diffs)
	
	def load_list(self, coords):
		coords = [pos for pos in coords if pos not in self._chunks]
		if coords:
			self._client.request_chunks(coords)
	
	def unload_list(self, coords):
		if coords:
			#self.save_changes()
			self._client.unload_chunks(coords)
			super().unload_list(coords)
