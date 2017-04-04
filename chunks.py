class ChunkDiff():
	"""
	Represents differences between two chunks (changes to be made to a chunk).
	Can be used to transform a chunk into another chunk.
	"""
	
	pass

class Chunk():
	"""
	Represents a chunk (16x8 characters on the map).
	Is able to generate diffs
	 - from another chunk
	 - from direct changes
	 - from accumulated changes
	"""
	
	pass

class ChunkPool():
	"""
	Is a collection of chunks.
	Allows user to manage (get, modify, delete) chunks, keeps track of chunks for them.
	Load chunks it doesn't know.
	"""
	
	pass
