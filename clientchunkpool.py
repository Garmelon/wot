from chunks import ChunkPool

class ClientChunkPool(ChunkPool):
	"""
	A ChunkPool that requests/loads chunks from a client.
	"""
	
	def __init__(self):
		super().__init__()
		self.max_age = 10 #s
	
	pass
