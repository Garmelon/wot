import threading
import time
from utils import CHUNK_WIDTH, CHUNK_HEIGHT

class ChunkDiff():
	"""
	Represents differences between two chunks (changes to be made to a chunk).
	Can be used to transform a chunk into another chunk.
	
	Todo: Implement delete diff
	"""
	
	@classmethod
	def combine(cls, diff_a, diff_b):
		diff = cls()
		diff.apply(diff_a)
		diff.apply(diff_b)
		return diff
	
	def __init__(self):
		self._chars = {}
	
	@classmethod
	def from_dict(cls, d):
		diff = cls()
		diff._chars = d
		return diff
		#self._chars = d.copy()
	
	def copy(self):
		return ChunkDiff.from_dict(self.to_dict().copy())
	
	def combine(self, diff):
		newdiff = self.copy()
		newdiff.apply(diff)
		return newdiff
	
	def to_dict(self):
		return self._chars
		#return self._chars.copy()
	
	def set(self, x, y, character):
		self._chars[x+y*CHUNK_WIDTH] = character
	
	def delete(self, x, y):
		del self._chars[x+y*CHUNK_WIDTH]
	
	def apply(self, diff):
		for i, c in diff._chars.items():
			self._chars[i] = c
	
	def lines(self):
		d = self._chars
		s = "".join(d.get(i, " ") for i in range(CHUNK_WIDTH*CHUNK_HEIGHT))
		return [s[i:i+CHUNK_WIDTH] for i in range(0, CHUNK_WIDTH*CHUNK_HEIGHT, CHUNK_WIDTH)]
	

class Chunk():
	"""
	Represents a chunk (16x8 characters on the map).
	Is able to generate diffs
	 - from another chunk
	 - from direct changes
	 - from accumulated changes
	"""
	
	def __init__(self):
		self._content = ChunkDiff()
		self._modifications = ChunkDiff()
		
		self.touch()
	
	def set(self, x, y, character):
		self._modifications.set(x, y, character)
	
	def delete(self, x, y):
		self._modifications.delete(x, y)
	
	def commit_changes(self):
		self._content.apply(self._modifications)
		self._modifications = ChunkDiff()
	
	def drop_changes(self):
		self._modifications = ChunkDiff()
	
	def get_changes(self):
		return self._modifications
	
	def touch(self):
		self.last_modified = time.time()
	
	def draw_to(self, x, y, window):
		for line in self._content.combine(self._modifications).lines():
			window.addstr(y, x, line)
			y += 1

class ChunkPool():
	"""
	Is a collection of chunks.
	Allows user to manage (get, modify, delete) chunks, keeps track of chunks for them.
	Load chunks it doesn't know.
	"""
	
	def __init__(self):
		self._chunks = {}
		self._lock = threading.RLock()
	
	def __enter__(self):
		self._lock.acquire()
		return self
	
	def __exit__(self, type, value, tb):
		self._lock.release()
	
	def create(self, pos):
		self._chunks[pos] = Chunk()
		return self._chunks[pos]
	
	def load(self, pos):
		if not pos in self._chunks:
			self.create(pos)
	
	def load_list(self, coords):
		for pos in coords:
			self.load(pos)
	
	def get(self, pos):
		return self._chunks.get(pos)
