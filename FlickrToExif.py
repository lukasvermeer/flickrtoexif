#!/usr/bin/env python

# Tagged, Geotagged and given many pictures a title in Flickr? Want to copy that metadata
# to your local image files so that Picasa (or another photo management tool) can also
# benefit? This script should do the trick.
#
# This script takes as an argument a bunch of images. It then tries to find these same
# images on your Flickr account based on "DateTimeOriginal". If it finds one match (and
# only one match) it will copy title, tags and geolocation to the local exif data.
#
# ABSOLUTELY NO WARRANTY. MAKE SURE YOU HAVE BACKUPS!

import argparse
import subprocess
import flickrapi
import re

api_key = 'a1dd0b738929c7da854234add4f6580c'
api_secret = '0769e4c49cea4ca0'

username = 'lukasvermeer' # You probably want to change this ...
machine_title = re.compile('\d+_\d')

parser = argparse.ArgumentParser()
parser.add_argument('--auth', action='store_true')
parser.add_argument('photos', nargs='+')
args = parser.parse_args()

flickr = flickrapi.FlickrAPI(api_key, api_secret)

if args.__dict__['auth']:
	flickr.authenticate_via_browser(perms='read')

for photo in args.__dict__['photos']:
	# TODO According to the Flickr documentation I should be able to use this to find the 
	# TODO exact picture I need, but I can't seem to get it to work. A shame. Leaving this 
	# TODO here for future reference.
	# unique_id = commands.getstatusoutput('exiftool -EXIF:ImageUniqueID %s'%photo)[1].split(' : ')[1]
	# matches = flickr.photos.search(user_id=username, machine_tags="ExifIFD:ImageUniqueID=\"%s\""%unique_id)
	
	print photo
	dt_org = subprocess.check_output(['exiftool','-EXIF:DateTimeOriginal',photo])
	if (len(dt_org) == 0):
		print '%s -- does not seem to have an exif creation date. SKIPPING.' % (photo)
	else:
		create_date = dt_org.splitlines()[0].split(' : ')[1].replace(':','-',2)
		print '%s -- creation date %s' % (photo, create_date)

		matches = flickr.photos.search(user_id=username, min_taken_date=create_date, max_taken_date=create_date, extras='tags,geo')
		if len(matches[0]) == 0:
			print 'ZERO matches found. SKIPPING because cannot find photo on Flickr.'
		elif len(matches[0]) == 1:

			t = matches[0][0].get('title')
			if (t):
				if subprocess.check_output(['exiftool','-XMP:Description','-IPTC:Caption-Abstract',photo]):
					print '%s already has title data. SKIPPING to avoid overwriting.' % photo
				elif machine_title.match(t):
					print '%s looks like a machine generated title. SKIPPING.' % t
				else:
					print '%s writing title data: %s' % (photo, t)
					# TODO Write all changes at once
					subprocess.check_output(['exiftool','-overwrite_original_in_place','-XMP:Description="'+t+'"','-IPTC:Caption-Abstract="'+t+'"',photo])
			else:
				print '%s no title data found.' % photo

			if (matches[0][0].get('tags')):
				tags = matches[0][0].get('tags').split(' ')
				tags_check = subprocess.check_output(['exiftool', '-IPTC:Keywords', '-XMP:Subject', photo])
				if tags_check:
					print '%s already has tag data. MERGING to avoid overwriting.' % photo
					old_tags = {}
					merged_tags = {}
					for t in tags:
						merged_tags[t] = 1
					for line in tags_check.split('\n'):
						for t in (line.split(': ')[-1]).split(', '):
							if (t):
								merged_tags[t] = 1
								old_tags[t] = 1
					if len(set(old_tags.keys()) ^ set(merged_tags.keys())) == 0:
						print '%s already has all merged tag data. SKIPPING to avoid overwriting.' % photo
					else:
						print '%s is missing some tag data. Writing MERGED tags.' % photo
						print 'Tags in Exif  : %s' % old_tags.keys()
						print 'Tags on Flickr: %s' % tags
						print 'Merged tags   : %s' % merged_tags.keys()
						# TODO Write all changes at once
						subprocess.check_output(['exiftool', '-sep',',', '-overwrite_original_in_place', '-IPTC:Keywords='+','.join(merged_tags.keys())+'', '-XMP:Subject='+','.join(merged_tags.keys())+'', photo])
				else:
					print '%s writing tag data: %s' % (photo, tags)
					# TODO Write all changes at once
					subprocess.check_output(['exiftool', '-sep',',', '-overwrite_original_in_place', '-IPTC:Keywords='+','.join(tags)+'', '-XMP:Subject='+','.join(tags)+'', photo])
			else:
				print '%s no tag data found.' % photo

			geo_lat = matches[0][0].get('latitude')
			geo_lon = matches[0][0].get('longitude')
			if (geo_lat and geo_lon and geo_lat != '0' and geo_lon != '0'):
				if subprocess.check_output(['exiftool', '-GPSLongitude', '-GPSLatitude', photo]):
					print '%s already has geotag data. SKIPPING to avoid overwriting.'%photo
				else:
					print '%s writing geotag data: %s, %s' % (photo, geo_lat, geo_lon)
					subprocess.check_output(['exiftool', 
						'-overwrite_original_in_place', 
						'-GPSLongitude="'+geo_lon+'"',
						'-GPSLongitudeRef='+('E' if geo_lon>0 else 'W'), 
						'-GPSLatitude="'+geo_lat+'"', 
						'-GPSLatitudeRef='+('N' if geo_lon>0 else 'S'), 
						'-GPSAltitudeRef=above', photo])
			else:
				print '%s no geotag data found.' % photo
		else:
			# TODO Use UniqueImageID?
			print 'MULTIPLE matches found. SKIPPING to avoid mismatching.'