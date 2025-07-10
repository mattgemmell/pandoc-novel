function string.starts(String,Start)
	return string.sub(String,1,string.len(Start))==Start
end

---Parse raw HTML A-tag links into Link AST elements. Modifies Inlines in place.
---@param inlines			  Inlines
local function parse_links(inlines)
	-- Based on https://github.com/rnwst/pandoc-discussions/blob/master/10840/filter.lua
	-- Go back to front to avoid problems with changing indices.
	for i = #inlines, 1, -1 do
		if inlines[i].tag == 'RawInline' and string.starts(inlines[i].text, '<a ') then
			local a_start, a_end, delim, href = string.find(inlines[i].text, '<a%s+[^>]*href=(["\'])([^%1]+)%1[^>]->')
			if a_start then
				for j = i + 1, #inlines, 1 do
					if inlines[j].tag == 'RawInline' and inlines[j].text == '</a>' then
						inlines[i] = pandoc.Link( { table.unpack(inlines, i + 1, j - 1)}, href)
						for _ = i + 1, j, 1 do
							inlines:remove(i + 1)
						end
						break
					end
				end
			end
		end
	end
end

---@param inlines Inlines
---@return Inlines | nil
function Inlines(inlines)
	parse_links(inlines)
	return inlines
end
