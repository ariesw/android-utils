#!/usr/bin/env python
# coding: utf-8


# coding: utf-8
# coding: latin-1
# coding: ascii
'''
NOTE: Python will assume byte strings are ASCII the moment they hit any standard I/O
Fix this to use UTF-8 by doing something like this:

import codecs
fileObj = codecs.open( "someFile", "r", "utf-8" )
u = fileObj.read() # Returns a Unicode string from the UTF-8 bytes in the file

'''
import sys
import os
import urllib
import traceback


def main():
	listdir('non-ascii')
	listdir(u'non-ascii')
	
def listdir(path):
	# matches come from SQLite db value that was generated from mac filesystem
	matches = ['ho%CC%82tel%20costes%20quatre', 'ascii']
	try:
		print "listing directory %s %s: " % (type(path), path),
		files = os.listdir(path)
		print "Found %d files: " % len(files)
		for idx,file in enumerate(files):
			print "file %d: name length:%d, %s" % (idx+1, len(file), type(file))
		#try2match(path)
		for file in files:
			try2match(file, matches)
			#try2match(file)
	except Exception, e:
		print "Error: %s\n%s" % (str(e), traceback.format_exc())
		
	print "\n"


def try2match(obj, matches=None):
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


def to_unicode_or_bust(obj, encoding='utf-8'):
	if isinstance(obj, basestring):
		if not isinstance(obj, unicode):
			obj = unicode(obj, encoding)
			print "obj is a str, not unicode, so encoding to unicode"
	return obj
	'''
	basestring
	    /    \
	unicode  str
	        / |  \
	   ascii utf8 latin-1
	'''

main()


'''
What have i learned

create strings, paths as unicode string



'''