import curses
import math
from utils import CHUNK_HEIGHT, CHUNK_WIDTH, chunkx, chunky, inchunkx, inchunky, Position

import sys

class Map():
	"""
	A map which displays chunks and a cursor on the screen.
	Allows for user to modify chunks in an intuitive way.
	"""
	
	def __init__(self, width, height, chunkpool):
		self.worldx = 0
		self.worldy = 0
		self.cursorx = 0
		self.cursory = 0
		self.chunkpreload = 0
		
		self.chunkpool = chunkpool
		
		self._pad = curses.newpad(5, 5)
		self.resize(width, height)
	
	def draw(self):
		with self.chunkpool as pool:
			for x in range(chunkx(self.width) + 1):
				for y in range(chunky(self.height) + 1):
					chunk = pool.get(x+chunkx(self.worldx), y+chunky(self.worldy))
					if chunk:
						chunk.draw_to(x*CHUNK_WIDTH, y*CHUNK_HEIGHT, self._pad)
					else:
						self.draw_empty_to(x*CHUNK_WIDTH, y*CHUNK_HEIGHT)
		
		# set cursor position in world
		self._pad.move(
			self.cursory - chunky(self.worldy)*CHUNK_HEIGHT,
			self.cursorx - chunkx(self.worldx)*CHUNK_WIDTH
		)
		
		self._pad.noutrefresh(inchunky(self.worldy), inchunkx(self.worldx), 0, 0, self.height-1, self.width-1)
	
	def draw_empty_to(self, x, y):
		if curses.has_colors():
			curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_WHITE)
			for dy in range(CHUNK_HEIGHT):
				self._pad.addstr(y+dy, x, " "*CHUNK_WIDTH, curses.color_pair(1))
		else:
			for dy in range(CHUNK_HEIGHT):
				s = "."*(CHUNK_WIDTH)
				self._pad.addstr(y+dy, x, s)
	
	def resize(self, width, height):
		self.width = width
		self.height = height
		
		self._pad.resize(
			(chunky(height) + 1)*CHUNK_HEIGHT,
			(chunkx(width) + 1)*CHUNK_WIDTH + 1 # workaround for addwstr issue when drawing
		)
		
		with self.chunkpool as pool:
			pool.load_list(self.visible_chunk_coords())
	
	def visible_chunk_coords(self):
		coords = []
		
		xstart = chunkx(self.worldx) - self.chunkpreload
		ystart = chunky(self.worldy) - self.chunkpreload
		xend = xstart + chunkx(self.width) + 1 + 2*self.chunkpreload
		yend = ystart + chunky(self.height) + 1 + 2*self.chunkpreload
		
		for x in range(xstart, xend):
			for y in range(ystart, yend):
				coords.append(Position(x, y))
		
		return coords
	
	def write(self, char):
		pass
	
	def move_cursor(self, dx, dy):
		pass
	
	def scroll(self, dx, dy):
		pass
	

class ChunkMap():
	"""
	A map that shows which chunks are currently loaded.
	Might show additional details too (i.e. if a chunk has been modified).
	"""
	
	def __init__(self, chunkpool):
		self.cpool = chunkpool
#	
#	def draw(self):
#		pass
#	
#	def resize(self, size):
#		pass
#	
	def move(self, x, y, corner):
		pass
	
	def toggle(self):
		pass
