from collections import namedtuple
import curses
import math
import threading
from utils import CHUNK_HEIGHT, CHUNK_WIDTH, chunkx, chunky, inchunkx, inchunky, Position

class Map():
	"""
	A map which displays chunks and a cursor on the screen.
	Allows for user to modify chunks in an intuitive way.
	"""
	
	def __init__(self, width, height, chunkpool, client):
		self._lock = threading.RLock()
		
		self.chunkpreload = 1 # preload chunks in this radius (they will count as "visible")
		self.chunkunload = 10 # don't unload chunks within this radius
		self.cursorpadding = 2
		self.worldx = -self.cursorpadding
		self.worldy = -self.cursorpadding
		self.cursorx = 0
		self.cursory = 0
		self.lastcurx = self.cursorx
		self.lastcury = self.cursory
		
		self.chunkpool = chunkpool
		self.client = client
		
		self.alternating_colors = False
		
		self._pad = curses.newpad(1, 1) # size doesn't matter (heh), since it resizes
		self.resize(width, height)      # directly afterwards to fit the width+height
		
		if curses.has_colors():
			curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE) # chunk not loaded
			curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE) # alternate color for chunks
	
	def __enter__(self):
		self._lock.acquire()
		return self
	
	def __exit__(self, type, value, tb):
		self._lock.release()
	
	def redraw(self):
		self._pad.redrawwin()
		
		self.client.redraw()
	
	def draw(self):
		with self.chunkpool as pool:
			for x in range(chunkx(self.width) + 2):      # +2, not +1, or there will be empty gaps
				for y in range(chunky(self.height) + 2): # in the bottom and right borders
					pos = Position(x+chunkx(self.worldx), y+chunky(self.worldy))
					chunk = pool.get(pos)
					if chunk:
						self.draw_chunk_to(x*CHUNK_WIDTH, y*CHUNK_HEIGHT, chunk, (pos.x+pos.y)%2)
					else:
						self.draw_empty_to(x*CHUNK_WIDTH, y*CHUNK_HEIGHT)
		
		self.update_cursor()
		self.noutrefresh()
	
	def noutrefresh(self):
		self._pad.noutrefresh(inchunky(self.worldy), inchunkx(self.worldx), 0, 0, self.height-1, self.width-1)
	
	def update_cursor(self):
		self._pad.move(
			self.cursory - chunky(self.worldy)*CHUNK_HEIGHT,
			self.cursorx - chunkx(self.worldx)*CHUNK_WIDTH
		)
	
	def draw_empty_to(self, x, y):
		if curses.has_colors():
			for dy in range(CHUNK_HEIGHT):
				self._pad.addstr(y+dy, x, " "*CHUNK_WIDTH, curses.color_pair(1))
		else:
			for dy in range(CHUNK_HEIGHT):
				s = "."*CHUNK_WIDTH
				self._pad.addstr(y+dy, x, s)
	
	def draw_chunk_to(self, x, y, chunk, blue=False):
		if self.alternating_colors and curses.has_colors() and blue:
			for line in chunk.lines():
				self._pad.addstr(y, x, line, curses.color_pair(2))
				y += 1
		else:
			for line in chunk.lines():
				self._pad.addstr(y, x, line)
				y += 1
	
	def _unload_condition(self, pos, chunk):
		xstart = chunkx(self.worldx) - self.chunkunload
		ystart = chunky(self.worldy) - self.chunkunload
		xend = xstart + chunkx(self.width)+2 + 2*self.chunkunload
		yend = ystart + chunky(self.height)+2 + 2*self.chunkunload
		
		in_range = pos.x >= xstart and pos.x < xend and pos.y >= ystart and pos.y < yend
		return not in_range and not chunk.modified()
	
	def load_visible(self):
		with self.chunkpool as pool:
			coords = self.visible_chunk_coords()
			pool.load_list(coords)
			pool.clean_up(except_for=coords, condition=self._unload_condition)
		
		self.client.redraw()
	
	def resize(self, width, height):
		self.width = width
		self.height = height
		
		self._pad.resize(
			(chunky(height) + 2)*CHUNK_HEIGHT,
			(chunkx(width) + 2)*CHUNK_WIDTH + 1 # workaround for addwstr issue when drawing
		)
		
		self.load_visible()
	
	def visible_chunk_coords(self):
		coords = []
		
		xstart = chunkx(self.worldx) - self.chunkpreload
		ystart = chunky(self.worldy) - self.chunkpreload
		xend = xstart + chunkx(self.width)+2 + 2*self.chunkpreload
		yend = ystart + chunky(self.height)+2 + 2*self.chunkpreload
		
		for x in range(xstart, xend):
			for y in range(ystart, yend):
				coords.append(Position(x, y))
		
		return coords
	
	def write(self, char):
		with self.chunkpool as pool:
			chunk = pool.get(Position(chunkx(self.cursorx), chunky(self.cursory)))
			
			if chunk:
				chunk.set(inchunkx(self.cursorx), inchunky(self.cursory), char)
				pool.save_changes_delayed()
				
				self.move_cursor(1, 0, False)
	
	def delete(self):
		with self.chunkpool as pool:
			chunk = pool.get(Position(chunkx(self.cursorx-1), chunky(self.cursory)))
			if chunk:
				chunk.delete(inchunkx(self.cursorx-1), inchunky(self.cursory))
				pool.save_changes_delayed()
				
				self.move_cursor(-1, 0, False)
	
	def newline(self):
		self.set_cursor(self.lastcurx, self.lastcury+1)
	
	def set_cursor(self, x, y, explicit=True):
		self.cursorx = x
		self.cursory = y
		
		if explicit:
			self.lastcurx = self.cursorx
			self.lastcury = self.cursory
		
		self.worldx = min(
			self.cursorx - self.cursorpadding,
			max(
				self.cursorx - self.width+1 + self.cursorpadding,
				self.worldx
			)
		)
		
		self.worldy = min(
			self.cursory - self.cursorpadding,
			max(
				self.cursory - self.height+1 + self.cursorpadding,
				self.worldy
			)
		)
		
		self.load_visible()
		
	
	def move_cursor(self, dx, dy, explicit=True):
		self.set_cursor(self.cursorx+dx, self.cursory+dy, explicit)
	
	def scroll(self, dx, dy):
		self.worldx += dx
		self.worldy += dy
		
		# new scrolling code: The cursor stays on the same screen position while scrolling
		self.move_cursor(dx, dy)
		
		# old scrolling code: The cursor would stay on the same world coordinates while scrolling,
		# and only if it was at the edge of the screen, it would get carried with the window.
		#self.cursorx = min(
			#self.worldx + self.width-1 - self.cursorpadding,
			#max(
				#self.worldx + self.cursorpadding,
				#self.cursorx
			#)
		#)
		
		#self.cursory = min(
			#self.worldy + self.height-1 - self.cursorpadding,
			#max(
				#self.worldy + self.cursorpadding,
				#self.cursory
			#)
		#)
		
		#self.load_visible()
	
	def commit_diffs(self, diffs):
		with self.chunkpool as pool:
			pool.commit_diffs(diffs)

