# _plugins/figuremark.rb

require 'rexml/document'

Jekyll::Hooks.register [:documents, :pages], :pre_render do |doc|
  # Only process Markdown files.
  ext = doc.respond_to?(:extname) ? doc.extname : File.extname(doc.relative_path)
  next unless ext == '.md' || ext == '.markdown'
	
	# Set figuremark: true in a post/page's YAML front-matter to enable processing.
	# You can also set figuremark: true in your site's _config.yml file to enable it globally.
	proceed = true
	if doc.data.key?('figuremark')
		proceed = (doc.data['figuremark'] == true)
	else
		proceed = (doc.site.config['figuremark'] == true)
	end
	next unless proceed
	
  def convert(doc)
		figure_block_pattern = /(?<!<!--\n)^(`{3,}|~{3,})\s*figuremark(\s+[^\{]+?)?\s*(?:\{([^\}]*?)\})?\s*$\n([\s\S\n]*?)\n\1\s*?$/mi
		figure_span_pattern = /(?<!\\)\[(.+?)(?<!\\)\]\{([^\}]+?)\}|\{([\d.-]+)\}/
		shared_css_class = "figuremark"
		marks_map = {
			"+" => "insert",
			"-" => "remove",
			"/" => "comment",
			">" => "result",
			"!" => "highlight"
		}
		figure_number = 0
		figs_processed = 0
	
		last_fig_end = 0
		
		text = doc.content
		
		while match = text.match(figure_block_pattern, last_fig_end)
			block_title = match[2].strip
			block_attributes = match[3]
			processed_block = match[4]
	
			# Process any embedded figure-marking spans.
			last_span_end = 0
			loop do
				span_match = processed_block.match(figure_span_pattern, last_span_end)
				break unless span_match
	
				processed_span = ""
				bracketed_text = span_match[1] ? span_match[1] : ""
				if span_match[3]
					# Reference number without bracketed span.
					ref_num = span_match[3]
					processed_span = %Q{<span class="#{shared_css_class} reference reference-#{ref_num}">#{ref_num}</span>}
				elsif span_match[2] && marks_map[span_match[2]]
					# Known directive span.
					css_class = marks_map[span_match[2]]
					processed_span = %Q{<span class="#{shared_css_class} #{css_class}">#{bracketed_text}</span>}
				else
					# Parse as an attribute list.
					span_attrs = parse_attributes(span_match[2])
					span_attrs['classes'] ||= []
					span_attrs['classes'] << shared_css_class
					processed_span = %Q{<span#{attributes_as_string(span_attrs)}>#{bracketed_text}</span>}
				end
				# Replace the span in processed_block
				processed_block = processed_block[0...span_match.begin(0)] + processed_span + processed_block[span_match.end(0)..-1]
				last_span_end = span_match.begin(0) + processed_span.length
			end
	
			# Sync figure number with any intervening non-FigureMark figures.
			block_prefix = text[last_fig_end...match.begin(0)]
			other_figures = block_prefix ? block_prefix.scan(/<figure[^>]*>.+?<\/figure>/m) : []
			figure_number += other_figures.length
			figure_number += 1
	
			# Assemble a suitable pre-formatted figure block.
			
			# Remove escaping backslashes from brackets and braces.
			processed_block = processed_block.gsub(/(?<!\\)\\([\[\]\{\}\\])/, '\1')
			processed_block = %Q{<div class="figure-content">#{processed_block}</div>}
			attrs = {}
			if block_attributes
				attrs = parse_attributes(block_attributes)
			end
			attrs['id'] ||= "figure-#{figure_number}"
			attrs['pairs'] ||= []
			attrs['pairs'] << ['data-fignum', "#{figure_number}"]
			
			fignum_format = "Fig. #{figure_number}"
			add_empty_caption = true
			caption_before = true
			link_caption = "num" # | title | all | none
			retain_block = "none" # | comment | indent
			new_pairs = []
			
			# Process and strip any directives.
			attrs['pairs'].each do |key, val|
				if key.start_with?(":")
					if key.end_with?("fig-num-format")
						fignum_format = val.gsub("#", figure_number.to_s)
					elsif key.end_with?("empty-captions")
						add_empty_caption = (val == "true")
					elsif key.end_with?("caption-before")
						caption_before = (val == "true")
					elsif key.end_with?("link-caption")
						link_caption = val
					elsif key.end_with?("retain-block")
						retain_block = val
					end
				else
					new_pairs << [key, val]
				end
			end
			attrs['pairs'] = new_pairs
			
			figure_attrs_string = attributes_as_string(attrs)
			if block_title != "" || add_empty_caption
				link_tag = %Q{<a href="##{attrs['id']}">}
				caption_string = %Q{<figcaption><span class="figure-number">#{link_tag}#{fignum_format}</a></span><span class=\"figure-title\">#{block_title}</span></figcaption>}
				if link_caption == "title"
					caption_string = %Q{<figcaption><span class="figure-number">#{fignum_format}</span><span class=\"figure-title\">#{link_tag}#{block_title}</a></span></figcaption>}
				elsif link_caption == "all"
					caption_string = %Q{<figcaption>#{link_tag}<span class="figure-number">#{fignum_format}</span><span class=\"figure-title\">#{block_title}</span></a></figcaption>}
				elsif link_caption == "none"
					caption_string = %Q{<figcaption><span class="figure-number">#{fignum_format}</span><span class=\"figure-title\">#{block_title}</span></figcaption>}
				end
				
				if caption_before
					processed_block = %Q{#{caption_string}\n#{processed_block}}
				else
					processed_block = %Q{#{processed_block}\n#{caption_string}}
				end
			end
			
			processed_block = %Q{<figure#{figure_attrs_string}>#{processed_block}</figure>}
			
			if retain_block == "comment"
				processed_block = %Q{<!--\n#{match[0]}\n-->\n\n#{processed_block}}
			elsif retain_block == "indent"
				lines = match[0].split(/\n/)
				lines.each do |line|
					line = %Q{\t#{line}}
				end
				indented = lines.join("\n")
				processed_block = %Q{#{indented}\n\n#{processed_block}}
			end
			
			last_fig_end = match.begin(0) + processed_block.length
			text = text[0...match.begin(0)] + processed_block + text[match.end(0)..-1]
			figs_processed += 1
		end
	
		if figs_processed > 0
			puts "Processed #{figs_processed} FigureMark blocks in \"#{doc.data['title']}\" (#{doc.path})."
		else
			#puts "No FigureMark blocks found in #{doc.data['title']}."
		end
		
		text
	end
	
	def parse_attributes(s)
		# Parse attribute string like '.class #id key=val'.
		id_attr = nil
		classes = []
		pairs = []
	
		# Regex to match: .class, #id, or key=val (optionally quoted)
		pattern = /([.#][\w-]+|[\w:-]+=(?:"[^"]*"|'[^']*'|[^\s]+))/
		s.scan(pattern) do |match_arr|
			item = match_arr[0]
			if item.start_with?('.')
				classes << item[1..-1]
			elsif item.start_with?('#')
				id_attr = item[1..-1]
			else
				key, _, val = item.partition('=')
				val = "" if val.nil?
				pairs << [key, val.gsub(/\A['"]|['"]\z/, '')]
			end
		end
	
		attrs = {}
		attrs['id'] = id_attr if id_attr
		attrs['classes'] = classes unless classes.empty?
		attrs['pairs'] = pairs unless pairs.empty?
		attrs
	end
	
	def attributes_as_string(attrs)
		attr_str = ""
		attr_str += %Q{ id="#{attrs['id']}"} if attrs['id']
		if attrs['classes']
			attr_str += %Q{ class="#{attrs['classes'].join(' ')}"}
		end
		if attrs['pairs']
			attrs['pairs'].each do |k, v|
				attr_str += %Q{ #{k}="#{v}"}
			end
		end
		attr_str
	end
	
	doc.content = convert(doc)
end
