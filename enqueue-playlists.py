#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
import pprint
import traceback
import codecs
import logging

DB_FILE      = os.path.expanduser('~/Library/Application Support/Enqueue/Enqueue.db')
DESTINATION_DIR   = 'playlists/'
PLAYLISTS_FN = 'playlists.txt'


def main():
    p = optparse.OptionParser(description = '''

Creates playlist m3u files from enqueue db, writes m3u files to output directory, and copies all 
songs needed in m3u files to same output directory. 

Only playlists listed in "playlists_file" will be created in output directory. 
It's best to create initial "playlists_file" with -i, then edit file 
commenting out playlists to skip, then invoke again with -c to copy.

    ''')
    # Android Winamp note: 
    # http://android.stackexchange.com/questions/21133/how-can-i-delete-all-winamp-playlists-at-once
    p.add_option('-v', '--verbose', action ='store_true', default=False, help='returns verbose output')
    p.add_option('--erase_unused', action ='store_true', default=False, 
                 help='Erase files in dest_dir that are not used by m3u playlists')
    p.add_option('--skip_empty_playlists', action ='store_true', default=False, 
                 help='Skip playlists that have 0 songs')
    p.add_option('--db_file', help='Enqueue db file. Default: '+ DB_FILE, default=DB_FILE)
    p.add_option('--dest_dir', default=DESTINATION_DIR,
                 help='directory that will contain newly created playlists and songs. Default: '+ DESTINATION_DIR)
    p.add_option('-p', '--playlists_file', default=PLAYLISTS_FN, 
                 help='File containing list of playlists to export, created using -i. Default: '+ PLAYLISTS_FN)
    p.add_option('-i', '--initialize_playlists_file', action ='store_true', default=False,
                 help='Initialize the "playlists_file" based on current playlists in Enqueue, '\
                     +'replacing any existing file.  Do not create any other files.')
    p.add_option('-c', '--copy_playlists', action ='store_true', default=False,
                 help='Copy to "dest_dir" all playlists from the "playlists_file", and songs referenced by them.')
    p.add_option('-m', '--m3u_only', action ='store_true', default=False,
                 help='Only create playlist m3u files, do not copy any songs.')
    p.add_option('--stats', action ='store_true', default=False, help='Output stats on the Enqueue DB')

    options, arguments = p.parse_args()

    nq = EnqueueWrapper(db_file              = options.db_file,
                        dest_dir             = options.dest_dir,
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
        self.dest_dir             = DESTINATION_DIR
        self.playlists_file       = PLAYLISTS_FN
        self.skip_playlists       = ('Music', 'Now Playing', 'Duplicate Files', 'Missing Files')
        self.number_warnings      = 0
        self.number_errors        = 0
        self.playlists_to_copy    = []
        self.fn_bytes             = {}
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

        # set dir to unicode so we get unicode names when doing listdir()
        # more http://docs.python.org/howto/unicode.html#unicode-filenames
        self.dest_dir = unicode(self.dest_dir, 'utf-8')
        if not re.search( os.sep + '$', self.dest_dir):
            self.dest_dir += os.sep
        if not os.path.exists(self.dest_dir):
            raise StandardError('dest_dir path does not exist: '+ self.dest_dir)
        
        if self.verbose:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING)
        self.log = logging.getLogger('NQ')


    def _getDateTimeString(self, secs=None):
        if time.daylight:
            tz = time.tzname[1]
        else:
            tz = time.tzname[0]
        #print str(datetime.datetime.utcnow()) + ' UTC ' + str(time.timezone) + tz
        # use datetime to get microsecs, use time to get timezone and custom formatting
        if not secs:
            secs = time.localtime()
        return time.strftime('%Y-%m-%d %A %I:%M:%S %p %Z', secs)


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
        p_unicode = u'''#
# Playlists file, generated from Enqueue %s
# 
# Any line begining with a hash is a comment and is ignored.
# Comment out or delete unwanted playlists. If a second playlist
# exists with the same name, a _v2 is appended. If a third, a _v3, etc.
# NOTE: playlist name must not begin with # or whitespace
#
''' \
            % self._getDateTimeString()
        for playlist_name in sorted(self.playlists_info.keys()):
            num_songs = len(self.playlists_info[playlist_name])
            if self.skip_empty_playlists and (num_songs == 0):
                continue
            p_unicode += u"# %s contains %s songs\n%s\n" \
                % (playlist_name, num_songs, playlist_name)

        f = codecs.open(self.playlists_file, 'w', "utf-8")
        f.write(p_unicode)
        f.close()
        self.log.info("Created playlist file: "+ self.playlists_file)


    def readPlaylistFile(self):
        self.playlists_to_copy = []
        f = codecs.open(self.playlists_file, 'r', "utf-8")
        for line in f.readlines():
            # NOTE: playlist name must not begin with # or whitespace
            m = re.match("([^#\s].*?)\n*$", line)
            if m:
                self.playlists_to_copy.append( str(m.group(1)) )
        f.close()
        self.log.info("Found %s playlists to copy from: %s" % (len(self.playlists_to_copy), self.playlists_file))


    def writeFiles(self):
        self.log.info("Copying files to %s ..." % self.dest_dir)
        self.songs2copy = []
        self.files_needed = []
        self.copied_bytes = 0
        self.needed_bytes = 0
        self.unused_bytes = 0
        self.existing_dest_files = os.listdir(self.dest_dir)
        
        self.writeM3uFiles()
        self.copySongs()
        self.eraseUnused()
        
        self.log.info("dest_dir has %s MB that is needed, %s MB was just copied." % \
            (self.getMB(self.needed_bytes), self.getMB(self.copied_bytes)))
        if self.erase_unused:
            self.log.info("Erased %s MB no longer needed." % self.getMB(self.unused_bytes))
        else:
            self.log.info("Could have erased %s MB no longer needed." % self.getMB(self.unused_bytes))
        self.log.info("Done.  %s warning(s), %s error(s)." % (self.number_warnings, self.number_errors))


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
                self.number_warnings += 1
                log.warning("Skipping unknown playlist: "+ playlist_name)
                continue
            self.log.info("Creating playlist: " + playlist_name)
            m3u_fn = playlist_name + '.m3u'
            m3u_unicode = u"# -*- coding: utf-8 -*-\n"
            m3u_unicode += "#EXTM3U - \"%s\" Enqueue playlist generated by chad %s\n#\n" \
                       % (playlist_name, now)
            for song in songs:
                seconds = str( int(song['time']/1000) )
                m3u_unicode += "# orig path: "+ song['path'] + "\n"
                m3u_unicode += "#EXTINF:%s, %s - %s\n" % \
                    (seconds, self.sql_decode(song['artist']), self.sql_decode(song['title']) )
                m3u_unicode += self.dbPath2DestFn(song['path']) + "\n\n"
                self.songs2copy.append( song['path'] )
            try:
                f = codecs.open(self.dest_dir + m3u_fn, 'w', "utf-8")
                f.write(m3u_unicode) # encode from unicode to type str
                f.close()
                self.copied_bytes += self.getFileBytes( self.dest_dir + m3u_fn )
                self.files_needed.append(m3u_fn)
            except Exception,e:
                self.number_errors += 1
                self.log.error("M3U Error: %s\nm3u_fn: %s\n" % (str(e), m3u_fn))


    def copySongs(self):
        # m3u files are written, now copy all necessary audio files
        for db_path in self.songs2copy:
            dest_fn      = self.dbPath2DestFn(db_path)
            src_path_fn  = self.dbPath2SrcPathFn(db_path)
            dest_path_fn = self.dest_dir + dest_fn
            self.files_needed.append(dest_fn)
            if dest_fn in self.existing_dest_files:
                self.log.info("Not copying, already exists: " + dest_path_fn.encode('utf-8'))
                continue
            if self.getFileBytes( dest_path_fn, True ):
                self.log.info("Not copying, just made a copy: " + dest_path_fn.encode('utf-8'))
                continue
            self.needed_bytes += self.getFileBytes( src_path_fn )
            if self.m3u_only:
                self.log.info("Not copying, m3u_only: " + dest_path_fn.encode('utf-8'))
                continue

            self.log.info("    Copying file from: " + src_path_fn)
            self.log.info("    Copying file to  : " + dest_path_fn + "\n")
            shutil.copy2(src_path_fn, dest_path_fn) # copy2 preserves modification time, etc
            self.copied_bytes += self.getFileBytes( dest_path_fn, True )
            '''
            If enqueue ever supports music files on the web, http style, then use something like this:
            remote_fo = urllib2.urlopen(path)
            with open(self.dest_dir + dest_fn, 'wb') as local_fo:
                print "Copying to "+ dest_fn
                shutil.copyfileobj(remote_fo, local_fo)
            '''


    def eraseUnused(self):
        # Check to remove files no longer used in output directory
        for fn in self.existing_dest_files:
            if fn in self.files_needed:
                self.needed_bytes += self.getFileBytes( self.dest_dir + fn )
                self.log.debug("File is needed: " + self.dest_dir + fn)
                continue
            #full_file_name = os.path.join(self.dest_dir, dest_fn)
            #if (os.path.isfile(full_file_name)):
            self.unused_bytes += self.getFileBytes( self.dest_dir + fn )
            if self.erase_unused:
                self.log.info("Deleting file no longer needed: " + self.dest_dir + fn)
                os.remove( self.dest_dir + fn )


    # returns unicode string containing destination filename, converted from sql db
    def dbPath2DestFn(self, path):
        p = urlparse.urlparse(path)
        if not p.scheme == 'file':
            self.number_warnings += 1
            self.log.warning("WARNING: FIX dbPath2DestFn: "+ path)
        #path_fn = urllib.url2pathname(p.path)  # converts to unicode, does not work
        path_fn    = urllib.url2pathname(p.path)   # works with python ?
        #path_fn_latin1 = urllib.url2pathname(p.path).encode('latin-1') # works with print, files
        # todo: add to file name something that will guarantee file name is unique, like
        # size in bytes, modification time, or better yet - sha1 hash of file
        unique_str = '00'
        fn = path_fn
        try:
            # size in bytes is fast and good enough for now
            path_fn_uni = urllib.url2pathname(p.path).encode('latin-1').decode('utf-8')
            fn = path_fn_uni
            unique_str = self.getFileBytes( path_fn_uni )
        except OSError, e:
            self.number_errors += 1
            self.log.error("dbPath2DestFn() OS Error: "+ str(e))
        except (UnicodeDecodeError, UnicodeEncodeError):
            self.number_warnings += 1
            self.log.warning("dbPath2DestFn() decode/encode error, calling try2match() ")
            self.try2match(urllib.url2pathname(p.path))
            
        fn = re.sub(r'.*\/', '', fn) # remove path, leave only file name
        fn = re.sub( r'^(.*)(\.[^\.]+)$', \
            lambda m: "%s_%s%s" % (m.group(1), unique_str, m.group(2)), fn)
        return fn


    # converts path from Enqueue db (SQLite) to mac os file system path
    def dbPath2SrcPathFn(self, path):
        p = urlparse.urlparse(path)
        if not p.scheme == 'file':
            self.number_warnings += 1
            self.log.warning("WARNING: FIX dbPath2SrcPathFn: "+ path)
        path_fn = urllib.url2pathname(p.path)  # converts to unicode, does not work
        path_fn = urllib.url2pathname(p.path).encode('latin-1') # does work
        #path_fn = urllib.unquote(p.path)  
        #print "dbPath2SrcPathFn() Orig path: %s" % path
        #print "dbPath2SrcPathFn() New path (%s): %s" % (type(path_fn), path_fn)
        return path_fn


    def filesafe(self, name):
        # no / or \ allowed in name
        name = re.sub(r'(/|\\)', '-', name)  
        return name


    def getFileBytes(self, fn, force_stat=False):
        ''' Returns number of bytes of fn if exists and stat succedes, 0 otherwise'''
        if not force_stat:
            if fn in self.fn_bytes:
                return self.fn_bytes[fn]
        self.fn_bytes[fn] = 0
        try:
            statinfo = os.stat( fn )
            self.fn_bytes[fn] = statinfo.st_size
        except OSError, e:
            if e.errno != 2:
                # errno 2 is "No such file or directory"
                self.log.warning(e)
                self.log.warning("getFileBytes() warning (%s): %s\n%s" % 
                    (e.errno, fn, traceback.format_exc()))
        except Exception, e:
            self.number_errors += 1
            self.log.error("getFileBytes() error (%s): %s\n%s" % (type(fn), fn, traceback.format_exc()))
        self.log.debug("SIZE: bytes: %d, str: %s, fn:%s" % (self.fn_bytes[fn], self.base36(self.fn_bytes[fn]), fn))
        return self.fn_bytes[fn]


    def getMB(self, int_x):
        return str(round( int_x / (1024**2), 1))


    def base36(self, int_x):
        BASE36 = '1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ' 
        base36_x = ''
        while int_x >= 36:
            div, mod = divmod(int_x, 36)
            base36_x = BASE36[mod] + base36_x
            int_x = int(div)
        return BASE36[int_x] + base36_x


    def to_unicode_or_bust(obj, encoding='utf-8'):
        if isinstance(obj, basestring):
            if not isinstance(obj, unicode):
                obj = unicode(obj, encoding)
        return obj


    def sql_decode(self, obj):
        return obj # disabling this for now
        obj2 = obj
        try:
            obj2 = obj.encode('latin-1').decode('utf-8')
        except:
            self.log.warning("sql_decode() Error: could not decode obj, calling try2match() ")
            self.try2match(obj)
            '''
            try:
                obj = obj.decode('utf-8')
            except:
                print "Error: could not decode obj from utf-8: %s %s" % (type(obj), obj)
            '''
        #print "sql_decode(obj) %s %s" % (type(obj), obj)
        return obj2


    def try2match(self, obj, matches=None):
        print "\n%26s try2match(obj)" % ''
        for _newobj in [ "obj", 
            "obj.decode('utf-8')",
            "obj.decode('ascii')",
            "obj.decode('latin-1')",
            "obj.encode('utf-8')",
            "obj.encode('ascii')",
            "obj.encode('latin-1')",
            "urllib.unquote(obj)",
            "urllib.quote(obj)",
            "urllib.quote(obj.encode('utf-8'))",
            "urllib.quote(obj.encode('latin-1'))",
            ]:
            print "%40s :" % _newobj,
            try:
                newobj = eval(_newobj)
                if newobj == obj:
                    print "M",
                else:
                    print " ",
                print type(newobj),
                print newobj,
            except Exception, e:
                print "  Error: eval failed"
                #print "Error: %s - %s\n%s" % (_newobj, str(e), traceback.format_exc())
                continue
            if matches:
                if newobj in matches:
                    print "- MATCH!!"
                else:
                    print "- No match"
            else:
                print


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
            playlist_name = self._makeUnique(self.playlists_info, self.filesafe(row['title']))
            c2 = conn.cursor()
            for items in c2.execute("SELECT * FROM playlist_items WHERE playlist_id='%d' ORDER BY playlist_index"
                    % row['playlist_id']):
                c3 = conn.cursor()
                c3.execute("SELECT * FROM library WHERE file_id='%s'" % items['file_id'])
                song_info = c3.fetchone()
                cur_playlist.append( song_info )
            self.playlists_info[ playlist_name ] = cur_playlist
            '''
            TODO: change playlists_info to be an array of tuples:
            buttonSetup = [(310, 350, 'red'), (310, 310, 'yellow'),
                           (310, 270, 'blue')]
            for (x, y, color) in buttonSetup:
            '''

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
        conn.close()

        self.stats['total_songs_gbytes'] = round(self.stats['total_songs_bytes']/(1024**3), 2)
        self.stats['avg_song_size'] = round(self.stats['total_songs_bytes']/self.stats['total_songs'], 1)
        self.stats['avg_song_time'] = round(self.stats['total_songs_time']/self.stats['total_songs'], 1)
        print "Stats on Enqueue Database - "+ self.db_file
        pprint.pprint(self.stats)


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



