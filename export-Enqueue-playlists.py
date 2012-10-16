#!/usr/bin/env python
# coding=utf-8
import sys
import os
import optparse
import sqlite3
import re
import datetime
import time
import shutil
import urllib
import urlparse

DB_FILE      = os.path.expanduser('~/Library/Application Support/Enqueue/Enqueue.db')
OUTPUT_DIR   = 'playlists/'
PLAYLISTS_FN = 'playlists.txt'


def main():
	p = optparse.OptionParser(description = '''

Creates playlist m3u files from enqueue db, writes m3u files to output directory, and copies all 
songs needed in m3u files to same output directory. 

Only playlists listed in "playlists_file" will be created in output directory. 
It's best to create initial "playlists_file" with -i, then edit file 
commenting out playlists to skip, then invoke again with -c.

	''')
	p.add_option('-v', '--verbose', action ='store_true', default=False, help='returns verbose output')
	p.add_option('-e', '--erase_unused', action ='store_true', default=False, help='Erase files in output_dir that are not used by m3u playlists')
	p.add_option('-s', '--skip_empty_playlists', action ='store_true', default=False, help='Skip playlists that have 0 songs')
	p.add_option('-d', '--db_file', help='Enqueue db file. Default: '+ DB_FILE, default=DB_FILE)
	p.add_option('-o', '--output_dir', default=OUTPUT_DIR,
	             help='directory that will contain newly created playlists and songs. Default: '+ OUTPUT_DIR)
	p.add_option('-p', '--playlists_file', default=PLAYLISTS_FN, 
	             help='File containing list of playlists to export, created using -c. Default: '+ PLAYLISTS_FN)
	p.add_option('-i', '--initialize_playlists_file', action ='store_true', default=False,
	             help='Initialize the "playlists_file" based on current playlists in Enqueue, '\
	                 +'replacing any existing file.  Do not create any other files.')
	p.add_option('-c', '--copy_playlists', action ='store_true', default=False,
	             help='Copy to "output_dir" all playlists and needed songs from the "playlists_file".')
	p.add_option('-m', '--m3u_only', action ='store_true', default=False,
	             help='Only create playlist m3u files, do not copy any songs.')
	p.add_option('--stats', action ='store_true', default=False, help='Output stats on Enqueue DB')

	options, arguments = p.parse_args()

	nq = EnqueueWrapper(db_file              = options.db_file,
	                    output_dir           = options.output_dir,
	                    playlists_file       = options.playlists_file,
	                    skip_empty_playlists = options.skip_empty_playlists,
	                    erase_unused         = options.erase_unused,
	                    m3u_only             = options.m3u_only,
	                    verbose              = options.verbose)
	nq.readDB(options.stats)
	
	if options.initialize_playlists_file:
		nq.createPlaylistFile()
	elif options.copy_playlists:
		nq.readPlaylistFile()
		nq.writeFiles()
	else:
		p.error("-i or -c is required.  -h for help.\n")


