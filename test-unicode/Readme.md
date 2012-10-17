<!-- tips on markdown http://stackoverflow.com/questions/10240125/working-with-readme-md-on-github-com -->

Readme for test-unicode
========================

I created test-unicode/* to do some quick sanity tests when dealing with strings and file names with unknown encoding.  It's not meant to be a complete or robust test, but a quick way for you to edit and run test.py to help troubleshoot.

Tips:

* Python will assume byte strings are ASCII the moment they hit any standard I/O 
* Android, Mac, and many *nix prefer UTF-8 for files path/file names. 
* Windows can also use latin-1 for files, or UTF-16 for file names
* DB's - PostgreSQL uses UTF-8 by default, MySQL prefers Latin-1 (sigh)

For more info on python, unicode, and utf-8, I like these

* Software should use unicode internally <http://docs.python.org/howto/unicode.html#tips-for-writing-unicode-aware-programs>
* 2009 June - explanations and examples: <http://lobstertech.com/python_unicode.html>
* 2008 slide presentation - <http://farmdev.com/talks/unicode/>


Here's a sample example output on a mac with UTF-8 terminal 

	% python test.py 
	listing directory <type 'str'> non-ascii:  Found 3 files: 
	file 1: name length:5, <type 'str'>
	file 2: name length:21, <type 'str'>
	file 3: name length:10, <type 'str'>

	  try2match(obj) obj =      <type 'str'> :  ascii
	                                     obj : M <type 'str'> ascii - MATCH!!
	                     obj.decode('utf-8') : M <type 'unicode'> ascii - MATCH!!
	                     obj.decode('ascii') : M <type 'unicode'> ascii - MATCH!!
	                   obj.decode('latin-1') : M <type 'unicode'> ascii - MATCH!!
	                     obj.encode('utf-8') : M <type 'str'> ascii - MATCH!!
	                     obj.encode('ascii') : M <type 'str'> ascii - MATCH!!
	                   obj.encode('latin-1') : M <type 'str'> ascii - MATCH!!
	                     urllib.unquote(obj) : M <type 'str'> ascii - MATCH!!
	                       urllib.quote(obj) : M <type 'str'> ascii - MATCH!!
	       urllib.quote(obj.encode('utf-8')) : M <type 'str'> ascii - MATCH!!
	     urllib.quote(obj.encode('latin-1')) : M <type 'str'> ascii - MATCH!!

	  try2match(obj) obj =      <type 'str'> :  hôtel costes quatre
	                                     obj : M <type 'str'> hôtel costes quatre - No match
	test.py:61: UnicodeWarning: Unicode equal comparison failed to convert both arguments to Unicode - interpreting them as being unequal
	  if newobj == obj:
	                     obj.decode('utf-8') :   <type 'unicode'> hôtel costes quatre - No match
	                     obj.decode('ascii') :   Error: eval failed
	                   obj.decode('latin-1') :   <type 'unicode'> hoÌtel costes quatre - No match
	                     obj.encode('utf-8') :   Error: eval failed
	                     obj.encode('ascii') :   Error: eval failed
	                   obj.encode('latin-1') :   Error: eval failed
	                     urllib.unquote(obj) : M <type 'str'> hôtel costes quatre - No match
	                       urllib.quote(obj) :   <type 'str'> ho%CC%82tel%20costes%20quatre - MATCH!!
	       urllib.quote(obj.encode('utf-8')) :   Error: eval failed
	     urllib.quote(obj.encode('latin-1')) :   Error: eval failed

	  try2match(obj) obj =      <type 'str'> :  Lunático
	                                     obj : M <type 'str'> Lunático - No match
	                     obj.decode('utf-8') :   <type 'unicode'> Lunático - No match
	                     obj.decode('ascii') :   Error: eval failed
	                   obj.decode('latin-1') :   <type 'unicode'> LunaÌtico - No match
	                     obj.encode('utf-8') :   Error: eval failed
	                     obj.encode('ascii') :   Error: eval failed
	                   obj.encode('latin-1') :   Error: eval failed
	                     urllib.unquote(obj) : M <type 'str'> Lunático - No match
	                       urllib.quote(obj) :   <type 'str'> Luna%CC%81tico - No match
	       urllib.quote(obj.encode('utf-8')) :   Error: eval failed
	     urllib.quote(obj.encode('latin-1')) :   Error: eval failed


	listing directory <type 'unicode'> non-ascii:  Found 3 files: 
	file 1: name length:5, <type 'unicode'>
	file 2: name length:20, <type 'unicode'>
	file 3: name length:9, <type 'unicode'>

	  try2match(obj) obj =  <type 'unicode'> :  ascii
	                                     obj : M <type 'unicode'> ascii - MATCH!!
	                     obj.decode('utf-8') : M <type 'unicode'> ascii - MATCH!!
	                     obj.decode('ascii') : M <type 'unicode'> ascii - MATCH!!
	                   obj.decode('latin-1') : M <type 'unicode'> ascii - MATCH!!
	                     obj.encode('utf-8') : M <type 'str'> ascii - MATCH!!
	                     obj.encode('ascii') : M <type 'str'> ascii - MATCH!!
	                   obj.encode('latin-1') : M <type 'str'> ascii - MATCH!!
	                     urllib.unquote(obj) : M <type 'unicode'> ascii - MATCH!!
	                       urllib.quote(obj) : M <type 'unicode'> ascii - MATCH!!
	       urllib.quote(obj.encode('utf-8')) : M <type 'str'> ascii - MATCH!!
	     urllib.quote(obj.encode('latin-1')) : M <type 'str'> ascii - MATCH!!

	  try2match(obj) obj =  <type 'unicode'> :  hôtel costes quatre
	                                     obj : M <type 'unicode'> hôtel costes quatre - No match
	                     obj.decode('utf-8') :   Error: eval failed
	                     obj.decode('ascii') :   Error: eval failed
	                   obj.decode('latin-1') :   Error: eval failed
	                     obj.encode('utf-8') :   <type 'str'> hôtel costes quatre - No match
	                     obj.encode('ascii') :   Error: eval failed
	                   obj.encode('latin-1') :   Error: eval failed
	                     urllib.unquote(obj) : M <type 'unicode'> hôtel costes quatre - No match
	                       urllib.quote(obj) :   Error: eval failed
	       urllib.quote(obj.encode('utf-8')) :   <type 'str'> ho%CC%82tel%20costes%20quatre - MATCH!!
	     urllib.quote(obj.encode('latin-1')) :   Error: eval failed

	  try2match(obj) obj =  <type 'unicode'> :  Lunático
	                                     obj : M <type 'unicode'> Lunático - No match
	                     obj.decode('utf-8') :   Error: eval failed
	                     obj.decode('ascii') :   Error: eval failed
	                   obj.decode('latin-1') :   Error: eval failed
	                     obj.encode('utf-8') :   <type 'str'> Lunático - No match
	                     obj.encode('ascii') :   Error: eval failed
	                   obj.encode('latin-1') :   Error: eval failed
	                     urllib.unquote(obj) : M <type 'unicode'> Lunático - No match
	                       urllib.quote(obj) :   Error: eval failed
	       urllib.quote(obj.encode('utf-8')) :   <type 'str'> Luna%CC%81tico - No match
	     urllib.quote(obj.encode('latin-1')) :   Error: eval failed

Note that the above was copied from a UTF-8 terminal to UTF-8 editor.
If test.py output is redirected to a file, python will try to convert to ascii, and something like this will appear:

	% python test.py >test.py.out
	% cat test.py.out 
	...
	try2match(obj) obj =  <type 'unicode'> :  Error: 'ascii' codec can't encode character u'\u0302' in position 2: ordinal not in range(128)
