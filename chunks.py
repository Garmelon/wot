import string
import threading
import time
from utils import CHUNK_WIDTH, CHUNK_HEIGHT, Position

class ChunkDiff():
	"""
	Represents differences between two chunks (changes to be made to a chunk).
	Can be used to transform a chunk into another chunk.
	
	Todo: Implement delete diff
	"""
	
	def __init__(self):
		self._chars = {}
	
	def __str__(self):
		return "cd" + str(self._chars)
	
	def __repr__(self):
		return "cd" + repr(self._chars)
	
	@classmethod
	def from_dict(cls, d):
		diff = cls()
		diff._chars = {int(i): v for i, v in d.items()}
		return diff
	
	def to_dict(self):
		return self._chars
		#return self._chars.copy()
	
	@classmethod
	def from_string(cls, s):
		diff = cls()
		for i, char in enumerate(s):
			diff._chars[i] = char
		return diff
	
	def to_string(self):
		s = "".join(self._chars.get(i, " ") for i in range(CHUNK_WIDTH*CHUNK_HEIGHT))
		return s
	
	def copy(self):
		return ChunkDiff.from_dict(self.to_dict().copy())
	
	def combine(self, diff):
		newdiff = self.copy()
		newdiff.apply(diff)
		return newdiff
	
	def set(self, x, y, character):
		pos = x+y*CHUNK_WIDTH
		self._chars[pos] = character
	
	def delete(self, x, y):
		self.set(x, y, " ")
	
	def clear_deletions(self):
		self._chars = {i: v for i, v in self._chars.items() if v != " "}
	
	def apply(self, diff):
		for i, c in diff._chars.items():
			self._chars[i] = c
	
	def lines(self):
		s = self.to_string()
		return [s[i:i+CHUNK_WIDTH] for i in range(0, CHUNK_WIDTH*CHUNK_HEIGHT, CHUNK_WIDTH)]
	
	def empty(self):
		return not bool(self._chars)
	
	def legitimate(self):
		for i, char in self._chars.items():
			if not (isinstance(char, str) and len(char) == 1 and ord(char) > 31 and (char not in string.whitespace or char == " ")):
				return False
		else:
			return True
	
	def diff(self, chunk):
		diffs = {}
		for pos, char in self._chars.items():
			diffs[pos] = chunk._chars.get(pos, " ")
		
		return ChunkDiff.from_dict(diffs)

def jsonify_diffs(diffs):
	ddiffs = []
	for pos, diff in diffs.items():
		ddiff = diff.to_dict()
		ddiffs.append((pos, ddiff))
	
	return ddiffs

def dejsonify_diffs(ddiffs):
	diffs = {}
	for dchunk in ddiffs:
		pos = Position(dchunk[0][0], dchunk[0][1])
		diff = ChunkDiff.from_dict(dchunk[1])
		diffs[pos] = diff
	
	return diffs

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
		
		self.last_modified = 0
	
	@classmethod
	def from_string(cls, s):
		chunk = cls()
		chunk._content = ChunkDiff.from_string(s)
		return chunk
	
	def to_string(self):
		return self.as_diff().to_string()
	
	def set(self, x, y, character):
		self._modifications.set(x, y, character)
		self.touch()
	
	def delete(self, x, y):
		self._modifications.delete(x, y)
		self.touch()
	
	def commit_changes(self):
		self.commit_diff(self._modifications)
		self._modifications = ChunkDiff()
		self.touch()
	
	def apply_diff(self, diff):
		self._modifications.apply(diff)
		self.touch()
	
	def commit_diff(self, diff):
		self._content.apply(diff)
		self._content.clear_deletions()
		self.touch()
	
	def drop_changes(self):
		self._modifications = ChunkDiff()
		self.touch()
	
	def get_changes(self):
		return self._modifications
	
	def as_diff(self):
		return self._content.combine(self._modifications)
	
	def touch(self, now=None):
		self.last_modified = now or time.time()
	
	def age(self, now=None):
		return (now or time.time()) - self.last_modified
	
	def lines(self):
		return self.as_diff().lines()
	
	def modified(self):
		return not self._modifications.empty()
	
	def empty(self):
		return self._content.empty() and self._modifications.empty()

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
	
	def set(self, pos, chunk):
		self._chunks[pos] = chunk
	
	def get(self, pos):
		return self._chunks.get(pos)
	
	def create(self, pos):
		chunk = Chunk()
		self.set(pos, chunk)
		return chunk
	
	def apply_diffs(self, diffs):
		for pos, diff in diffs.items():
			chunk = self.get(pos) or self.create(pos)
			#chunk = self.load(pos)
			
			if not diff.empty():
				chunk.apply_diff(diff)
	
	def commit_diffs(self, diffs):
		for pos, diff in diffs.items():
			chunk = self.get(pos) or self.create(pos)
			#chunk = self.load(pos)
			
			if not diff.empty():
				chunk.commit_diff(diff)
	
	def commit_changes(self):
		changes = {}
		
		for pos, chunk in self._chunks.items():
			if chunk.modified():
				changes[pos] = chunk.get_changes()
				chunk.commit_changes()
		
		return changes
	
	def save_changes(self):
		self.commit_changes()
	
	def load(self, pos):
		if not self.get(pos):
			self.create(pos)
		#return self.get(pos) or self.create(pos)
	
	def load_list(self, coords):
		for pos in coords:
			self.load(pos)
	
	def unload(self, pos):
		if pos in self._chunks:
			del self._chunks[pos]
	
	def unload_list(self, coords):
		for pos in coords:
			self.unload(pos)
	
	def clean_up(self, except_for=[], condition=lambda pos, chunk: True):
		## old list comprehension which became too long:
		#coords = [pos for pos, chunk in self._chunks.items() if not pos in except_for and condition(chunk)]
		
		#self.save_changes() # needs to be accounted for by the user
		
		coords = []
		
		for pos, chunk in self._chunks.items():
			if not pos in except_for and condition(pos, chunk):
				coords.append(pos)
		
		self.unload_list(coords)
