from figuremark import figuremark

try:
	input_file = open("figuremark-example.md", 'r')
	file_contents = input_file.read()
	input_file.close()
	
	file_contents = figuremark.convert(file_contents)
	
	output_file = open("figuremark-converted.md", 'w')
	output_file.write(file_contents)
	output_file.close()
 
except IOError as e:
	print(f"Problem: {e}")
	sys.exit(1)
