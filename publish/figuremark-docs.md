# FigureMark

This is the documentation for **FigureMark**, a simple syntax for marking up _figures_ in Markdown documents (i.e. HTML `<figure>` blocks). Its purpose is to help with formatting explanatory content online and in digital and printed books. It was created by [Matt Gemmell](https://mattgemmell.scot).

```figuremark Hamlet — Act 3, Scene 1 {.poetry :caption-before=false #act3-scene1 :link-caption=title}
[To be, or not to be]{!}, that is the question: {1}
Whether 'tis nobler in the mind to suffer
The slings and arrows of [outrageous]{+} fortune,
Or to take arms against a sea of troubles
And by opposing {2} end them. […]{/}
```

Feature requests, bug reports, and general discussion are welcomed; you can [find my contact details here](https://mattgemmell.scot/contact/).

---

## Purpose

While working on my [pandoc-based Markdown publishing system](https://github.com/mattgemmell/pandoc-publish), it seemed to me that when writing non-fiction content, there was no accessible way to mark-up content for the purpose of explanation, examination, and education. It's often necessary to show something technical or detailed, and to annotate such material with clarifying or didactic decorations.

Syntax-highlighting systems are ubiquitous, but they apply only to code listings and certain related textual data, and they use the _mechanics_ of the language, rather than _explaining_ or _focusing_ on the content. Manual tagging with HTML and CSS is of course possible, but is tedious and lacks automation.

My aim was to provide an 80% solution, allowing the annotation of a document's figures in a semantic shorthand which is easily parsed and extended, with some functional conveniences included. The result is FigureMark.

FigureMark is intended to be useful in the creation of non-fiction works, particularly those on technical matters, such as learning a programming language, discussing complex concepts which benefit from detailed examples, and so on. Its focus is on simplicity, and meeting a set of common needs without complexity, at the expense of comprehensiveness.

Note in particular that while FigureMark is very useful for annotating code samples, it is equally intended for use in textual analysis of prose and poetry, discussing quotations, illustrating concepts, and much more. Its semantics are intentionally loose and extensible, and the user is encouraged to adapt it to their needs.

---

## Implementations

FigureMark is a very simple markup format, and implementation of a parser should be straightforward in any language supporting regular expressions.

#### Python script

There is a [Python implementation here](https://github.com/mattgemmell/pandoc-publish/blob/main/publish/figuremark/figuremark.py), and also a simple [wrapper script](https://github.com/mattgemmell/pandoc-publish/blob/main/publish/figuremark-demo.py) showing its use.

#### Jekyll plugin (Ruby)

There is a [Jekyll plugin implementation here](https://github.com/mattgemmell/pandoc-publish/blob/main/publish/figuremark/figuremark.rb).

Find out [about Jekyll](https://jekyllrb.com). Install the plugin in your site's `_plugins` folder. To use it, set `figuremark: true` in a post/page's YAML front-matter to enable processing. You can also set `figuremark: true` in your site's `_config.yml` file to enable it globally.

All of these are licensed under the [GPL-3.0 license](https://www.gnu.org/licenses/gpl-3.0.en.html).

If you create an implementation in another language or format, let me know so I can link to it.

---

## Syntax

FigureMark is extremely simple in syntax and functionality, easy to understand, and hopefully not too burdensome to use. Let's begin with an example.

Here's the source of a given figure, using the FigureMark syntax:

~~~figuremark FigureMark Syntax {.example #syntax}
[```figuremark]{!} Demo of FigureMark [{.example #demo}]{!}
normal text
[\[]{!}inserted text[\]{+}]{!}
[\[]{!}removed text[\]{-}]{!} [\[]{!}comment[\]{/}]{!}
text with a reference [{1}]{!}
[\[]{!}result of something[\]{>}]{!}
text with reference [{2.1}]{!} and a [\[]{!}highlight[\]{!}]{!}
[```]{!}
~~~

Here's the result after processing, and with [some example CSS](https://mattgemmell.scot/css/figuremark.css) suited to code samples:

```figuremark Demo of FigureMark {.example #demo}
normal text
[inserted text]{+}
[removed text]{-} [comment]{/}
text with a reference {1}
[result of something]{>}
text with reference {2.1} and a [highlight]{!}
```

Alternate styles can readily be used to display other types of content besides code samples:

```figuremark Stephen King {.quotation :fig-num-format="Figure #" :caption-before=false}
A [short story]{!} is a different thing altogether — like a [quick kiss in the dark]{+} from a stranger.
```

---

## Documentation

There are several notable features of the FigureMark syntax and parser, as described below.

### Figure blocks

Figures begin and end with lines which start with at least 3 `` ` `` (backtick) symbols followed by `figuremark` (or just `figure`). You can use `~` tildes instead of backticks if you wish. The closing line should have no other content. The opening line may also have, in order:

1. A title, which if provided will become the figure's caption.
2. An _attributes list_, inside `{braces}`. This can contain any number and combination of:
	- An `#id` for the figure tag, e.g. `#chp1-example1`
	- CSS `.classes` for the figure tag, e.g. `.example`
	- `Key=value` pairs for the figure tag, e.g. `data-foo="baz"`
	- **Directives**, which are `:key=value` pairs whose key is prefixed with a `:` colon. [See below](#directives).

The title and attributes list may have whitespace between or around them. Key-value pairs may have the values in single-quotes, double-quotes, or neither, but all values will be double-quoted in the resulting HTML.

The figure's caption will automatically gain a `figure-number` span containing `Fig. 1` or such (the format can be overridden via a directive; see below), which can easily be hidden or moved via CSS. The figure's number is automatically calculated on a global basis, and takes into account both FigureMark figures and _also_ any pre-existing HTML `<figure>` blocks. If a title was specified for the figure, it will be within a `figure-title` span inside the caption.

Figures can be [linked to](#demo) via their `id` attribute, which will be of the form `figure-1` unless overridden in the attributes block as described above. If multiple IDs are specified in the attributes block, only the final one will be used. The `figure-number` span within the caption, mentioned above, will be linked to the figure itself.

The resulting figure tag will also automatically gain a `data-fignum` attribute, containing the figure number. The figure's entire content, _excluding_ any caption, will be inside a `div` with the `figure-content` class applied.

#### Directives

Special keys called _directives_, with corresponding values, can be specified in the attributes list. These directives will _not_ be transferred to the resulting HTML figure tag as conventional attributes, but will instead alter some aspect of its processing or generation. Currently supported directives are below.

- `:fig-num-format="Figure #"` will change the format of the `figure-number` span within the figure's caption. Any `#` symbols will each be replaced with the figure number. This is useful for localisation into human languages for which the default `Fig. 1` (etc.) is not suitable.

- `:empty-captions=false` will change the figure's caption behaviour with regard to titles. By default, even if no title is specified for the figure block, a `<figcaption>` will still be generated, containing a span with the figure number (formatted according to the `:fig-num-format` directive above). If you instead wish to _omit_ the caption entirely when no title is specified, set this directive to `false`.

- `:caption-before=false` will move the figure's caption to _after_ the content, instead of the default position before the content.

- `:link-caption=num` controls which parts of the caption, if any, are hyperlinked to the figure itself. `num` is the default, making the figure number into a link. The other options are `title`, `all`, or `none`.

- `:retain-block=none` controls whether the original FigureMark block will be kept when its processed version is inserted into the document. The default value, `none`, replaces the block with its processed version. Other accepted values are `indent`, which indents the original FigureMark block by one tab and then inserts the processed version after it (which in Markdown will usually result in the tab-indented segment becoming a `<code>` block); and `comment`, which places the original FigureMark block into an HTML comment and then inserts the processed version after it.  
  
  Note that to protect against unwanted duplication when using `comment` mode and re-processing an already-processed document, FigureMark blocks which are immediately preceded by an opening HTML comment (`<!--`) on the previous line will never be processed. Likewise, FigureMark blocks whose opening (backticked or tilded) lines are indented to any degree will not be processed.

Any other (unrecognised) directives will be removed.

#### Global attributes

It can be useful to set document-wide default values of figure block attributes, so that all subsequent FigureMark blocks will use those attributes unless they specify their own overrides. This can be achieved with a _FigureMark globals block_. Here's an example:

	{figuremark :caption-before=false :fig-num-format="Figure #." .poetry}

A globals block should occur on a line of its own, without any leading whitespace, and consists of an opening brace immediately followed by `figuremark` (or just `figure`), then the usual space-delimited [string of attributes](#figure-blocks) followed by a closing brace. More than one globals block can be provided, and they will be processed in order, with the specified attributes being applied to all FigureMark figure blocks which occur later in the document.

Globals blocks can include `:directives`, CSS `.classes`, `key=value` pairs, and even CSS `#ids` (even though it doesn't make much sense to globally apply the same ID to multiple elements). Some advanced functionality is available:

1. Globals blocks and figure blocks are processed in strict order of appearance in the document, meaning that (for example) you can _redefine_ globals part-way through the document, allowing them to affect only the figures in certain sections. A concrete application of this feature would be to define certain global attributes for FigureMark blocks in a book's front-matter, and then define a different set of globals for the manuscript portion.

2. Each type of global attribute can also be _deleted_, either individually or as a group, by using the special _remove token_ (`-:`) in a globals block. It works as follows:  
  
  - `#-:foo` will cause the global ID `foo` to be deleted (if set). `#-:` will delete _any_ globally-set ID.
  - `.-:foo` will cause the global CSS class `foo` to be deleted (if set). `.-:` will delete _all_ globally-set CSS classes.
  - `foo=-:` will cause the global key=value pair for the key `foo` to be deleted (if set). `-:=` will delete _all_ globally-set key=value pairs.
  - `:link-caption=-:` will cause the global directive `:link-caption` to be deleted (if set). `:-:=` will delete _all_ globally-set directives.

This can be judiciously used to achieve the toggling on or off of certain sets of global attributes according to the flow of the document.

### Escaping

Since the FigureMark marking syntax (described below) makes use of square brackets and curly braces, it may be necessary to escape those characters in the figure's content, if you do not wish them to be interpreted as marks.

This can be achieved by prefixing any literal brackets and braces with a backslash (like this: `\[`). Any such backslashes will be removed when the block is processed. If you wish to have a literal backslash before a bracket or brace, use two backslashes instead of one; only one will remain after processing.

Escaping these characters is especially important when [annotating FigureMark syntax examples](#inception) using FigureMark.

### Mark types

There are 7 types of marks available to decorate content, reflecting commonly-needed kinds of annotations when illustrating material for discursive or educational purposes. They are split into three groups, detailed below.

All marks are transformed into `<span>` tags, each with their own classes as described. Additionally, every mark will have the `figuremark` class. The exact rendering of the marks is of course determined by the CSS applied to the document.

#### 1. Reference marks

Reference marks are simply numerical call-outs, inserted on their own so that the text can refer to them. The syntax is `{1}` for example, with full-stops/periods/dots and dashes/hyphens also permitted. The resulting spans will have the `reference` class, and _also_ a class of the form `reference-1` etc.

References are the only standalone mark, with all of the remaining marks spanning some content.

#### 2. Short marks

Short marks are single-character marks, which decorate the spanned section of content within a line. There are five predefined short marks, as detailed below, with their syntax all following the same form: `[content to annotate]{type}`. Any occurrences of square brackets or curly braces within the bracketed content can be escaped with backslashes.

The defined types are:

- `+` mapped to the CSS class `insert`. Intended for added, inserted, or approved content.
- `-` mapped to the CSS class `remove`. Intended for removed, replaced, or disapproved content.
- `!` mapped to the CSS class `highlight`. Intended to draw attention to content.
- `>` mapped to the CSS class `result`. Intended to show a result or outcome, for example of code execution.
- `/` mapped to the CSS class `comment`. Intended for remarks or other asides, including source code comments.

Styling of these is up to your CSS, using the mapped classes mentioned above.

#### 3. Attributed marks

Similar to the second group, the final type of mark is an attributed mark, whose annotation is simply interpreted as a list of attributes to apply to the resulting span, in the same way as for the figure block itself (detailed above). The same attributes are supported in attributed marks as in the figure block's attributes list, with the exception of directives.

For example, the syntax `[some text]{.big title='This!'}` will result in a FigureMark span with the `big` CSS class applied, and with a `title` attribute which has the value `"This!"`.

As a convenience, there is a special case: if the entire attributes string has no prefix and no whitespace, it will be treated as a dot-separated list of one or more CSS classes. Thus, both of these are equivalent: `[text]{.big}` and `[text]{big}`, and you can apply the CSS classes `one`, `two`, and `three` like this: `[text]{one.two.three}`. This essentially allows applying custom short marks, with suitable CSS styles defined.

---

## Questions

The following questions are anticipated, and answers provided.

#### Where is FigureMark in use?

Currently, it's used in my own pandoc-based publishing system, [pandoc-publish](https://github.com/mattgemmell/pandoc-publish/), and also [on my site](https://mattgemmell.scot).

#### How can I annotate an example of FigureMark syntax using FigureMark?

To avoid ambiguity for the parser, follow these two rules:

1. The outer FigureMark block should either use a different number of backticks/tildes for its opening and closing lines than the inner example block does, or the outer and inner blocks should use different delimiters (for example, use tildes on the outer block and backticks on the inner).

2. Within the example block, escape each square bracket and curly brace with a backslash if they would otherwise be interpreted as FigureMark syntax. Any such backslashes will be removed when the block is processed.

This will allow FigureMark samples to be annotated, as shown below.

~~~figuremark FigureMark Syntax {.example #inception}
[```figuremark]{!} Example of FigureMark [{.example}]{!}
Some [\[]{!}marked up[\]{!}]{!} text. [{1}]{!} [\[]{!}// comment[\]{/}]{!}
[```]{!}
~~~

#### Can I have more than one type of (numeric) reference marks?

Certainly. Since reference marks (e.g. `{1}`) are mapped to the CSS class `reference`, you can use an attributed mark with that same class plus an additional modifier class: `[2]{.reference .modifier}`.

If you just want, for example, to change the colour of each number for regular reference marks, note that each resulting span will have not only the `reference` class, but also `reference-1` and so on, as appropriate to the numeric value.

Feel free to [contact me](https://mattgemmell.scot/contact/) with any other questions or remarks.
