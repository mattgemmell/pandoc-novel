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

default_args_filename = "args.txt"
default_metadata_filename = "metadata.json"
default_exclusions_filename = "exclusions.tsv"
default_transformations_filename = "transformations.tsv"
master_basename = "collated-book-master"
tk_pattern = r"(?i)\b(TK)+\b"
valid_placeholder_modes = ["basic", "templite", "jinja2"] # or "none"
valid_output_formats = ["epub", "pdf", "pdf-6x9"] # or "all"
verbose_mode = False
pattern_metadata_flag = "M"
pattern_negate_flag = "N"
pattern_flag_regex = r"^\(\?[a-zA-Z]*({pattern_flag})[^\)]*\)"
pattern_metadata_key_regex = rf"\%([^\%]+?)\%"

# --- Functions ---

def inform(msg, severity="normal", force=False):
	should_echo = (force or verbose_mode or severity=="warning" or severity=="error")
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

def pattern_has_flag(patt, flag):
	return re.match(f"{pattern_flag_regex.format(pattern_flag = flag)}", patt)

def pattern_strip_flag(patt, flag):
	# Remove the pattern flag from this pattern.
	flag_match = pattern_has_flag(patt, flag)
	if flag_match:
		return patt[:flag_match.start(1)] + patt[flag_match.end(1):]
	return patt

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

class MGArgumentParser(argparse.ArgumentParser):
	def convert_arg_line_to_args(self, arg_line):
		# Ignore whitespace or #-commented lines
		if (re.match(r"^[\s]*#", arg_line) or 
				re.match(r"^[\s]*$", arg_line)):
			return []
		# Split on first whitespace to allow full arg+vals per line.
		#return re.split(r"[ =]", arg_line, maxsplit=1)
		return re.split(r"\s+", arg_line, maxsplit=1)

# --- Main script begins ---

# Check for an args file.
found_args_file = False
file_args_prefix = '@'
if os.path.isfile(default_args_filename):
	found_args_file = True
	sys.argv.insert(1, f"{file_args_prefix}{default_args_filename}")

