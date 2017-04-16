import sqlite3
import time
import threading

from chunks import ChunkPool, Chunk
from utils import Position, CHUNK_WIDTH, CHUNK_HEIGHT

class ChunkDB():
	"""
	Load and save chunks to a SQLite db.
	"""
	
	def __init__(self, filename):
		self.dbfilename = filename
		
		self._create_table()
	
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
	def _create_table(self, con):
		cur = con.cursor()
		cur.execute(("CREATE TABLE IF NOT EXISTS chunks ("
		             "x INTEGER NOT NULL, "
		             "y INTEGER NOT NULL, "
		             "content TEXT, "
		             "PRIMARY KEY (x, y)"
		             ")"))
	
	@transaction
	def save_many(self, con, chunks):
		lchunks = ChunkDB.chunks_to_list(chunks)
		con.executemany("INSERT OR REPLACE INTO chunks VALUES (?, ?, ?)", lchunks)
	
	@transaction
	def load_many(self, con, coords):
		cur = con.cursor()
		results = []
		
		for pos in coords:
			cur.execute("SELECT * FROM chunks WHERE x=? AND y=?", pos)
			results.extend(cur.fetchall())
		
		results = ChunkDB.list_to_chunks(results)
		return results
	
	@transaction
	def remove_empty(self, con):
		con.execute("DELETE FROM chunks WHERE content=?", (" "*CHUNK_WIDTH*CHUNK_HEIGHT,))
	
	@staticmethod
	def list_to_chunks(l):
		chunks = {}
		
		for item in l:
			pos = Position(item[0], item[1])
			chunk = Chunk.from_string(item[2])
			chunks[pos] = chunk
		
		return chunks
	
	@staticmethod
	def chunks_to_list(chunks):
		l = []
		
		for pos, chunk in chunks.items():
			l.append((pos[0], pos[1], chunk.to_string()))
		
		return l

class DBChunkPool(ChunkPool):
	"""
	A ChunkPool that can load/save chunks from/to a database.
	"""
	
	def __init__(self, filename):
		super().__init__()
		self._chunkdb = ChunkDB(filename)
		
		self.save_period = 60 # save and clean up every minute
		self.max_age = 60 # ca. one minute until a chunk is unloaded again
		
		self.save_thread = threading.Thread(
			target=self.perodic_save,
			name="save_thread",
			daemon=True
		)
		self.save_thread.start()
	
	def save_changes(self):
		diffs = self.commit_changes()
		
		changed_chunks = {}
		for pos, diff in diffs.items():
			chunk = self.get(pos)
			changed_chunks[pos] = chunk
		
		self._chunkdb.save_many(changed_chunks)
	
	def load(self, pos):
		raise Exception
	
	def load_list(self, coords):
		to_load = [pos for pos in coords if pos not in self._chunks]
		chunks = self._chunkdb.load_many(to_load)
		
		for pos in to_load:
			if pos in chunks:
				self.set(pos, chunks.get(pos))
			else:
				self.create(pos)
	
	def perodic_save(self):
		while True:
			time.sleep(self.save_period)
			
			with self:
				self.save_changes()
				
				# unload old chunks
				now = time.time()
				self.clean_up(condition=lambda pos, chunk: chunk.age(now) > self.max_age)
	
	def remove_empty(self):
		self._chunkdb.remove_empty()
	
	def _get_min_max(self):
		"""
		Meant for debugging.
		"""
		
		minx = min(pos.x for pos in self._chunks)
		maxx = max(pos.x for pos in self._chunks)
		miny = min(pos.y for pos in self._chunks)
		maxy = max(pos.y for pos in self._chunks)
		
		return minx, maxx, miny, maxy
	
	def _print_chunks(self):
		"""
		Meant for debugging.
		"""
		
		if self._chunks:
			minx, maxx, miny, maxy = self._get_min_max()
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
