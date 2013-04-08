<!-- tips on markdown http://stackoverflow.com/questions/10240125/working-with-readme-md-on-github-com -->
<!-- live preview of github markdown: http://tmpvar.com/markdown.html -->

Readme for android-utils
========================

I created this project to store scripts and/or utilities for android devices like my Droid Bionic phone.


enqueue-playlists.py
--------------------

This script is made for people who use Enqueue, a mac audio player and playlist organizer.  
The main reason I use Enqueue is because it is a fast and easy way to make a playlist from songs that 
exist on external drives or other computers, especially when dealing with thousands of songs and 
hundreds of GB of music. iTunes is not good at that.  [More 
reasons](http://www.macworld.com/article/1167567/enqueue_plays_audio_files_that_itunes_cant_handle.html)
to [get Enqueue](https://itunes.apple.com/us/app/enqueue/id493119959?mt=12)

After using Enqueue to create playlists, use this script to copy a m3u playlist file and all songs
it needs to android (USB mounted) or to a local directory (to sync later with android).  Of course
you don't have to copy to android, you can just use this to copy songs to local drive.


Here's a sample 

	% ./enqueue-playlists.py -h
	Usage: enqueue-playlists.py [options]

	  Creates playlist m3u files from enqueue db, writes m3u files to output
	directory, and copies all  songs needed in m3u files to same output directory.
	Only playlists listed in "playlists_file" will be created in output directory.
	It's best to create initial "playlists_file" with -i, then edit file
	commenting out playlists to skip, then invoke again with -c to copy.

	Options:
	  -h, --help            show this help message and exit
	  -v, --verbose         returns verbose output
	  --erase_unused        Erase files in dest_dir that are not used by m3u
	                        playlists
	  --skip_empty_playlists
	                        Skip playlists that have 0 songs
	  --db_file=DB_FILE     Enqueue db file. Default:
	                        /Users/chadn/Library/Application
	                        Support/Enqueue/Enqueue.db
	  --dest_dir=DEST_DIR   directory that will contain newly created playlists
	                        and songs. Default: playlists/
	  -p PLAYLISTS_FILE, --playlists_file=PLAYLISTS_FILE
	                        File containing list of playlists to export, created
	                        using -i. Default: playlists.txt
	  -i, --initialize_playlists_file
	                        Initialize the "playlists_file" based on current
	                        playlists in Enqueue, replacing any existing file.  Do
	                        not create any other files.
	  -c, --copy_playlists  Copy to "dest_dir" all playlists from the
	                        "playlists_file", and songs referenced by them.
	  -m, --m3u_only        Only create playlist m3u files, do not copy any songs.
	  --stats               Output stats on the Enqueue DB
	
	% time ./enqueue-playlists.py -v --dest_dir=/Volumes/BIONIC32GB/chadmedia -c --stats
	 ....


## Licence

android-utils is released under the MIT license:

* [http://www.opensource.org/licenses/MIT](http://www.opensource.org/licenses/MIT)


[![githalytics.com alpha](https://cruel-carlota.pagodabox.com/d6b93797ab1d55576a6f0d2a6f36beca "githalytics.com")](http://githalytics.com/chadn/android-utils)
