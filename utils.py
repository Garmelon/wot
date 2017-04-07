from collections import namedtuple

Position = namedtuple("Position", "x y")

CHUNK_WIDTH = 64
CHUNK_HEIGHT = 32

def chunkx(value):
	return value//CHUNK_WIDTH

def chunky(value):
	return value//CHUNK_HEIGHT

def inchunkx(value):
	return value%CHUNK_WIDTH

def inchunky(value):
	return value%CHUNK_HEIGHT
