import re


def convert(text):
	figure_block_pattern = r"(?mi)^(`{3,}|~{3,})\s*figuremark(\s+[^\{]+?)?\s*(?:\{([^\}]*?)\})?\s*$\n([\s\S\n]*?)\n\1\s*?$"
	figure_span_pattern = r"(?<!\\)\[(.+?)(?<!\\)\]\{([^\}]+?)\}|\{([\d.-]+)\}"
	shared_css_class = "figuremark"
	marks_map = {	"+": "insert",
								"-": "remove",
								"/": "comment",
								">": "result",
								"!": "highlight"}
	figure_number = 0
	figs_processed = 0
	
	# Find any FigureMark blocks needing rewritten.
	block_pattern_obj = re.compile(figure_block_pattern)
	span_pattern_obj = re.compile(figure_span_pattern)
	last_fig_end = 0
	
	block_match = block_pattern_obj.search(text, last_fig_end)
	while block_match:
		block_title = block_match.group(2).strip()
		block_attributes = block_match.group(3) 
		processed_block = block_match.group(4)
		
		# Process any embedded figure-marking spans.
		last_span_end = 0
		span_match = span_pattern_obj.search(processed_block, last_span_end)
		while span_match:
			processed_span = ""
			bracketed_text = span_match.group(1) if span_match.group(1) else ""
			if span_match.group(3):
				# Reference number without bracketed span.
				ref_num = span_match.group(3)
				processed_span = f'<span class="{shared_css_class} reference reference-{ref_num}">{ref_num}</span>'
				
			elif span_match.group(2) in marks_map:
				# Known directive span.
				css_class = marks_map[span_match.group(2)]
				processed_span = f'<span class="{shared_css_class} {css_class}">{bracketed_text}</span>'
				
			else:
				# Parse as an attribute list.
				span_attrs = parse_attributes(span_match.group(2))
				if not 'classes' in span_attrs:
					span_attrs['classes'] = []
				span_attrs['classes'].append(shared_css_class)	
				processed_span = f'<span{attributes_as_string(span_attrs)}>{bracketed_text}</span>'
			
			last_span_end = span_match.start() + len(processed_span)
			processed_block = processed_block[:span_match.start()] + processed_span + processed_block[span_match.end():]
			span_match = span_pattern_obj.search(processed_block, last_span_end)
		
		# Sync figure number with any intervening non-FigureMark figures.
		other_figures = re.findall(r"(?sm)<figure[^>]*>.+?</figure>", text[last_fig_end:block_match.start()])
		if other_figures:
			figure_number += len(other_figures)
		figure_number += 1
		
		# Assemble a suitable pre-formatted figure block.
		
		# Remove escaping backslashes from brackets and braces.
		processed_block = re.sub(r"(?<!\\)\\([\[\]\{\}\\])", r"\1", processed_block)
		processed_block = f"<div class=\"figure-content\">{processed_block}</div>"
		attrs = {}
		if block_attributes:
			attrs = parse_attributes(block_attributes)
		if not 'id' in attrs:
			attrs['id'] = f"figure-{figure_number}"
		if not 'pairs' in attrs:
			attrs['pairs'] = []
		attrs['pairs'].append(('data-fignum', f'{figure_number}'))
		
		fignum_format = f"Fig. {figure_number}"
		add_empty_caption = True
		caption_before = True
		link_caption = "num" # | title | all | none
		new_pairs = []
		
		# Process and strip any directives.
		for key, val in attrs['pairs']:
			if key.startswith(":"):
				if key.endswith("fig-num-format"):
					fignum_format = val.replace("#", str(figure_number))
				elif key.endswith("empty-captions"):
					add_empty_caption = (val == "true")
				elif key.endswith("caption-before"):
					caption_before = (val == "true")
				elif key.endswith("link-caption"):
					link_caption = val
			else:
				new_pairs.append((key, val))
		attrs['pairs'] = new_pairs
		
		figure_attrs_string = attributes_as_string(attrs)
		if block_title != "" or add_empty_caption:
			link_tag = f"<a href=\"#{attrs['id']}\">"
			caption_string = f"<figcaption><span class=\"figure-number\">{link_tag}{fignum_format}</a></span><span class=\"figure-title\">{block_title}</span></figcaption>"
			if link_caption == "title":
				caption_string = f"<figcaption><span class=\"figure-number\">{fignum_format}</span><span class=\"figure-title\">{link_tag}{block_title}</a></span></figcaption>"
			elif link_caption == "all":
				caption_string = f"<figcaption>{link_tag}<span class=\"figure-number\">{fignum_format}</span><span class=\"figure-title\">{block_title}</span></a></figcaption>"
			elif link_caption == "none":
				caption_string = f"<figcaption><span class=\"figure-number\">{fignum_format}</span><span class=\"figure-title\">{block_title}</span></figcaption>"
			
			if caption_before:
				processed_block = f"{caption_string}\n{processed_block}"
			else:
				processed_block = f"{processed_block}\n{caption_string}"
		processed_block = f"<figure{figure_attrs_string}>{processed_block}</figure>"
		last_fig_end = block_match.start() + len(processed_block)
		text = text[:block_match.start()] + processed_block + text[block_match.end():]
		figs_processed += 1
		block_match = block_pattern_obj.search(text, last_fig_end)
	
	if figs_processed > 0:
		print(f"Processed {figs_processed} FigureMark blocks.")
	else:
		print(f"No FigureMark blocks found.")
	
	return text


def parse_attributes(s):
	# Parse attribute string like '.class #id key=val'.

	id_attr = None
	classes = []
	pairs = []

	# Regex to match: .class, #id, or key=val (optionally quoted)
	pattern = re.compile(r'([.#][\w-]+|[\w:-]+=(?:"[^"]*"|\'[^\']*\'|[^\s]+))')
	for match in pattern.findall(s):
		item = match
		if item.startswith('.'):
			classes.append(item[1:])
		elif item.startswith('#'):
			id_attr = item[1:]
		else:
			key, _, val = item.partition('=')
			val = val or ""
			pairs.append((key, val.strip('"\'')))

	attrs = {}
	if id_attr:
		attrs['id'] = id_attr
	if classes:
		attrs['classes'] = classes
	if pairs:
		attrs['pairs'] = pairs
	return attrs


def attributes_as_string(attrs):
	attr_str = ""
	if 'id' in attrs:
		attr_str += f' id="{attrs["id"]}"'
	if 'classes' in attrs:
		attr_str += f' class="{" ".join(attrs["classes"])}"'
	if 'pairs' in attrs:
		for k, v in attrs['pairs']:
			attr_str += f' {k}="{v}"'
	return attr_str

