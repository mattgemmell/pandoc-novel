#!/usr/bin/python

# Usage: Run this script with the "-h" flag for brief help.
# Documentation: https://github.com/mattgemmell/pandoc-novel/blob/main/README.org

import re
import argparse
import os
import glob
import sys
import datetime
import json
import subprocess

# --- Globals ---

default_metadata_filename = "metadata.json"
exclusions_filename = "exclusions.tsv"
master_basename = "collated-book-master"
tk_pattern = r"(?i)\b(TK)+\b"
valid_placeholder_modes = ["basic", "templite", "jinja2"] # or "none"
valid_output_formats = ["epub", "pdf", "pdf-6x9"] # or "all"
transformations_filename = "transformations.tsv"
verbose_mode = False

# --- Functions ---

def inform(msg, severity="normal", force=False):
	should_echo = (force or verbose_mode or severity=="error")
	if should_echo:
		out = ""
		match severity:
			case "warning":
				out = f"[Warning]: {msg}"
			case "error":
				out = f"[ERROR]: {msg}"
				should_echo = True
			case _:
				out = msg
		print(out)

def sorted_alphanumeric(data):
	# Sorts lexicographically; natural numeric then alphabetical.
	convert = lambda text: int(text) if text.isdigit() else text.lower()
	alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
	return sorted(data, key=alphanum_key)

def string_to_slug(text):
		# Via: https://www.slingacademy.com/article/python-ways-to-convert-a-string-to-a-url-slug/
		
    # Remove non-alphanumeric characters
    text = re.sub(r'\W+', ' ', text)

    # Replace whitespace runs with single hyphens
    text = re.sub(r'\s+', '-', text)

    # Remove leading and trailing hyphens
    text = text.strip('-')

    # Return in lowercase
    return text.lower()

#--- Main script begins ---

