#!/usr/bin/env python
import sys
import sqlite3
import pprint

db_file = '/Users/chadn/Library/Application Support/Enqueue/Enqueue.db'
out_dir = 'playlists/'

playlist_files   = {}
skip_playlists   = ('Music', 'Now Playing', 'Duplicate Files', 'Missing Files')
conn             = sqlite3.connect(db_file)
conn.row_factory = sqlite3.Row # allows dictionary access, row['col_name']


def main():
	c = conn.cursor()

	for row in c.execute('SELECT * FROM playlists'):
		if row['title'] in skip_playlists:
			continue
		playlist_items = []
		c2 = conn.cursor()
		for items in c2.execute("SELECT * FROM playlist_items WHERE playlist_id='%d' ORDER BY playlist_index" % row['playlist_id']):
			c3 = conn.cursor()
			c3.execute("SELECT * FROM library WHERE file_id='%s'" % items['file_id'])
			song_info = c3.fetchone()
			playlist_items.append( song_info['path'] )
		playlist_files[ row['title'] ] = playlist_items
	print pprint.pprint(playlist_files)


main()


'''
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