class EnqueueWrapper(object):
	def __init__(self, *initial_data, **kwargs):
		# note names used in add_option() must match names used here
		self.db_file              = DB_FILE
		self.output_dir           = OUTPUT_DIR
		self.playlists_file       = PLAYLISTS_FN
		self.skip_playlists       = ('Music', 'Now Playing', 'Duplicate Files', 'Missing Files')
		self.number_errors        = 0
		self.playlists_to_copy    = []
		for dictionary in initial_data:
			for key in dictionary:
				setattr(self, key, dictionary[key])
		for key in kwargs:
			setattr(self, key, kwargs[key])


	def _getDateTimeString(self, secs=None):
		if time.daylight:
			tz = time.tzname[1]
		else:
			tz = time.tzname[0]
		#print str(datetime.datetime.utcnow()) + ' UTC ' + str(time.timezone) + tz
		# use datetime to get microsecs, use time to get timezone and custom formatting
		return time.strftime('%Y-%m-%d %A %I:%M:%S %p %Z', time.localtime())


	def _makeUnique(self, dictionary, key, suffix=None):
		key2 = key
		if not suffix == None:
			key2 = key + '_v' + str(suffix)
		if key2 not in dictionary:
			return key2
		else:
			if suffix == None:
				suffix = 2
			else:
				suffix += 1
			return self._makeUnique(dictionary, key, suffix)


	def createPlaylistFile(self):
		f = open(self.playlists_file, 'w')
		f.write( '''#
# Playlists file, generated from Enqueue %s
# 
# Any line begining with a hash is a comment and is ignored.
# Comment out or delete unwanted playlists. If a second playlist
# exists with the same name, a _v2 is appended. If a third, a _v3, etc.
# NOTE: playlist name must not begin with # or whitespace
#
''' 
			% self._getDateTimeString() )
		for playlist_name in sorted(self.playlists_info.keys()):
			num_songs = len(self.playlists_info[playlist_name])
			if self.skip_empty_playlists and (num_songs == 0):
				continue
			f.write("# %s contains %s songs\n%s\n" % (playlist_name, num_songs, playlist_name) )
		f.close()
		print "Created playlist file: "+ self.playlists_file

	def readPlaylistFile(self):
		self.playlists_to_copy = []
		f = open(self.playlists_file, 'r')
		for line in f.readlines():
			# NOTE: playlist name must not begin with # or whitespace
			m = re.match("([^#\s].*?)\n*$", line)
			if m:
				#print "matched '%s'" %  str(m.group(1))
				self.playlists_to_copy.append( str(m.group(1)) )
		f.close()
		print "Found %s playlists to copy" % len(self.playlists_to_copy)

	def writeFiles(self):
		print "Copying files to %s ..." % self.output_dir
		self.songs2copy = []
		self.files_needed = []
		self.copied_bytes = 0
		self.needed_bytes = 0
		self.unused_bytes = 0
		self.existing_files = os.listdir(self.output_dir)
		
		self.writeM3uFiles()
		self.copySongs()
		self.eraseUnused()
		
		print "output_dir has %s MB that is needed, %s MB was just copied." % \
			(self.getMB(self.needed_bytes), self.getMB(self.copied_bytes))
		if self.erase_unused:
			print "Erased %s MB no longer needed." % self.getMB(self.unused_bytes)
		else:
			print "Could have erased %s MB no longer needed." % self.getMB(self.unused_bytes)
		print "Done.  %s error(s)." % self.number_errors

	def writeM3uFiles(self):
		now = self._getDateTimeString()
		'''  Example:
		#EXTM3U - header - must be first line of file
		#EXTINF - extra info - length (seconds), artist - title
		#EXTINF:157,Zee Avi - Bitter Heart
		bitter_heart.mp3
		'''
		# create playlists (m3u files)
		for playlist_name in self.playlists_to_copy:
			try:
				songs = self.playlists_info[playlist_name]
			except:
				self.number_errors += 1
				print "Error: Skipping unknown playlist: "+ playlist_name
				continue
			print "Creating playlist: " + playlist_name
			m3u_fn = playlist_name + '.m3u'
			m3u_text = "#EXTM3U - \"%s\" playlist generated by chad from Enqueue on %s \n\n" \
			           % (playlist_name, now)
			for song in songs:
				seconds = str( int(song['time']/1000) )
				m3u_text += "# orig path: "+ song['path'] + "\n"
				m3u_text += "#EXTINF:"+ seconds + ", "+ song['artist'] + " - "+ song['title'] + "\n"
				m3u_text += self.getFilename(song['path']) + "\n\n"
				self.songs2copy.append( song['path'] )
			try:
				f = open(self.output_dir + m3u_fn, 'w')
				f.write(m3u_text.encode('utf-8')) # encode from unicode to type str
				f.close()
				self.copied_bytes += self.getFileBytes( self.output_dir + m3u_fn )
				self.files_needed.append(m3u_fn)
			except Exception,e:
				self.number_errors += 1
				print "M3U Error: "+ str(e)
				print "m3u_fn: %s \n" % m3u_fn


	def copySongs(self):
		# m3u files are written, now copy all necessary audio files
		for remote_path in self.songs2copy:
			local_fn = self.getFilename(remote_path)
			self.files_needed.append(local_fn)
			if local_fn in self.existing_files:
				print "Not copying, already exists: " + self.output_dir + local_fn
				continue
			remote_fn = self.convertPath(remote_path)
			print "    Copying file from: " + remote_fn
			print "    Copying file to  : " + self.output_dir + local_fn + "\n"
			self.needed_bytes += self.getFileBytes( remote_fn )
			if self.m3u_only:
				return
			shutil.copy2(remote_fn, self.output_dir + local_fn) # copy2 preserves modification time, etc
			self.copied_bytes += self.getFileBytes( self.output_dir + local_fn )
			'''
			remote_fo = urllib2.urlopen(path)
			with open(self.output_dir + local_fn, 'wb') as local_fo:
				print "Copying to "+ local_fn
				shutil.copyfileobj(remote_fo, local_fo)
			'''

	def eraseUnused(self):
		# Check to remove files no longer used in output directory
		for fn in self.existing_files:
			if fn in self.files_needed:
				self.needed_bytes += self.getFileBytes( self.output_dir + fn )
				print "File is needed: " + self.output_dir + fn
				continue
			#full_file_name = os.path.join(self.output_dir, local_fn)
		    #if (os.path.isfile(full_file_name)):
			self.unused_bytes += self.getFileBytes( self.output_dir + fn )
			if self.erase_unused:
				print "Deleting file no longer needed: " + self.output_dir + fn
				os.remove( self.output_dir + fn )


	def getFilename(self, path):
		fn = re.sub(r'.*\/', '', path)
		fn = urllib.unquote(fn)
		#fn = re.sub(r'%20','_', fn)
		# todo: add to file name something to guarantee file name is unique, like
		# size in bytes, modification time, or better yet - sha1 hash of file
		unique_str = '00'
		try:
			statinfo = os.stat( self.convertPath(path) )
			unique_str = str(statinfo.st_size) # size in bytes is fast and good enough for now
			#unique_str = base36(statinfo.st_size) 
			#print "SIZE: bytes: %d, str: %s\n" % (statinfo.st_size, base36(statinfo.st_size))
		except OSError, e:
			self.number_errors += 1
			print "OS Error: "+ str(e)
			
		fn = re.sub( r'^(.*)(\.[^\.]+)$', \
			lambda m: "%s_%s%s" % (m.group(1), unique_str, m.group(2)), fn)
		return fn


	# converts 
	def convertPath(self, path):
		p = urlparse.urlparse(path)
		if not p.scheme == 'file':
			self.number_errors += 1
			print "\nWARNING: FIX convertPath: "+ path
		#fn = urllib.url2pathname(p.path)  # does not convert as expected
		fn = urllib.url2pathname(p.path).encode('latin-1') # does work
		#print "convertPath() Orig path: %s" % path
		#print "convertPath() New path (%s): %s\n" % (type(fn), fn)
		return fn


	def filesafe(self, name):
		# no / or \ allowed in name
		name = re.sub(r'(/|\\)', '-', name)  
		return name
		
	def getFileBytes(self, fn):
		bytes = 0
		try:
			statinfo = os.stat( fn )
			bytes = statinfo.st_size
		except OSError, e:
			self.number_errors += 1
			print "Error: "+ str(e)
		return bytes


	def getMB(self, int_x):
		return str(round( int_x / (1024*1024), 1))


	def base36(int_x):
		BASE36 = '1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ' 
		base36_x = ''
		while int_x >= 36:
		    div, mod = divmod(int_x, 36)
		    base36_x = BASE36[mod] + base36_x
		    int_x = int(div)
		return BASE36[int_x] + base36_x


	def readDB(self, stats=False):
		self.stats          = {}
		self.playlists_info = {}
		conn                = sqlite3.connect(self.db_file)
		conn.row_factory    = sqlite3.Row # allows dictionary access, row['col_name']
		c = conn.cursor()
		c.execute('SELECT * FROM playlists')
		rows_playlists = c.fetchall()
		for row in rows_playlists:
			if row['title'] in self.skip_playlists:
				continue
			cur_playlist = []
			#print "==> "+ row['title']
			playlist_name = self._makeUnique(self.playlists_info, self.filesafe(row['title']))
			c2 = conn.cursor()
			for items in c2.execute("SELECT * FROM playlist_items WHERE playlist_id='%d' ORDER BY playlist_index" % row['playlist_id']):
				c3 = conn.cursor()
				c3.execute("SELECT * FROM library WHERE file_id='%s'" % items['file_id'])
				song_info = c3.fetchone()
				cur_playlist.append( song_info )
			self.playlists_info[ playlist_name ] = cur_playlist
		if not stats:
			conn.close()
			return
		self.stats['total_playlists'] = len(rows_playlists)
		c = conn.cursor()
		c.execute('SELECT COUNT(*) FROM library')
		self.stats['total_songs'] = c.fetchone()[0]
		c = conn.cursor()
		c.execute('SELECT SUM(size) FROM library')
		self.stats['total_songs_bytes'] = c.fetchone()[0]
		c = conn.cursor()
		c.execute('SELECT SUM(time) FROM library')
		self.stats['total_songs_time'] = c.fetchone()[0]
		self.stats['total_songs_gbytes'] = round(self.stats['total_songs_bytes']/(1024**3), 2)
		self.stats['avg_song_size'] = round(self.stats['total_songs_bytes']/self.stats['total_songs'], 1)
		self.stats['avg_song_time'] = round(self.stats['total_songs_time']/self.stats['total_songs'], 1)
		print self.stats
		conn.close()

