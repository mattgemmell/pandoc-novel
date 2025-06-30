
# FigureMark, by Matt Gemmell ~ https://mattgemmell.scot/figuremark


import re


class FMAttributes:
	# Directives
	fig_num_format = f"fig-num-format"
	empty_captions = f"empty-captions"
	caption_before = f"caption-before"
	link_caption = f"link-caption"
	retain_block = f"retain-block"
	
	# Magic
	shared_class = "figuremark"
	directive_prefix = ":"
	remove_token = f"-{directive_prefix}"
	
	def __init__(self, raw_string=None):
		self.tag_id = None
		self.classes = [FMAttributes.shared_class]
		self.tag_attrs = {}
		self.directives = {}
		
		if raw_string:
			# Parse attribute string like '.class #id key=val'.
			pattern = re.compile(r'([.#][\w:-]+|[\w:-]+=(?:"[^"]*"|\'[^\']*\'|[^\s]*)|[\w\-\.]+)')
			for match in pattern.findall(raw_string):
				item = match
				if item.startswith('.') and not item[1:] in self.classes:
					self.classes.append(item[1:])
				elif item.startswith('#'):
					self.tag_id = item[1:]
				elif "=" in item:
					key, _, val = item.partition('=')
					val = val or ""
					dest = self.tag_attrs
					this_key = key
					if key.startswith(FMAttributes.directive_prefix):
						dest = self.directives
						# Trim off the directive_prefix.
						this_key = this_key[len(FMAttributes.directive_prefix):]
					dest[this_key] = val.strip('"\'')
				else:
					split_classes = item.split(".")
					for this_class in split_classes:
						if not this_class in self.classes:
							self.classes.append(this_class)
	
	def __str__(self):
		attr_str = ""
		if self.tag_id:
			attr_str += f' id="{self.tag_id}"'
		if len(self.classes) > 0:
			attr_str += f' class="{" ".join(self.classes)}"'
		for k, v in self.tag_attrs.items():
			attr_str += f' {k}="{v}"'
		return attr_str
	
	def update(self, new_attrs):
		# Update self with values from new_attrs, OVERWRITING our own values if necessary.
		# This method also appropriately processes removals with the remove_token.
		
		if new_attrs.tag_id and new_attrs.tag_id.startswith(FMAttributes.remove_token):
			if self.tag_id == new_attrs.tag_id[len(FMAttributes.remove_token):] or new_attrs.tag_id == FMAttributes.remove_token:
				self.tag_id = None
		else:
			self.tag_id = new_attrs.tag_id
		
		for new_class in new_attrs.classes:
			if new_class == FMAttributes.remove_token:
				self.classes.clear()
			elif new_class.startswith(FMAttributes.remove_token):
				if new_class[len(FMAttributes.remove_token):] in self.classes:
					self.classes.remove(new_class[len(FMAttributes.remove_token):])
			elif not new_class in self.classes:
				self.classes.append(new_class)
		
		for k, v in new_attrs.tag_attrs.items():
			if v == FMAttributes.remove_token:
				if k in self.tag_attrs:
					del self.tag_attrs[k]
			elif k == FMAttributes.remove_token:
				self.tag_attrs.clear()
			else:
				self.tag_attrs[k] = v
		
		for k, v in new_attrs.directives.items():
			if v == FMAttributes.remove_token:
				if k in self.directives:
					del self.directives[k]
			elif k == FMAttributes.remove_token:
				self.directives.clear()
			else:
				self.directives[k] = v
	
	def incorporate(self, new_attrs):
		# Update self with values from new_attrs, letting our OWN values take precedence.
		# This method does NOT process removals.
		
		if not self.tag_id:
			self.tag_id = new_attrs.tag_id
		
		for new_class in new_attrs.classes:
			if not new_class in self.classes:
				self.classes.append(new_class)
		
		temp = dict(new_attrs.tag_attrs)
		temp.update(self.tag_attrs)
		self.tag_attrs = temp
		
		temp = dict(new_attrs.directives)
		temp.update(self.directives)
		self.directives = temp


