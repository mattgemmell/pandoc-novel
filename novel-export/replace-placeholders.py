#!/usr/bin/python

# Usage: replace-placeholders.py TEXT_FILE JSON_FILE [EXTRA_JSON_STRING]

# Takes an input TEXT_FILE and a variables (simple list of key-value pairs) JSON_FILE.
# Additional JSON key-value pairs can optionally be specified in EXTRA_JSON_STRING.
# Replaces all occurrences of variables' placeholders with their values in TEXT_FILE.

# The placeholders have the form "%key%".
# For example, given the JSON pair:	"name": "Bob",
# all occurrences of "%name%" are replaced with "Bob".

# Note: this UPDATES/OVERWRITES the input TEXT_FILE without warning!

import sys
import json
import re

# Check we have two params. (Arg 0 is this script itself).
if len(sys.argv) >= 3:
	text_file_path = sys.argv[1]
	json_file_path = sys.argv[2]
	
	try:
		# Read the text file.
		text_file = open(text_file_path, 'r')
		text_contents = text_file.read()
		text_file.close()
		
		try:
			# Read the JSON file.
			json_file = open(json_file_path, 'r')
			json_contents = json.load(json_file)
			json_file.close()
			
			# Check for extra JSON variables.
			if len(sys.argv) >= 4:
				extra_json_string = sys.argv[3]
				try:
					extra_json = json.loads(extra_json_string)
					json_contents.update(extra_json)
				except ValueError as e:
					print("An error occurred: %s" % e)
			
			# Replace all occurrences of key placeholders in text_contents.
			for key, value in json_contents.items():
				#print(f"{key}: {value}")
				text_contents = text_contents.replace(f"%{key}%", value)
			
			# Save text_file.
			try:
				text_file = open(text_file_path, 'w')
				text_file.write(text_contents)
				text_file.close()
			except IOError as e:
				print("An IOError occurred: %s" % e)
				
		except IOError:
			print("Couldn't read JSON file: " + json_file_path)
		
	except IOError:
		print("Couldn't read text file: " + text_file_path)

else:
	print("Usage: replace-placeholders.py TEXT_FILE JSON_FILE [EXTRA_JSON_STRING]")
