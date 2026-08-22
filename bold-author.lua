-- bold-author.lua
-- Bolds "Hilton, L.K." wherever it appears in bibliography entries.
-- Matches the Elsevier Harvard CSL format: "Lastname, I.I."
-- The last-name-first pattern avoids bolding the title ("Laura K. Hilton, PhD").

local pandoc = require 'pandoc'

function Inlines(inlines)
  -- Quick exit: skip if "Hilton" is not present
  local found = false
  for _, el in ipairs(inlines) do
    if el.t == 'Str' and el.text:match('%*?Hilton') then
      found = true
      break
    end
  end
  if not found then return inlines end

  local result = pandoc.List{}
  local i = 1

  while i <= #inlines do
    local el = inlines[i]

    -- Match "Hilton," or "*Hilton," (asterisk prefix = co-first authorship)
    if el.t == 'Str' and el.text:match('^%*?Hilton,?$') then
      local name_parts = pandoc.List{el}
      local j = i + 1

      -- Peek: Space then initials like "L.K." or "L.K.,"
      if j <= #inlines and inlines[j].t == 'Space' then
        local k = j + 1
        if k <= #inlines and inlines[k].t == 'Str'
           and inlines[k].text:match('^[A-Z]%.') then
          name_parts:insert(inlines[j])  -- Space
          local init_text = inlines[k].text
          -- If initials end with comma (author separator), keep comma outside bold
          if init_text:match(',$') then
            name_parts:insert(pandoc.Str(init_text:sub(1, -2)))
            result:insert(pandoc.Strong(name_parts))
            result:insert(pandoc.Str(','))
          else
            name_parts:insert(inlines[k])
            result:insert(pandoc.Strong(name_parts))
          end
          i = k + 1
        else
          result:insert(pandoc.Strong(name_parts))
          i = j
        end
      else
        result:insert(pandoc.Strong(name_parts))
        i = j
      end
    else
      result:insert(el)
      i = i + 1
    end
  end

  return result
end