def convert(text):
	fm_globals_pattern = r"(?mi)^(?:\{figure(?:mark)?\s*([^\}]*)\})\s*?$"
	figure_block_pattern = r"(?mi)(?<!<!--\n)^(`{3,}|~{3,})\s*figure(?:mark)?(\s+[^\{]+?)?\s*(?:\{([^\}]*?)\})?\s*$\n([\s\S\n]*?)\n\1\s*?$"
	figure_span_pattern = r"(?<!\\)\[(.+?)(?<!\\)\]\{([^\}]+?)\}|\{([\d.-]+)\}"
	marks_map = {	"+": "insert",
								"-": "remove",
								"/": "comment",
								">": "result",
								"!": "highlight"}
	figure_number = 0
	figs_processed = 0
	block_pattern_obj = re.compile(figure_block_pattern)
	span_pattern_obj = re.compile(figure_span_pattern)
	last_fig_end = 0
	global_attrs = FMAttributes()
	
	# Find any FigureMark blocks needing rewritten.
	block_match = block_pattern_obj.search(text, last_fig_end)
	while block_match:
		block_title = block_match.group(2)
		if block_title:
			block_title = block_title.strip()
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
				processed_span = f'<span class="{FMAttributes.shared_class} reference reference-{ref_num}">{ref_num}</span>'
				
			elif span_match.group(2) in marks_map:
				# Known directive span.
				css_class = marks_map[span_match.group(2)]
				processed_span = f'<span class="{FMAttributes.shared_class} {css_class}">{bracketed_text}</span>'
				
			else:
				# Parse as an attribute list.
				span_attrs = FMAttributes(span_match.group(2))
				processed_span = f'<span{span_attrs}>{bracketed_text}</span>'
			
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
		attrs = FMAttributes(block_attributes)
		if not attrs.tag_id:
			attrs.tag_id = f"figure-{figure_number}"
		attrs.tag_attrs['data-fignum'] = f'{figure_number}'
		
		# Handle intervening globals blocks.
		pre_match_text = text[:block_match.start()]
		pre_match_orig_len = len(pre_match_text)
		globals_matches = []
		
		# Update global_attrs with each set of found globals, in order.
		for globals_match in re.finditer(fm_globals_pattern, pre_match_text):
			globals_matches.append(globals_match)
			global_attrs.update(FMAttributes(globals_match.group(1)))
				
		# Remove globals blocks in reverse, to preserve offsets as we go.
		for globals_match in reversed(globals_matches):
			pre_match_text = pre_match_text[:globals_match.start()] + pre_match_text[globals_match.end():]
		
		# Account for changed offsets in block_match due to removal of globals blocks.
		pre_match_delta = pre_match_orig_len - len(pre_match_text)
		
		# Incorporate global attributes, overriding with local values.
		attrs.incorporate(global_attrs)
		
		# Enact directives.
		fig_num_format = attrs.directives.get(FMAttributes.fig_num_format, "Fig. #").replace("#", str(figure_number))
		empty_captions = (attrs.directives.get(FMAttributes.empty_captions, "true") == "true")
		caption_before = (attrs.directives.get(FMAttributes.caption_before, "true") == "true")
		link_caption = attrs.directives.get(FMAttributes.link_caption, "num") # | title | all | none
		retain_block = attrs.directives.get(FMAttributes.retain_block, "none") # | comment | indent
		
		if block_title != "" or empty_captions:
			link_tag = f"<a href=\"#{attrs.tag_id}\">"
			caption_string = f"<figcaption><span class=\"figure-number\">{link_tag}{fig_num_format}</a></span><span class=\"figure-title\">{block_title}</span></figcaption>"
			if link_caption == "title":
				caption_string = f"<figcaption><span class=\"figure-number\">{fig_num_format}</span><span class=\"figure-title\">{link_tag}{block_title}</a></span></figcaption>"
			elif link_caption == "all":
				caption_string = f"<figcaption>{link_tag}<span class=\"figure-number\">{fig_num_format}</span><span class=\"figure-title\">{block_title}</span></a></figcaption>"
			elif link_caption == "none":
				caption_string = f"<figcaption><span class=\"figure-number\">{fig_num_format}</span><span class=\"figure-title\">{block_title}</span></figcaption>"
			
			if caption_before:
				processed_block = f"{caption_string}\n{processed_block}"
			else:
				processed_block = f"{processed_block}\n{caption_string}"
				
		processed_block = f"<figure{attrs}>{processed_block}</figure>"
		
		if retain_block == "comment":
			processed_block = f"<!--\n{block_match[0]}\n-->\n\n{processed_block}"
		elif retain_block == "indent":
			processed_block = f"{'\t'.join(('\t'+block_match[0].lstrip()).splitlines(True))}\n\n{processed_block}"
		
		last_fig_end = block_match.start() + len(processed_block) - pre_match_delta
		text = pre_match_text + processed_block + text[block_match.end():]
		figs_processed += 1
		block_match = block_pattern_obj.search(text, last_fig_end)
	
	if figs_processed > 0:
		print(f"Processed {figs_processed} FigureMark blocks.")
	else:
		print(f"No FigureMark blocks found.")
	
	return text
