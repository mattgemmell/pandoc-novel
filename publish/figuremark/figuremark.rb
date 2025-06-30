# FigureMark, by Matt Gemmell ~ https://mattgemmell.scot/figuremark
# Jekyll plugin. Install: _plugins/figuremark.rb

# Set figuremark: true in a post/page's YAML front-matter to enable processing.
# You can also set figuremark: true in your site's _config.yml file to enable it globally.

class FMAttributes
  # Directives
  FIG_NUM_FORMAT = 'fig-num-format'
  EMPTY_CAPTIONS = 'empty-captions'
  CAPTION_BEFORE = 'caption-before'
  LINK_CAPTION = 'link-caption'
  RETAIN_BLOCK = 'retain-block'

  # Magic
  SHARED_CLASS = "figuremark"
  DIRECTIVE_PREFIX = ":"
  REMOVE_TOKEN = "-#{DIRECTIVE_PREFIX}"

  attr_accessor :tag_id, :classes, :tag_attrs, :directives

  def initialize(raw_string=nil)
    @tag_id = nil
    @classes = [SHARED_CLASS]
    @tag_attrs = {}
    @directives = {}

    if raw_string
      # Parse attribute string like '.class #id key=val'.
      pattern = /([.#][\w:-]+|[\w:-]+=(?:"[^"]*"|'[^']*'|[^\s]*)|[\w\-\.]+)/
      raw_string.scan(pattern).flatten.each do |item|
        if item.start_with?('.') && !@classes.include?(item[1..-1])
          @classes << item[1..-1]
        elsif item.start_with?('#')
          @tag_id = item[1..-1]
        elsif item.include? "="
          key, val = item.split('=', 2)
          val ||= ""
          dest = @tag_attrs
          this_key = key
          if key.start_with?(DIRECTIVE_PREFIX)
            dest = @directives
            this_key = this_key[DIRECTIVE_PREFIX.length..-1]
          end
          dest[this_key] = val.gsub(/\A['"]|['"]\z/, '')
        else
        	split_classes = item.split(".")
        	split_classes.each do |this_class|
        		if !@classes.include?(this_class)
        			@classes << this_class
        		end
        	end
        end
      end
    end
  end

  def to_s
    attr_str = ""
    attr_str += " id=\"#{@tag_id}\"" if @tag_id
    attr_str += " class=\"#{@classes.join(' ')}\"" if @classes.size > 0
    @tag_attrs.each { |k, v| attr_str += " #{k}=\"#{v}\"" }
    attr_str
  end

  def update(new_attrs)
    # OVERWRITE our own values if necessary, process removals
    if new_attrs.tag_id && new_attrs.tag_id.start_with?(REMOVE_TOKEN)
      if @tag_id == new_attrs.tag_id[REMOVE_TOKEN.length..-1] || new_attrs.tag_id == REMOVE_TOKEN
        @tag_id = nil
      end
    else
      @tag_id = new_attrs.tag_id if new_attrs.tag_id
    end

    new_attrs.classes.each do |new_class|
      if new_class == REMOVE_TOKEN
        @classes.clear
      elsif new_class.start_with?(REMOVE_TOKEN)
        @classes.delete(new_class[REMOVE_TOKEN.length..-1])
      elsif !@classes.include?(new_class)
        @classes << new_class
      end
    end

    new_attrs.tag_attrs.each do |k, v|
      if v == REMOVE_TOKEN
        @tag_attrs.delete(k)
      elsif k == REMOVE_TOKEN
        @tag_attrs.clear
      else
        @tag_attrs[k] = v
      end
    end

    new_attrs.directives.each do |k, v|
      if v == REMOVE_TOKEN
        @directives.delete(k)
      elsif k == REMOVE_TOKEN
        @directives.clear
      else
        @directives[k] = v
      end
    end
  end

  def incorporate(new_attrs)
    # Let OWN values take precedence, no removals
    @tag_id ||= new_attrs.tag_id
    new_attrs.classes.each { |cls| @classes << cls unless @classes.include?(cls) }
    @tag_attrs = new_attrs.tag_attrs.merge(@tag_attrs)
    @directives = new_attrs.directives.merge(@directives)
  end
end


Jekyll::Hooks.register [:documents, :pages], :pre_render do |doc|
  # Only process Markdown files.
  ext = doc.respond_to?(:extname) ? doc.extname : File.extname(doc.relative_path)
  next unless ext == '.md' || ext == '.markdown'
	
	proceed = true
	if doc.data.key?('figuremark')
		proceed = (doc.data['figuremark'] == true)
	else
		proceed = (doc.site.config['figuremark'] == true)
	end
	next unless proceed
	
	def convert(doc)
		text = doc.content
		
		fm_globals_pattern = /(?mi)^\{figure(?:mark)?\s*([^\}]*)\}\s*?$/
		figure_block_pattern = /(?mi)(?<!<!--\n)^(`{3,}|~{3,})\s*figure(?:mark)?(\s+[^\{]+?)?\s*(?:\{([^\}]*?)\})?\s*$\n([\s\S\n]*?)\n\1\s*?$/
		figure_span_pattern = /(?<!\\)\[(.+?)(?<!\\)\]\{([^\}]+?)\}|\{([\d.-]+)\}/
		marks_map = {
			"+" => "insert",
			"-" => "remove",
			"/" => "comment",
			">" => "result",
			"!" => "highlight"
		}
	
		figure_number = 0
		figs_processed = 0
		block_pattern_obj = Regexp.new(figure_block_pattern)
		span_pattern_obj = Regexp.new(figure_span_pattern)
		last_fig_end = 0
		global_attrs = FMAttributes.new
	
		# Find any FigureMark blocks needing rewritten.
		text_out = text.dup
		while (block_match = block_pattern_obj.match(text_out, last_fig_end))
			block_title = block_match[2] ? block_match[2].strip : ""
			block_attributes = block_match[3]
			processed_block = block_match[4]
	
			# Process any embedded figure-marking spans.
			last_span_end = 0
			while (span_match = span_pattern_obj.match(processed_block, last_span_end))
				processed_span = ""
				bracketed_text = span_match[1] || ""
				if span_match[3]
					# Reference number without bracketed span.
					ref_num = span_match[3]
					processed_span = "<span class=\"#{FMAttributes::SHARED_CLASS} reference reference-#{ref_num}\">#{ref_num}</span>"
				elsif marks_map.has_key?(span_match[2])
					# Known directive span.
					css_class = marks_map[span_match[2]]
					processed_span = "<span class=\"#{FMAttributes::SHARED_CLASS} #{css_class}\">#{bracketed_text}</span>"
				else
					# Parse as an attribute list.
					span_attrs = FMAttributes.new(span_match[2])
					processed_span = "<span#{span_attrs}>#{bracketed_text}</span>"
				end
				replace_start = span_match.begin(0)
				replace_end = span_match.end(0)
				processed_block = processed_block[0...replace_start] + processed_span + processed_block[replace_end..-1]
				last_span_end = replace_start + processed_span.length
			end
	
			# Sync figure number with any intervening non-FigureMark figures.
			between_text = text_out[last_fig_end...block_match.begin(0)]
			other_figures = between_text.to_enum(:scan, /(?m)<figure[^>]*>.+?<\/figure>/).map { Regexp.last_match }
			figure_number += other_figures.length if other_figures
			figure_number += 1
	
			# Remove escaping backslashes from brackets and braces.
			processed_block.gsub!(/(?<!\\)\\([\[\]\{\}\\])/, '\1')
			processed_block = "<div class=\"figure-content\">#{processed_block}</div>"
			attrs = FMAttributes.new(block_attributes)
			attrs.tag_id ||= "figure-#{figure_number}"
			attrs.tag_attrs['data-fignum'] = figure_number.to_s
	
			# Handle intervening globals blocks.
			pre_match_text = text_out[0...block_match.begin(0)]
			pre_match_orig_len = pre_match_text.length
			globals_matches = []
			pre_match_text.scan(fm_globals_pattern) do
				m = Regexp.last_match
				globals_matches << m
				global_attrs.update(FMAttributes.new(m[1]))
			end
	
			# Remove globals blocks in reverse, to preserve offsets as we go.
			globals_matches.reverse.each do |m|
				pre_match_text = pre_match_text[0...m.begin(0)] + pre_match_text[m.end(0)..-1]
			end
	
			# Account for changed offsets in block_match due to removal of globals blocks.
			pre_match_delta = pre_match_orig_len - pre_match_text.length
	
			# Incorporate global attributes, overriding with local values.
			attrs.incorporate(global_attrs)
	
			# Enact directives.
			fig_num_format = (attrs.directives[FMAttributes::FIG_NUM_FORMAT] || "Fig. #").gsub('#', figure_number.to_s)
			empty_captions = (attrs.directives[FMAttributes::EMPTY_CAPTIONS] || "true") == "true"
			caption_before = (attrs.directives[FMAttributes::CAPTION_BEFORE] || "true") == "true"
			link_caption = attrs.directives[FMAttributes::LINK_CAPTION] || "num"
			retain_block = attrs.directives[FMAttributes::RETAIN_BLOCK] || "none"
	
			if block_title != "" || empty_captions
				link_tag = "<a href=\"##{attrs.tag_id}\">"
				caption_string = "<figcaption><span class=\"figure-number\">#{link_tag}#{fig_num_format}</a></span><span class=\"figure-title\">#{block_title}</span></figcaption>"
				if link_caption == "title"
					caption_string = "<figcaption><span class=\"figure-number\">#{fig_num_format}</span><span class=\"figure-title\">#{link_tag}#{block_title}</a></span></figcaption>"
				elsif link_caption == "all"
					caption_string = "<figcaption>#{link_tag}<span class=\"figure-number\">#{fig_num_format}</span><span class=\"figure-title\">#{block_title}</span></a></figcaption>"
				elsif link_caption == "none"
					caption_string = "<figcaption><span class=\"figure-number\">#{fig_num_format}</span><span class=\"figure-title\">#{block_title}</span></figcaption>"
				end
	
				if caption_before
					processed_block = "#{caption_string}\n#{processed_block}"
				else
					processed_block = "#{processed_block}\n#{caption_string}"
				end
			end
	
			processed_block = "<figure#{attrs}>#{processed_block}</figure>"
	
			if retain_block == "comment"
				processed_block = "<!--\n#{block_match[0]}\n-->\n\n#{processed_block}"
			elsif retain_block == "indent"
				lines = block_match[0].lstrip.lines
				indented = lines.map { |l| "\t#{l}" }.join
				processed_block = "#{indented}\n\n#{processed_block}"
			end
	
			last_fig_end = block_match.begin(0) + processed_block.length - pre_match_delta
			text_out = pre_match_text + processed_block + text_out[block_match.end(0)..-1]
			figs_processed += 1
		end
	
		if figs_processed > 0
			puts "Processed #{figs_processed} FigureMark blocks in \"#{doc.data['title']}\" (#{doc.path})."
		else
			#puts "No FigureMark blocks found in \"#{doc.data['title']}\" (#{doc.path})."
		end
		
		text_out
	end
	
	doc.content = convert(doc)
end