ChunkStyle = namedtuple("ChunkStyle", "string color")

class ChunkMap():
	"""
	A map that shows which chunks are currently loaded.
	Might show additional details too (i.e. if a chunk has been modified).
	"""
	
	styles = {
		"empty":    ChunkStyle("()", 3),
		"normal":   ChunkStyle("[]", 4),
		"unload":   ChunkStyle("{}", 5),
		"visible":  ChunkStyle("##", 6),
		"modified": ChunkStyle("!!", 7),
	}
	
	def __init__(self, map_):
		self.map_ = map_
		self.chunkpool = map_.chunkpool
		self.corner = "ur" # upper right
		
		#minx, maxx, miny, maxy = self.get_min_max()
		#self.win = curses.newwin(maxy-miny+2, maxx-minx+2)
		self.win = curses.newwin(2, 2)
		
		if curses.has_colors():
			curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_BLUE) # empty chunk
			curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE) # chunk
			curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_YELLOW) # chunk to be unloaded
			curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_GREEN) # visible chunk
			curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_RED) # modified chunk
	
	def update_size(self, sizex, sizey):
		winy, winx = self.win.getmaxyx()
		if winx != 2*sizex + 4 or winy != sizey + 3:
			self.win.resize(sizey + 3, 2*sizex + 4)
	
	def draw(self):
		with self.chunkpool as pool:
			if pool._chunks:
				minx, maxx, miny, maxy = self.get_min_max(pool)
			else:
				minx, maxx, miny, maxy = 0, 0, 0, 0
			sizex = maxx - minx
			sizey = maxy - miny
			self.update_size(sizex, sizey)
			
			self.win.erase()
			self.win.border()
			
			for pos, chunk in pool._chunks.items():
				tp = self.type_of(pos, chunk)
				if curses.has_colors():
					self.win.addstr(
						pos.y - miny + 1,
						2*(pos.x - minx) + 1,
						"  ",
						curses.color_pair(self.styles[tp].color)
					)
				else:
					self.win.addstr(
						pos.y - miny + 1,
						2*(pos.x - minx) + 1,
						self.styles[tp].string
					)
			
			self.win.noutrefresh()
	
	def get_min_max(self, pool):
		minx = min(pos.x for pos in pool._chunks)
		maxx = max(pos.x for pos in pool._chunks)
		miny = min(pos.y for pos in pool._chunks)
		maxy = max(pos.y for pos in pool._chunks)
		
		return minx, maxx, miny, maxy
	
	def get_size(self):
		minx, maxx, miny, maxy = self.get_min_max()
		return maxx - minx, maxy - miny
	
	def type_of(self, pos, chunk):
		if chunk.modified():
			return "modified"
		elif self.map_._unload_condition(pos, chunk):
			return "unload"
		elif not chunk.empty():
			return "normal"
		elif pos in self.map_.visible_chunk_coords():
			return "visible"
		else:
			return "empty"
	
	#def move(self, x, y, corner):
		#pass