if __name__ == '__main__':
	main()

'''
Following from enqueue sql db:

CREATE TABLE playlists (
playlist_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
type INT,	
title TEXT,
rules BLOB,
listViewColumnInfo BLOB,
listViewSortColumn INT DEFAULT 2 NOT NULL,
listViewAscending INT DEFAULT 1 NOT NULL,
albumListViewColumnInfo BLOB,
albumListViewSortColumn INT DEFAULT -1 NOT NULL,
albumListViewAscending INT DEFAULT 1 NOT NULL,
search TEXT DEFAULT '' NOT NULL,
browser_1_attribute INT DEFAULT 0 NOT NULL,
browser_2_attribute INT DEFAULT 0 NOT NULL,
browser_3_attribute INT DEFAULT 2 NOT NULL,
browser_1_selection BLOB,
browser_2_selection BLOB,
browser_3_selection BLOB,
browserInfo BLOB,
libraryViewMode INT DEFAULT 0 NOT NULL );

CREATE TABLE playlist_items (
playlist_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
playlist_id INTEGER NOT NULL,
playlist_index INTEGER NOT NULL,
file_id INTEGER NOT NULL,
UNIQUE(playlist_id,
playlist_index),
FOREIGN KEY(playlist_id) REFERENCES playlists(playlist_id) ON UPDATE CASCADE ON DELETE CASCADE,
FOREIGN KEY(file_id) REFERENCES library(file_id) ON UPDATE CASCADE ON DELETE CASCADE);

CREATE TABLE library (
file_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
path TEXT NOT NULL UNIQUE,
title TEXT NOT NULL DEFAULT '',
artist TEXT NOT NULL DEFAULT '',
album TEXT NOT NULL DEFAULT '',
albumArtist TEXT NOT NULL DEFAULT '',
composer TEXT NOT NULL DEFAULT '',
comments TEXT NOT NULL DEFAULT '',
genre TEXT NOT NULL DEFAULT '',
year INT NOT NULL DEFAULT 0,
trackNumber INT NOT NULL DEFAULT 0,
trackCount INT NOT NULL DEFAULT 0,
discNumber INT NOT NULL DEFAULT 0,
discCount INT NOT NULL DEFAULT 0,
BPM INT NOT NULL DEFAULT 0,
checkSum BLOB NOT NULL DEFAULT x'',
size INT NOT NULL DEFAULT 0,
kind INT NOT NULL DEFAULT 0,
time INT NOT NULL DEFAULT 0,
bitrate INT NOT NULL DEFAULT 0,
channels INT NOT NULL DEFAULT 0,
sampleRate INT NOT NULL DEFAULT 0,
lastModified TEXT NOT NULL DEFAULT '',
albumArt INT NOT NULL DEFAULT 0,
dateAdded TEXT NOT NULL DEFAULT '',
lastPlayed TEXT NOT NULL DEFAULT '',
playCount INT NOT NULL DEFAULT 0,
rating INT NOT NULL DEFAULT 0,
artistAlbumArtist TEXT NOT NULL DEFAULT '' ,
lyrics TEXT NOT NULL DEFAULT '',
compilation INT NOT NULL DEFAULT 0);

'''



