import sqlite3
import time
import threading

from chunks import ChunkPool
from utils import Position

class ChunkDB():
	"""
	Load and save chunks to a SQLite db.
	"""
	
	def __init__(self, filename):
		self.dbfilename = filename
	
	def transaction(func):
		def wrapper(self, *args, **kwargs):
			con = sqlite3.connect(self.dbfilename)
			try:
				with con:
					return func(self, con, *args, **kwargs)
			finally:
				con.close()
		
		return wrapper
	
	@transaction
	def save_many(self, con, chunks):
		print("save_many")
	
	@transaction
	def load_many(self, con, coords):
		print("load_many")
		return [(coor, None) for coor in coords]

class DBChunkPool(ChunkPool):
	"""
	A ChunkPool that can load/save chunks from/to a database.
	"""
	
	def __init__(self, filename):
		super().__init__()
		self._chunkdb = ChunkDB(filename)
		
		self.save_period = 10 # save and clean up every minute
		self.max_age = 20 # ca. one minute until a chunk is unloaded again
		
		self.save_thread = threading.Thread(
			target=self.perodic_save,
			name="save_thread",
			daemon=True
		)
		self.save_thread.start()
	
	def save_changes(self):
		diffs = self.commit_changes()
		
		changed_chunks = []
		for dchunk in diffs:
			pos = dchunk[0]
			chunk = self.get(pos)
			changed_chunks.append((pos, chunk))
		
		self._chunkdb.save_many(changed_chunks)
	
	def load(self, pos):
		print("Loading individual chunk...")
		raise Exception
	
	def load_list(self, coords):
		print("Loading chunk list...")
		to_load = [pos for pos in coords if pos not in self._chunks]
		chunks = self._chunkdb.load_many(to_load)
		for dchunk in chunks:
			pos = dchunk[0]
			chunk = dchunk[1]
			if chunk:
				self.set(pos, chunk)
			else:
				self.create(pos)
	
	def perodic_save(self):
		while True:
			time.sleep(self.save_period)
			
			with self:
				print("BEFORE:::")
				self.print_chunks()
				
				self.save_changes()
				
				# unload old chunks
				now = time.time()
				for pos, chunk in self._chunks.items():
					print(f"p{pos} :: t{now} :: m{chunk.last_modified} :: a{chunk.age(now)}")
				self.clean_up(condition=lambda pos, chunk: chunk.age(now) > self.max_age)
				
				print("AFTER:::")
				self.print_chunks()
	
	def get_min_max(self):
		minx = min(pos.x for pos in self._chunks)
		maxx = max(pos.x for pos in self._chunks)
		miny = min(pos.y for pos in self._chunks)
		maxy = max(pos.y for pos in self._chunks)
		
		return minx, maxx, miny, maxy
	
	def print_chunks(self):
		if self._chunks:
			minx, maxx, miny, maxy = self.get_min_max()
			sizex, sizey = maxx - minx + 1, maxy - miny + 1
			print("┌" + "─"*sizex*2 + "┐")
			for y in range(miny, maxy + 1):
				line = []
				for x in range(minx, maxx + 1):
					chunk = self._chunks.get(Position(x, y))
					if chunk:
						if chunk.empty():
							line.append("()")
						else:
							line.append("[]")
					else:
						line.append("  ")
				line = "".join(line)
				print("│" + line + "│")
			print("└" + "─"*sizex*2 + "┘")
