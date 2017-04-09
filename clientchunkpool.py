from chunks import ChunkPool

class ClientChunkPool(ChunkPool):
	"""
	A ChunkPool that requests/loads chunks from a client.
	"""
	
	def __init__(self, client):
		super().__init__()
		
		self._client = client
	
	#def commit_changes(self):
		#changes = []
		
		#for pos, chunk in self._chunks.items():
			#changes.append((pos, chunk.get_changes()))
			#chunk.commit_changes()
		
		#return changes
	
	def apply_changes(self, changes):
		super().apply_changes(changes)
		
		self._client.redraw()
	
	def save_changes(self):
		changes = self.commit_changes()
		self._client.send_changes(changes)
	
	def load(self, pos):
		raise Exception
	
	def load_list(self, coords):
		self._client.request_chunks(coords)
