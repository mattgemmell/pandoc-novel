#!/usr/bin/python

# This script requires Python to already be installed.
# Call this script with the -h flag for help with parameters.

# This is a wrapper to build-book.sh which automatically supplies a suitable output filename for generated books.
# It should be useful for various automation scenarios.
# 
# This script accepts the same arguments as build-book.sh, except for the output filename.
# Arguments are passed to build-book.sh as-is.
# The output filename is constructed via the metadata JSON file, as follows:
#		- If an entry called "filename" is present in the JSON file, it will be used.
#		- Otherwise, the "title" entry (which is required) will be converted to a suitable filename.

import sys
import os
import argparse
import json
import re

def string_to_slug(text):
		# Via: https://www.slingacademy.com/article/python-ways-to-convert-a-string-to-a-url-slug/
		
    # Remove non-alphanumeric characters
    text = re.sub(r'\W+', ' ', text)

    # Replace spaces with hyphens
    # And prevent consecutive hyphens
    text = re.sub(r'\s+', '-', text)

    # Remove leading and trailing hyphens
    text = text.strip('-')

    # Convert to lowercase
    text = text.lower()

    return text

valid_modes = ["basic", "templite", "jinja2"]

parser=argparse.ArgumentParser(allow_abbrev=False)
parser.add_argument('--input-folder', '-i', help="Folder containing input Markdown files", type= str, required=True)
parser.add_argument('--json-file', '-j', help="JSON file with book metadata", type= str, required=True)
parser.add_argument('--replacement-mode', '-m', help=f"[optional] Replacement system to use: {', '.join(valid_modes)} or none (default is basic)", type= str, default= "basic")
parser.add_argument('--test', '-t', help="Just display which filename would be used, without actually invoking a build.", action="store_true")
args=parser.parse_known_args()

input_folder_path = args[0].input_folder
json_file_path = args[0].json_file
placeholder_mode = args[0].replacement_mode
test_mode = args[0].test == True

if placeholder_mode not in valid_modes:
	sys.exit(f"Invalid placeholder mode ({placeholder_mode}); should be {', '.join(valid_modes)} or none.")
elif placeholder_mode == "none":
	sys.exit(0)

try:
	# Read the JSON file.
	json_file = open(json_file_path, 'r')
	json_contents = json.load(json_file)
	json_file.close()
	
	# Determine suitable output filename
	output_basename = None
	filename_key = "filename"
	title_key = "title"
	if filename_key in json_contents and json_contents[filename_key] != "":
		output_basename = json_contents[filename_key]
		if test_mode:
				print(f"Using specified filename: {output_basename}")
	else:
		# Slugify the 'title' entry as a filename.
		if title_key in json_contents and json_contents[title_key] != "":
			title_val = json_contents[title_key]
			output_basename = string_to_slug(title_val)
			if test_mode:
				print(f"Converted title '{title_val}' to filename: {output_basename}")
			
		else:
			sys.exit(f"Couldn't find '{filename_key}' or '{title_key}' in metadata file. Aborting.")
	
	if output_basename:
		# Invoke build script
		script_name = "build-book.sh"
		script_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), script_name)
		script_args = f"{input_folder_path} {json_file_path} '{output_basename}' '{placeholder_mode}'"
		extra_args = ""
		if len(args[1]) > 0:
			extra_args = ' '.join(args[1])
			script_args = f"{script_args} {extra_args}"
		command_string = f"{script_path} {script_args}"
		if test_mode:
				print("Test mode: not building anything. In a real run, I'd execute this command:\n", command_string)
		else:
			import subprocess
			try:
				p = subprocess.run([script_path, input_folder_path, json_file_path, output_basename, placeholder_mode, extra_args])
			except Exception as e:
				print("Exception: ", e)
		
except IOError:
	print("Couldn't read JSON metadata file: " + json_file_path)