parser=MGArgumentParser(allow_abbrev=False, fromfile_prefix_chars=file_args_prefix)
parser.add_argument('--input-folder', '-i', help="Input folder of Markdown files", type= str, required=True)
parser.add_argument('--exclude', '-e', help=f"[optional] Regular expressions (one or more, space-separated) matching filenames of Markdown documents to exclude from the built books", action="store", nargs='+', default= None)
parser.add_argument('--json-metadata-file', '-j', help="JSON file with metadata", type= str, default=default_metadata_filename)
parser.add_argument('--exclusions-file', '-E', help="File of exclusion rules", type= str, default=default_exclusions_filename)
parser.add_argument('--transformations-file', '-t', help="File of transformations to perform", type= str, default=default_transformations_filename)
parser.add_argument('--replacement-mode', '-m', choices=valid_placeholder_modes + ["none"], help=f"[optional] Replacement system to use: {', '.join(valid_placeholder_modes)} (default is {valid_placeholder_modes[0]})", type= str, default= valid_placeholder_modes[0])
parser.add_argument('--output-basename', '-o', help=f"[optional] Output filename without extension (default is automatic based on metadata)", type= str, default= None)
parser.add_argument('--verbose', '-v', help="[optional] Enable verbose logging", action="store_true", default=False)
parser.add_argument('--check-tks', help="[optional] Check for TKs in Markdown files (default: enabled), or disable with --no-check-tks", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument('--stop-on-tks', '-k', help="[optional] Treat TKs as errors and stop", action="store_true", default=False)
parser.add_argument('--process-figuremark', help=f"[optional] Rewrite any FigureMark-formatted blocks as HTML figures. See documentation.", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument('--run-transformations', help=f"[optional] Perform any transformations found in default or specified transformations file (default: enabled), or disable with --no-run-transformations", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument('--run-exclusions', help=f"[optional] Process any exclusions from --exclude arguments, or in the default or specified exclusions file (default: enabled), or disable with --no-run-exclusions", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument('--formats', '-f', help=f"[optional] Output formats to create (as many as required), from: {', '.join(valid_output_formats)}, or all (default 'epub pdf')", action='store', nargs='+', choices=valid_output_formats + ["all"], default=["epub", "pdf"])
parser.add_argument('--retain-collated-master', '-c', help="[optional] Keeps the collated master Markdown file after generating books, instead of deleting it.", action="store_true", default=False)
parser.add_argument('--pandoc-verbose', '-V', help="[optional] Tell pandoc to enable its own verbose logging", action="store_true", default=False)
parser.add_argument('--show-pandoc-commands', '-p', help="[optional] Display the actual pandoc commands and arguments when invoking them for each format", action="store_true", default=False)
parser.add_argument('--lang', '-l', help="[optional] Define the language for the book being generated (this will overwrite the lang option in the metadata file)", type=str, default="")
args=parser.parse_known_args()

# Obtain configuration parameters
this_script_path = os.path.abspath(os.path.expanduser(sys.argv[0]))
folder_path = args[0].input_folder
exclusions = args[0].exclude
json_file_path = args[0].json_metadata_file
exclusions_path = args[0].exclusions_file
transformations_path = args[0].transformations_file
placeholder_mode = args[0].replacement_mode
output_basename = args[0].output_basename
verbose_mode = (args[0].verbose == True)
check_tks = (args[0].check_tks == True)
stop_on_tks = (args[0].stop_on_tks == True)
process_figuremark = (args[0].process_figuremark == True)
run_transformations = (args[0].run_transformations == True)
run_exclusions = (args[0].run_exclusions == True)
output_formats = args[0].formats
lang = args[0].lang
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

if found_args_file:
	inform(f"Found args file {default_args_filename}. Processing.")

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
	inform("Path to JSON metadata file isn't a file.", severity="error")
	sys.exit(1)

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

# Add any metadata specified as arguments in extra_args.
if args[1] and len(args[1]) > 0:
	metadata_arg_expr = r"(?:--metadata[ =]|-M )([^ =:]+)[=:](['\"].+?['\"]|\S+)"
	# Find all matches in extra_args, then trim any single or double quotes around values.
	for this_arg in re.finditer(metadata_arg_expr, extra_args):
		meta_key, meta_val = this_arg.group(1), this_arg.group(2)
		meta_val = meta_val[1:-1] if len(meta_val) > 2 and meta_val[0] in ['"', "'"] else meta_val
		json_contents[meta_key] = meta_val

# Validate placeholder mode.
if placeholder_mode not in valid_placeholder_modes:
	inform(f"Invalid placeholder mode ({placeholder_mode}); should be {', '.join(valid_modes)} or none.", severity="error")
	sys.exit(1)

# Substitute 'title' and 'subtitle' with the correct translation (if any).
if lang and lang != "":
	json_contents['lang'] = lang
	title_key = f"title_{lang}"
	subtitle_key = f"subtitle_{lang}"
	cover_key= f"cover-image_{lang}"
	if title_key in json_contents:
		json_contents['title'] = json_contents[title_key]
	if subtitle_key in json_contents:
		json_contents['subtitle'] = json_contents[subtitle_key]
	if cover_key in json_contents:
		json_contents['cover-image'] = json_contents[cover_key]

# Obtain all Markdown files, sorted sensibly.
files = sorted_alphanumeric([p for p in glob.glob(f"{full_folder_path}/**/*", recursive=True) if os.path.isfile(p) and p.endswith((".md", ".markdown", ".mdown"))])

master_documents = []
included_file_paths = []
files_with_tks = []
num_exclusions = 0

# Normalise exclusions and try to load additional patterns from a file.
tsv_delimiter = "\t"
exclusion_mode_key, exclusion_scope_key, path_key, search_key, replace_key, comment_key, negation_key = "mode", "scope", "path", "search", "replace", "comment", "negated"
mode_exclude, mode_e, mode_include, mode_i = "exclude", "e", "include", "i"
valid_exclusion_modes = [mode_exclude, mode_e, mode_include, mode_i]
scope_filename, scope_f, scope_filepath, scope_p, scope_fullpath, scope_u, scope_contents, scope_c = "filename", "f", "filepath", "p", "fullpath", "u", "contents", "c"
valid_exclusion_scopes = [scope_filename, scope_f, scope_filepath, scope_p, scope_fullpath, scope_u, scope_contents, scope_c]
path_any = "*"

exclusions_map = []
if exclusions and run_exclusions:
	for excl in exclusions:
		exclusions_map.append({exclusion_mode_key: mode_exclude, exclusion_scope_key: scope_filename, path_key: path_any, search_key: excl})

full_exclusions_path = os.path.abspath(os.path.expanduser(exclusions_path))
inform(f"Checking for exclusions file: {full_exclusions_path}")
if not os.path.isfile(full_exclusions_path):
	inform(f"Exclusions file not found. Continuing.")
elif run_exclusions:
	try:
		# Read the exclusions file.
		exclusions_file = open(full_exclusions_path, 'r')
		inform(f"Exclusions file found. Processing.")
		for line in exclusions_file:
			line = re.sub(r"\t+", "\t", line) # Collapse tab-runs
			components = line.strip('\n').split(tsv_delimiter)
			if len(components) > 3:
				exclusion = {exclusion_mode_key: components[0], exclusion_scope_key: components[1], path_key: components[2], search_key: components[3]}
				if len(components) > 4:
					exclusion[comment_key] = tsv_delimiter.join(components[4:]).rstrip()
				if exclusion[exclusion_mode_key] in valid_exclusion_modes and exclusion[exclusion_scope_key] in valid_exclusion_scopes:
					# Normalise modes and scopes.
					if exclusion[exclusion_mode_key] == mode_e:
						exclusion[exclusion_mode_key] = mode_exclude
					elif exclusion[exclusion_mode_key] == mode_i:
						exclusion[exclusion_mode_key] = mode_include
					
					if exclusion[exclusion_scope_key] == scope_f:
						exclusion[exclusion_scope_key] = scope_filename
					elif exclusion[exclusion_scope_key] == scope_p:
						exclusion[exclusion_scope_key] = scope_filepath
					elif exclusion[exclusion_scope_key] == scope_u:
						exclusion[exclusion_scope_key] = scope_fullpath
					elif exclusion[exclusion_scope_key] == scope_c:
						exclusion[exclusion_scope_key] = scope_contents
					
					# Consider metadata-substitution flags, if present.
					valid_rule = True
					log_delim = "  "
					orig_rule = log_delim.join(exclusion.values())
					rule_rewritten = False
					for this_key in [search_key, path_key, comment_key]:
						should_rewrite = False
						this_value = exclusion[this_key] if this_key in exclusion else None
						
						if this_key == comment_key and rule_rewritten and comment_key in exclusion:
							# We already rewrote search and/or path, and we have a comment field. Rewrite it too.
							should_rewrite = True
							
						elif this_value:
							flag_match = pattern_has_flag(this_value, pattern_metadata_flag)
							if flag_match:
								should_rewrite = True
								inform(f"- Metadata pattern flag (?{pattern_metadata_flag}) detected. Processing:")
								# Remove the pattern_metadata_flag from this pattern.
								this_value = pattern_strip_flag(this_value, pattern_metadata_flag)
								rule_rewritten = True
						
						if should_rewrite and this_value:
							# Process token replacement.
							token_match = re.search(pattern_metadata_key_regex, this_value)
							while token_match:
								meta_key = token_match.group(1)
								if meta_key in json_contents:
									meta_val = json_contents[meta_key]
									this_value = this_value[:token_match.start()] + meta_val + this_value[token_match.end():]
								else:
									inform(f"Requested key '{meta_key}' not found in metadata. Ignoring this exclusion.", severity="warning")
									valid_rule = False
									break
								token_match = re.search(pattern_metadata_key_regex, this_value)
							if valid_rule:
								delim = "  "
								exclusion[this_key] = this_value
							else:
								# Break from loop over exclusions keys
								break
					
					if rule_rewritten:
						inform(f"- Rewrote rule metadata pattern:\n  {orig_rule}\n  as:\n  {log_delim.join(exclusion.values())}.")
					
					# Consider negation flag.
					for this_key in [search_key, path_key]:
						this_value = exclusion[this_key]
						flag_match = pattern_has_flag(this_value, pattern_negate_flag)
						if flag_match:
							inform(f"- Negation pattern flag (?{pattern_negate_flag}) detected in {this_key} pattern. Processing.")
							if negation_key not in exclusion:
								exclusion[negation_key] = []
							exclusion[negation_key].append(this_key)
							# Remove the pattern_negate_flag from this pattern.
							this_value = pattern_strip_flag(this_value, pattern_negate_flag)
							exclusion[this_key] = this_value

					if valid_rule:
						exclusions_map.append(exclusion)
					
		exclusions_file.close()
	except IOError as e:
		inform(f"Couldn't read exclusions file: {e}", severity="warning")

try:
	for file in files:
		text_file = open(file, 'r')
		text_contents = text_file.read()
		text_file.close()
		
		filename = os.path.basename(file)
		file_path = os.path.dirname(file)
		excluded = False
		if exclusions_map and len(exclusions_map) > 0:
			for excl in exclusions_map:
				# Heed path filter if specified.
				if excl[path_key] != path_any:
					filter_matched = re.search(excl[path_key], file_path)
					# Consider negation.
					if negation_key in excl and path_key in excl[negation_key]:
						filter_matched = not filter_matched
					if not filter_matched:
						# This file doesn't match this exclusion's path filter; skip to next exclusion.
						continue
				
				# Run regexp search.
				target_scope = filename
				target_desc = "filename"
				if excl[exclusion_scope_key] == scope_filepath:
					target_scope = file_path
					target_desc = "file path"
				elif excl[exclusion_scope_key] == scope_fullpath:
					target_scope = file
					target_desc = "entire path"
				elif excl[exclusion_scope_key] == scope_contents:
					target_scope = text_contents
					target_desc = "contents"
				
				found_match = re.search(excl[search_key], target_scope)
				# Consider negation.
				if negation_key in excl and search_key in excl[negation_key]:
					found_match = not found_match
				
				if (found_match and excl[exclusion_mode_key] == mode_exclude) or (not found_match and excl[exclusion_mode_key] == mode_include):
					excluded = True
					num_exclusions = num_exclusions + 1
					message = ""
					if comment_key in excl:
						message = f"{excl[comment_key]}"
					else:
						message = f"\"{excl[search_key]}\""
						if negation_key in excl and search_key in excl[negation_key]:
							message = f"{message} (negated)"
						if excl[path_key] != path_any:
							message = f"{message}, path filter \"{excl[path_key]}\""
							if negation_key in excl and path_key in excl[negation_key]:
								message = f"{message} (negated)"
					inform(f"- File excluded, as requested: {file} ({target_desc} {'matched' if found_match else 'did not match'} {'exclusion' if excl[exclusion_mode_key] == mode_exclude else 'inclusion'}: {message})")
					break
		
		if not excluded:
			master_documents.append(text_contents)
			included_file_paths.append(file)
		else:
			continue
		
		if check_tks:
			tks = re.findall(tk_pattern, text_contents)
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
elif verbose_mode:
	for f in included_file_paths:
		inform(f"- {f}")

if check_tks:
	num_tks = len(files_with_tks)
	if num_tks > 0:
		files_with_tks_string = '\n'.join(['- ' + f for f in files_with_tks])
		inform(f"TKs are present in the following files:\n{files_with_tks_string}", severity="warning", force=check_tks)
		if stop_on_tks:
			inform("TKs were found and you requested to stop on TKs. Not continuing.", severity="error")
			sys.exit(1)
		else:
			inform(f"(Continuing despite TKs.)", severity="warning", force=check_tks)
	else:
		inform(f"No TKs found.")

# Concatenate master file.
master_contents = "\n".join(master_documents)

# Process Figuremark.
if process_figuremark:
	figuremark_lib_path = os.path.join(os.path.dirname(this_script_path), "FigureMark/src/python/")
	sys.path.append(figuremark_lib_path)
	from figuremark import figuremark
	inform(f"FigureMark processing enabled.")
	master_contents = figuremark.convert(master_contents)

# Process transformations.
if run_transformations:
	# Check for any requested transformations.
	full_transformations_path = os.path.abspath(os.path.expanduser(transformations_path))
	
	inform(f"Checking for transformations file: {full_transformations_path}")
	if not os.path.isfile(full_transformations_path):
		inform(f"Transformations file not found. Continuing.")
	else:
		transformations = []
		try:
			# Read the transformations file.
			transformations_file = open(full_transformations_path, 'r')
			for line in transformations_file:		
				line = re.sub(r"\t+", "\t", line) # Collapse tab-runs
				components = line.strip('\n').split(tsv_delimiter)
				if len(components) > 1:
					transformation = {search_key: components[1]}
					if components[0] != "":
						transformation[comment_key] = components[0]
					if len(components) > 2:
						transformation[replace_key] = components[2]
					else:
						transformation[replace_key] = ""
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
	placeholder_delim = "%"
	# Replace all occurrences of metadata placeholders in master_contents.
	for key, value in json_contents.items():
		#print(f"{key}: {value} [{type(value)}]")
		master_contents = master_contents.replace(f"{placeholder_delim}{key}{placeholder_delim}", str(value))
	
	# Identify and warn about any remaining placeholders, i.e. for missing metadata keys.
	placeholder_pattern = rf"(?<!{placeholder_delim})\W{placeholder_delim}([^{placeholder_delim}]+?){placeholder_delim}\W"
	for placeholder_match in re.finditer(placeholder_pattern, master_contents):
		meta_key = placeholder_match.group(1)
		if meta_key not in json_contents:
			inform(f"Can't replace placeholder '{meta_key}', because it has no value in metadata. Ignoring.", severity="warning")

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

# Save master file with timestamp, or without if we're retaining it.
if retain_collated_master:
	master_filename = f"{master_basename}.md"
else:
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
	subtitle_key = "subtitle"
	if basename_key in json_contents and json_contents[basename_key] != "":
		output_basename = json_contents[basename_key]
		inform(f"Using basename specified in metadata: {output_basename}")
	else:
		# Slugify the 'title' entry as a filename, appending subtitle if present.
		if title_key in json_contents and json_contents[title_key] != "":
			title_val = json_contents[title_key]
			if subtitle_key in json_contents and json_contents[subtitle_key] != "":
				title_val = f"{title_val} - {json_contents[subtitle_key]}"
			output_basename = string_to_slug(title_val)
			inform(f"Converted metadata '{title_val}' to basename: {output_basename}")
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
				format_filename = f"{output_basename}.epub"
				curr_format = "epub"
				inform(f"Building {curr_format} format with pandoc...")
				yaml_epub_path = os.path.join(os.path.dirname(this_script_path), "options-epub.yaml")
				format_command = pandoc_pre_args + [f'--defaults={yaml_epub_path}', f'--output={format_filename}'] + pandoc_post_args
				if show_pandoc_commands:
					inform(f"Using pandoc command:\n{' '.join(format_command)}")
				p = subprocess.run(format_command)
				inform(f"Built {curr_format} format: {format_filename}")
				
			if this_format == "pdf" or all_formats:
				format_filename = f"{output_basename}.pdf"
				curr_format = "pdf"
				inform(f"Building {curr_format} format with pandoc...")
				yaml_pdf_path = os.path.join(os.path.dirname(this_script_path), "options-pdf.yaml")
				format_command = pandoc_pre_args + [f'--defaults={yaml_pdf_path}', f'--output={format_filename}'] + pandoc_post_args
				if show_pandoc_commands:
					inform(f"Using pandoc command:\n{' '.join(format_command)}")
				p = subprocess.run(format_command)
				inform(f"Built {curr_format} format: {format_filename}")
				
			if this_format == "pdf-6x9" or all_formats:
				format_filename = f"{output_basename}-6x9.pdf"
				curr_format = "pdf-6x9"
				inform(f"Building {curr_format} format with pandoc...")
				yaml_pdf_path = os.path.join(os.path.dirname(this_script_path), "options-pdf.yaml")
				css_pdf_6x9_path = os.path.join(os.path.dirname(this_script_path), "pdf-6x9.css")
				format_command = pandoc_pre_args + [f'--defaults={yaml_pdf_path}', f'--output={format_filename}', f'--css={css_pdf_6x9_path}'] + pandoc_post_args
				if show_pandoc_commands:
					inform(f"Using pandoc command:\n{' '.join(format_command)}")
				p = subprocess.run(format_command)
				inform(f"Built {curr_format} format: {format_filename}")
				
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
