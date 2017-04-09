from collections import namedtuple

Position = namedtuple("Position", "x y")

#CHUNK_WIDTH = 64
#CHUNK_HEIGHT = 32
CHUNK_WIDTH = 32
CHUNK_HEIGHT = 16

def chunkx(value):
	return value//CHUNK_WIDTH

def chunky(value):
	return value//CHUNK_HEIGHT

def inchunkx(value):
	return value%CHUNK_WIDTH

def inchunky(value):
	return value%CHUNK_HEIGHT