parser=argparse.ArgumentParser(allow_abbrev=False)
parser.add_argument('--input-folder', '-i', help="Input folder of Markdown files", type= str, required=True)
parser.add_argument('--exclude', '-e', help=f"[optional] Regular expressions (one or more, space-separated) matching filenames of Markdown documents to exclude from the built books", action="store", nargs='+', default= None)
parser.add_argument('--json-metadata-file', '-j', help="JSON file with metadata", type= str, default=default_metadata_filename)
parser.add_argument('--replacement-mode', '-m', choices=valid_placeholder_modes + ["none"], help=f"[optional] Replacement system to use: {', '.join(valid_placeholder_modes)} (default is {valid_placeholder_modes[0]})", type= str, default= valid_placeholder_modes[0])
parser.add_argument('--output-basename', '-o', help=f"[optional] Output filename without extension (default is automatic based on metadata)", type= str, default= None)
parser.add_argument('--verbose', '-v', help="[optional] Enable verbose logging", action="store_true", default=False)
parser.add_argument('--check-tks', help="[optional] Check for TKs in Markdown files (default: enabled), or disable with --no-check-tks", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument('--stop-on-tks', '-k', help="[optional] Treat TKs as errors and stop", action="store_true", default=False)
parser.add_argument('--run-transformations', help=f"[optional] Perform any transformations found in {transformations_filename} file (default: enabled), or disable with --no-run-transformations", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument('--formats', '-f', help=f"[optional] Output formats to create (as many as required), from: {', '.join(valid_output_formats)}, or all (default 'epub pdf')", action='store', nargs='+', choices=valid_output_formats + ["all"], default=["epub", "pdf"])
parser.add_argument('--retain-collated-master', '-c', help="[optional] Keeps the collated master Markdown file after generating books, instead of deleting it.", action="store_true", default=False)
parser.add_argument('--pandoc-verbose', '-V', help="[optional] Tell pandoc to enable its own verbose logging", action="store_true", default=False)
parser.add_argument('--show-pandoc-commands', '-p', help="[optional] Display the actual pandoc commands and arguments when invoking them for each format", action="store_true", default=False)
args=parser.parse_known_args()

# Obtain configuration parameters
this_script_path = os.path.abspath(os.path.expanduser(sys.argv[0]))
folder_path = args[0].input_folder
exclusions = args[0].exclude
json_file_path = args[0].json_metadata_file
placeholder_mode = args[0].replacement_mode
output_basename = args[0].output_basename
verbose_mode = (args[0].verbose == True)
check_tks = (args[0].check_tks == True)
stop_on_tks = (args[0].stop_on_tks == True)
run_transformations = (args[0].run_transformations == True)
output_formats = args[0].formats
if isinstance(output_formats, list):
	# Uniquify
	output_formats = list(dict.fromkeys(output_formats))
else:
	output_formats = [output_formats]
pandoc_verbose = (args[0].pandoc_verbose == True)
show_pandoc_commands = (args[0].show_pandoc_commands == True)
retain_collated_master = (args[0].retain_collated_master == True)
extra_args = None
if len(args[1]) > 0:
	extra_args = ' '.join(args[1])

# Check if folder_path exists and is a folder.
full_folder_path = os.path.abspath(os.path.expanduser(folder_path))
inform(f"Path to Markdown folder: {full_folder_path}")
if not os.path.isdir(full_folder_path):
	inform("Path to Markdown folder isn't a folder.", severity="error")
	sys.exit(1)

# Check if json_file_path exists and is a file.
full_metadata_path = os.path.abspath(os.path.expanduser(json_file_path))
inform(f"Path to JSON metadata file: {full_metadata_path}")
if not os.path.isfile(full_metadata_path):
	if not full_metadata_path.endswith():
		inform("Path to JSON metadata file isn't a file.", severity="error")
		sys.exit(1)

# Validate placeholder mode.
if placeholder_mode not in valid_placeholder_modes:
	inform(f"Invalid placeholder mode ({placeholder_mode}); should be {', '.join(valid_modes)} or none.", severity="error")
	sys.exit(1)

# Obtain all Markdown files, sorted sensibly.
files = sorted_alphanumeric([p for p in glob.glob(f"{full_folder_path}/**/*", recursive=True) if os.path.isfile(p) and p.endswith((".md", ".markdown", ".mdown"))])

master_documents = []
files_with_tks = []
num_exclusions = 0

# Normalise exclusions and try to load additional patterns from a file.
tsv_delimiter = "\t"
search_key, replace_key, comment_key = "search", "replace", "comment"
exclusions_path = os.path.join(os.path.dirname(full_metadata_path), exclusions_filename)

exclusions_map = []
if exclusions:
	for excl in exclusions:
		exclusions_map.append({search_key: excl})

inform(f"Checking for exclusions file: {exclusions_path}")
if not os.path.isfile(exclusions_path):
	inform(f"Exclusions file not found. Continuing.")
else:
	try:
		# Read the exclusions file.
		exclusions_file = open(exclusions_path, 'r')
		inform(f"Exclusions file found. Processing.")
		for line in exclusions_file:
			components = line.split(tsv_delimiter)
			if len(components) > 0:
				exclusion = {search_key: components[0]}
				if len(components) > 1:
					exclusion[comment_key] = tsv_delimiter.join(components[1:]).rstrip()
				exclusions_map.append(exclusion)
		exclusions_file.close()
	except IOError as e:
		inform(f"Couldn't read exclusions file: {e}", severity="warning")

try:
	for file in files:
		filename = os.path.basename(file)
		excluded = False
		if exclusions_map and len(exclusions_map) > 0:
			for excl in exclusions_map:
				if re.search(excl[search_key], filename):
					excluded = True
					num_exclusions = num_exclusions + 1
					message = ""
					if comment_key in excl:
						message = f"{excl[comment_key]}"
					else:
						message = f"\"{excl[search_key]}\""
					inform(f"- File excluded, as requested: {filename} (matched exclusion: {message})")
					break
		
		if not excluded:
			text_file = open(file, 'r')
			text_contents = text_file.read()
			text_file.close()
			
			master_documents.append(text_contents)
			
		else:
			continue
		
		if check_tks:
			tks = re.findall(r"(?i)\b(TK)+\b", text_contents)
			if len(tks) > 0:
				files_with_tks.append(f"{filename} ({len(tks)} TK{'s' if len(tks) != 1 else ''})")
			
except IOError as e:
	inform(f"Couldn't read Markdown files: {e}", severity="error")
	sys.exit(1)

msg_excluded = ""
if num_exclusions > 0:
	msg_excluded = f" ({num_exclusions} file{'s' if num_exclusions != 1 else ''} excluded)"
inform(f"{len(master_documents)} Markdown files read{msg_excluded}.", force=verbose_mode)

if len(master_documents) == 0:
	inform(f"No files selected for building. Not continuing.", severity="error")
	sys.exit(1)

if check_tks:
	num_tks = len(files_with_tks)
	if num_tks > 0:
		inform(f"TKs are present in the following files:\n{'\n'.join(['- ' + f for f in files_with_tks])}", severity="warning", force=check_tks)
		if stop_on_tks:
			inform("TKs were found and you requested to stop on TKs. Not continuing.", severity="error")
			sys.exit(1)
		else:
			inform(f"(Continuing despite TKs.)", severity="warning", force=check_tks)
	else:
		inform(f"No TKs found.")

# Concatenate master file.
master_contents = "\n".join(master_documents)

# Prepare extra metadata.
now = datetime.datetime.now()
meta_date = now.strftime("%Y-%m-%d")
meta_date_year = now.strftime("%Y")

# Read the JSON metadata file.
json_contents = None
try:
	json_file = open(full_metadata_path, 'r')
	json_contents = json.load(json_file)
	json_file.close()
except IOError as e:
		inform(f"Couldn't read JSON metadata file: {e}", severity="error")
		sys.exit(1)

# Add dynamically-generated extra metadata.
json_contents['date'] = meta_date
json_contents['date-year'] = meta_date_year

# Process transformations.
if run_transformations:
	# Check for any requested transformations.
	transformations_path = os.path.join(os.path.dirname(full_metadata_path), transformations_filename)
	
	inform(f"Checking for transformations file: {transformations_path}")
	if not os.path.isfile(transformations_path):
		inform(f"Transformations file not found. Continuing.")
	else:
		transformations = []
		try:
			# Read the transformations file.
			transformations_file = open(transformations_path, 'r')
			for line in transformations_file:
				components = line.split(tsv_delimiter)
				if len(components) > 1:
					transformation = {search_key: components[0], replace_key: components[1]}
					if len(components) > 2:
						transformation[comment_key] = tsv_delimiter.join(components[2:]).rstrip()
					transformations.append(transformation)
			transformations_file.close()
		except IOError as e:
			inform(f"Couldn't read transformations file: {e}", severity="warning")
		
		if len(transformations) > 0:
			inform("Transformations found. Performing:")
		else:
			inform("No transformations found in file. Continuing.")
		
		# Perform transformations from file.
		for transformation in transformations:
			message = ""
			if comment_key in transformation:
				message = transformation[comment_key]
			else:
				message = f"Replace '{transformation[search_key]}' with '{transformation[replace_key]}'"
			inform(f"- {message}")
			master_contents = re.sub(transformation[search_key], transformation[replace_key], master_contents)

# Process placeholders.
if placeholder_mode == "basic":
	# Replace all occurrences of metadata placeholders in master_contents.
	for key, value in json_contents.items():
		#print(f"{key}: {value} [{type(value)}]")
		master_contents = master_contents.replace(f"%{key}%", str(value))

elif placeholder_mode == "templite":
	try:
		from templite import Templite
		t = Templite(master_contents)
		master_contents = t.render(**json_contents)
	except ImportError as e:
		inform(f"Couldn't find templite module: {e}", severity="warning")
		
elif placeholder_mode == "jinja2":
	try:
		from jinja2 import Template
		template = Template(master_contents)
		master_contents = template.render(json_contents)
	except ImportError as e:
		inform(f"Couldn't find jinja2 for python3: {e}", severity="warning")

# Save master file with timestamp.
timestamp = now.strftime("%Y%m%d-%H%M%S-%f")
master_filename = f"{master_basename}-{timestamp}.md"
try:
	inform(f"Saving collated master file: {master_filename}")
	master_file = open(master_filename, 'w')
	master_file.write(master_contents)
	master_file.close()
except IOError as e:
	inform(f"Couldn't save master file: {e}", severity="error")
	sys.exit(1)

# Determine output basename, if not already specified.
if not output_basename:
	inform(f"No output basename supplied in arguments; checking metadata.")
	basename_key = "basename"
	title_key = "title"
	if basename_key in json_contents and json_contents[basename_key] != "":
		output_basename = json_contents[basename_key]
		inform(f"Using basename specified in metadata: {output_basename}")
	else:
		# Slugify the 'title' entry as a filename.
		if title_key in json_contents and json_contents[title_key] != "":
			title_val = json_contents[title_key]
			output_basename = string_to_slug(title_val)
			inform(f"Converted metadata title '{title_val}' to basename: {output_basename}")
		else:
			inform(f"Couldn't find '{basename_key}' or '{title_key}' in metadata.", severity="error")
			sys.exit(1)
else:
	inform(f"Requested output basename: {output_basename}")

if extra_args:
	inform(f"Found extra arguments. Passing them to pandoc: {extra_args}")

# Invoke pandoc for each format, passing extra_args and warning for unrecognised formats.
inform(f"Output formats requested: {', '.join(output_formats)}")
all_formats = "all" in output_formats
yaml_shared_path = os.path.join(os.path.dirname(this_script_path), "options-shared.yaml")
# Final arg list will be: pre_args + (format-specific args, so settings/styles override properly) + post_args
pandoc_pre_args = ['pandoc', f'--defaults={yaml_shared_path}']
pandoc_post_args = [f'--metadata-file={full_metadata_path}', f'--metadata=date:"{meta_date}"', f'--metadata=date-year:"{meta_date_year}"', master_filename]
# Work around pandoc issue with not accepting css entries in metadata files.
if "css" in json_contents:
	extra_css = json_contents["css"]
	if not isinstance(extra_css, list):
		extra_css = [extra_css]
	for css_arg in extra_css:
		pandoc_post_args.append(f"--css={css_arg}")
if pandoc_verbose:
	pandoc_post_args.append("--verbose")
if extra_args:
	pandoc_post_args.append(extra_args)

for this_format in output_formats:
	if not this_format in valid_output_formats and this_format != "all":
		inform(f"Output format '{this_format}' not presently supported. Skipping.", severity="warning")
	else:
		try:
			if this_format == "epub" or all_formats:
				inform(f"Building epub format with pandoc...")
				yaml_epub_path = os.path.join(os.path.dirname(this_script_path), "options-epub.yaml")
				format_command = pandoc_pre_args + [f'--defaults={yaml_epub_path}', f'--output={output_basename}.epub'] + pandoc_post_args
				if show_pandoc_commands:
					inform(f"Using pandoc command:\n{' '.join(format_command)}")
				p = subprocess.run(format_command)
				
			if this_format == "pdf" or all_formats:
				inform(f"Building pdf format with pandoc...")
				yaml_pdf_path = os.path.join(os.path.dirname(this_script_path), "options-pdf.yaml")
				format_command = pandoc_pre_args + [f'--defaults={yaml_pdf_path}', f'--output={output_basename}.pdf'] + pandoc_post_args
				if show_pandoc_commands:
					inform(f"Using pandoc command:\n{' '.join(format_command)}")
				p = subprocess.run(format_command)
				
			if this_format == "pdf-6x9" or all_formats:
				inform(f"Building pdf-6x9 format with pandoc...")
				yaml_pdf_path = os.path.join(os.path.dirname(this_script_path), "options-pdf.yaml")
				css_pdf_6x9_path = os.path.join(os.path.dirname(this_script_path), "pdf-6x9.css")
				format_command = pandoc_pre_args + [f'--defaults={yaml_pdf_path}', f'--output={output_basename}-6x9.pdf', f'--css={css_pdf_6x9_path}'] + pandoc_post_args
				if show_pandoc_commands:
					inform(f"Using pandoc command:\n{' '.join(format_command)}")
				p = subprocess.run(format_command)
				
		except Exception as e:
			inform(f"Couldn't build {this_format} format with pandoc: {e}", severity="error")
			sys.exit(1)

# Remove temporary master file.
if not retain_collated_master:
	inform(f"Deleting collated master file: {master_filename}")
	try:
		os.remove(master_filename)
	except IOError as e:
		inform(f"Couldn't delete master file: {e}", severity="error")
		sys.exit(1)
else:
	inform(f"Keeping collated master file, as requested: {master_filename}")

inform("Done.")
