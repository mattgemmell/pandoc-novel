import sys
import os
from figuremark import figuremark

filename = "figuremark-docs.md"
if len(sys.argv) > 1:
	filename = sys.argv[1]

try:
	input_file = open(filename, 'r')
	file_contents = input_file.read()
	input_file.close()
	
	file_contents = figuremark.convert(file_contents)
	
	basename, sep, ext = filename.partition(".")
	output_file = open(f"{basename}-converted{sep}{ext}", 'w')
	output_file.write(file_contents)
	output_file.close()
 
except IOError as e:
	print(f"Error: {e}")
	sys.exit(1)
