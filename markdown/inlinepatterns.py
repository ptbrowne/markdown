# -*- coding: utf-8 -*-
"""
Python Markdown

A Python implementation of John Gruber's Markdown.

Documentation: https://python-markdown.github.io/
GitHub: https://github.com/Python-Markdown/markdown/
PyPI: https://pypi.org/project/Markdown/

Started by Manfred Stienstra (http://www.dwerg.net/).
Maintained for a few years by Yuri Takhteyev (http://www.freewisdom.org).
Currently maintained by Waylan Limberg (https://github.com/waylan),
Dmitry Shachnev (https://github.com/mitya57) and Isaac Muse (https://github.com/facelessuser).

Copyright 2007-2018 The Python Markdown Project (v. 1.7 and later)
Copyright 2004, 2005, 2006 Yuri Takhteyev (v. 0.2-1.6b)
Copyright 2004 Manfred Stienstra (the original version)

License: BSD (see LICENSE.md for details).

INLINE PATTERNS
=============================================================================

Inline patterns such as *emphasis* are handled by means of auxiliary
objects, one per pattern.  Pattern objects must be instances of classes
that extend markdown.Pattern.  Each pattern object uses a single regular
expression and needs support the following methods:

    pattern.getCompiledRegExp() # returns a regular expression

    pattern.handleMatch(m) # takes a match object and returns
                           # an ElementTree element or just plain text

All of python markdown's built-in patterns subclass from Pattern,
but you can add additional patterns that don't.

Also note that all the regular expressions used by inline must
capture the whole block.  For this reason, they all start with
'^(.*)' and end with '(.*)!'.  In case with built-in expression
Pattern takes care of adding the "^(.*)" and "(.*)!".

Finally, the order in which regular expressions are applied is very
important - e.g. if we first replace http://.../ links with <a> tags
and _then_ try to replace inline html, we would end up with a mess.
So, we apply the expressions in the following order:

* escape and backticks have to go before everything else, so
  that we can preempt any markdown patterns by escaping them.

* then we handle auto-links (must be done before inline html)

* then we handle inline HTML.  At this point we will simply
  replace all inline HTML strings with a placeholder and add
  the actual HTML to a hash.

* then inline images (must be done before links)

* then bracketed links, first regular then reference-style

* finally we apply strong and emphasis
"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import util
import re
try:  # pragma: no cover
    from html import entities
except ImportError:  # pragma: no cover
    import htmlentitydefs as entities


def build_inlinepatterns(md, **kwargs):
    """ Build the default set of inline patterns for Markdown. """
    inlinePatterns = util.Registry()
    inlinePatterns.register(BacktickInlineProcessor(BACKTICK_RE), 'backtick', 190)
    inlinePatterns.register(EscapeInlineProcessor(ESCAPE_RE, md), 'escape', 180)
    inlinePatterns.register(ReferenceInlineProcessor(REFERENCE_RE, md), 'reference', 170)
    inlinePatterns.register(LinkInlineProcessor(LINK_RE, md), 'link', 160)
    inlinePatterns.register(ImageInlineProcessor(IMAGE_LINK_RE, md), 'image_link', 150)
    inlinePatterns.register(
        ImageReferenceInlineProcessor(IMAGE_REFERENCE_RE, md), 'image_reference', 140
    )
    inlinePatterns.register(
        ShortReferenceInlineProcessor(REFERENCE_RE, md), 'short_reference', 130
    )
    inlinePatterns.register(AutolinkInlineProcessor(AUTOLINK_RE, md), 'autolink', 120)
    inlinePatterns.register(AutomailInlineProcessor(AUTOMAIL_RE, md), 'automail', 110)
    inlinePatterns.register(SubstituteTagInlineProcessor(LINE_BREAK_RE, 'br'), 'linebreak', 100)
    inlinePatterns.register(HtmlInlineProcessor(HTML_RE, md), 'html', 90)
    inlinePatterns.register(HtmlInlineProcessor(ENTITY_RE, md), 'entity', 80)
    inlinePatterns.register(SimpleTextInlineProcessor(NOT_STRONG_RE), 'not_strong', 70)
    inlinePatterns.register(DoubleTagInlineProcessor(EM_STRONG_RE, 'strong,em'), 'em_strong', 60)
    inlinePatterns.register(DoubleTagInlineProcessor(STRONG_EM_RE, 'em,strong'), 'strong_em', 50)
    inlinePatterns.register(SimpleTagInlineProcessor(STRONG_RE, 'strong'), 'strong', 40)
    inlinePatterns.register(SimpleTagInlineProcessor(EMPHASIS_RE, 'em'), 'emphasis', 30)
    inlinePatterns.register(SimpleTagInlineProcessor(SMART_STRONG_RE, 'strong'), 'strong2', 20)
    inlinePatterns.register(SimpleTagInlineProcessor(SMART_EMPHASIS_RE, 'em'), 'emphasis2', 10)
    return inlinePatterns


"""
The actual regular expressions for patterns
-----------------------------------------------------------------------------
"""

NOIMG = r'(?<!\!)'

# `e=f()` or ``e=f("`")``
BACKTICK_RE = r'(?:(?<!\\)((?:\\{2})+)(?=`+)|(?<!\\)(`+)(.+?)(?<!`)\2(?!`))'

# \<
ESCAPE_RE = r'\\(.)'

# *emphasis*
EMPHASIS_RE = r'(\*)([^\*]+)\1'

# **strong**
STRONG_RE = r'(\*{2})(.+?)\1'

# __smart__strong__
SMART_STRONG_RE = r'(?<!\w)(_{2})(?!_)(.+?)(?<!_)\1(?!\w)'

# _smart_emphasis_
SMART_EMPHASIS_RE = r'(?<!\w)(_)(?!_)(.+?)(?<!_)\1(?!\w)'

# ***strongem*** or ***em*strong**
EM_STRONG_RE = r'(\*|_)\1{2}(.+?)\1(.*?)\1{2}'

# ***strong**em*
STRONG_EM_RE = r'(\*|_)\1{2}(.+?)\1{2}(.*?)\1'

# [text](url) or [text](<url>) or [text](url "title")
LINK_RE = NOIMG + r'\['

# ![alttxt](http://x.com/) or ![alttxt](<http://x.com/>)
IMAGE_LINK_RE = r'\!\['

# [Google][3]
REFERENCE_RE = LINK_RE

# ![alt text][2]
IMAGE_REFERENCE_RE = IMAGE_LINK_RE

# stand-alone * or _
NOT_STRONG_RE = r'((^|\s)(\*|_)(\s|$))'

# <http://www.123.com>
AUTOLINK_RE = r'<((?:[Ff]|[Hh][Tt])[Tt][Pp][Ss]?://[^<>]*)>'

# <me@example.com>
AUTOMAIL_RE = r'<([^<> !]*@[^@<> ]*)>'

# <...>
HTML_RE = r'(<([a-zA-Z/][^<>]*|!--(?:(?!<!--|-->).)*--)>)'

# "&#38;" (decimal) or "&#x26;" (hex) or "&amp;" (named)
ENTITY_RE = r'(&(?:\#[0-9]+|\#x[0-9a-fA-F]+|[a-zA-Z0-9]+);)'

# two spaces at end of line
LINE_BREAK_RE = r'  \n'


def dequote(string):
    """Remove quotes from around a string."""
    if ((string.startswith('"') and string.endswith('"')) or
       (string.startswith("'") and string.endswith("'"))):
        return string[1:-1]
    else:
        return string


"""
The pattern classes
-----------------------------------------------------------------------------
"""


class Pattern(object):  # pragma: no cover
    """Base class that inline patterns subclass. """

    ANCESTOR_EXCLUDES = tuple()

    def __init__(self, pattern, md=None):
        """
        Create an instant of an inline pattern.

        Keyword arguments:

        * pattern: A regular expression that matches a pattern

        """
        self.pattern = pattern
        self.compiled_re = re.compile(r"^(.*?)%s(.*)$" % pattern,
                                      re.DOTALL | re.UNICODE)

        self.md = md

    @property
    @util.deprecated("Use 'md' instead.")
    def markdown(self):
        # TODO: remove this later
        return self.md

    def getCompiledRegExp(self):
        """ Return a compiled regular expression. """
        return self.compiled_re

    def handleMatch(self, m):
        """Return a ElementTree element from the given match.

        Subclasses should override this method.

        Keyword arguments:

        * m: A re match object containing a match of the pattern.

        """
        pass  # pragma: no cover

    def type(self):
        """ Return class name, to define pattern type """
        return self.__class__.__name__

    def unescape(self, text):
        """ Return unescaped text given text with an inline placeholder. """
        try:
            stash = self.md.treeprocessors['inline'].stashed_nodes
        except KeyError:  # pragma: no cover
            return text

        def get_stash(m):
            id = m.group(1)
            if id in stash:
                value = stash.get(id)
                if isinstance(value, util.string_type):
                    return value
                else:
                    # An etree Element - return text content only
                    return ''.join(value.itertext())
        return util.INLINE_PLACEHOLDER_RE.sub(get_stash, text)


class InlineProcessor(Pattern):
    """
    Base class that inline patterns subclass.

    This is the newer style inline processor that uses a more
    efficient and flexible search approach.
    """

    def __init__(self, pattern, md=None):
        """
        Create an instant of an inline pattern.

        Keyword arguments:

        * pattern: A regular expression that matches a pattern

        """
        self.pattern = pattern
        self.compiled_re = re.compile(pattern, re.DOTALL | re.UNICODE)

        # Api for Markdown to pass safe_mode into instance
        self.safe_mode = False
        self.md = md

    def handleMatch(self, m, data):
        """Return a ElementTree element from the given match and the
        start and end index of the matched text.

        If `start` and/or `end` are returned as `None`, it will be
        assumed that the processor did not find a valid region of text.

        Subclasses should override this method.

        Keyword arguments:

        * m: A re match object containing a match of the pattern.
        * data: The buffer current under analysis

        Returns:

        * el: The ElementTree element, text or None.
        * start: The start of the region that has been matched or None.
        * end: The end of the region that has been matched or None.

        """
        pass  # pragma: no cover


class SimpleTextPattern(Pattern):  # pragma: no cover
    """ Return a simple text of group(2) of a Pattern. """
    def handleMatch(self, m):
        return m.group(2)


class SimpleTextInlineProcessor(InlineProcessor):
    """ Return a simple text of group(1) of a Pattern. """
    def handleMatch(self, m, data):
        return m.group(1), m.start(0), m.end(0)


class EscapeInlineProcessor(InlineProcessor):
    """ Return an escaped character. """

    def handleMatch(self, m, data):
        char = m.group(1)
        if char in self.md.ESCAPED_CHARS:
            return '%s%s%s' % (util.STX, ord(char), util.ETX), m.start(0), m.end(0)
        else:
            return None, m.start(0), m.end(0)


class SimpleTagPattern(Pattern):  # pragma: no cover
    """
    Return element of type `tag` with a text attribute of group(3)
    of a Pattern.

    """
    def __init__(self, pattern, tag):
        Pattern.__init__(self, pattern)
        self.tag = tag

    def handleMatch(self, m):
        el = util.etree.Element(self.tag)
        el.text = m.group(3)
        return el


class SimpleTagInlineProcessor(InlineProcessor):
    """
    Return element of type `tag` with a text attribute of group(2)
    of a Pattern.

    """
    def __init__(self, pattern, tag):
        InlineProcessor.__init__(self, pattern)
        self.tag = tag

    def handleMatch(self, m, data):
        el = util.etree.Element(self.tag)
        el.text = m.group(2)
        return el, m.start(0), m.end(0)


class SubstituteTagPattern(SimpleTagPattern):  # pragma: no cover
    """ Return an element of type `tag` with no children. """
    def handleMatch(self, m):
        return util.etree.Element(self.tag)


class SubstituteTagInlineProcessor(SimpleTagInlineProcessor):
    """ Return an element of type `tag` with no children. """
    def handleMatch(self, m, data):
        return util.etree.Element(self.tag), m.start(0), m.end(0)


class BacktickInlineProcessor(InlineProcessor):
    """ Return a `<code>` element containing the matching text. """
    def __init__(self, pattern):
        InlineProcessor.__init__(self, pattern)
        self.ESCAPED_BSLASH = '%s%s%s' % (util.STX, ord('\\'), util.ETX)
        self.tag = 'code'

    def handleMatch(self, m, data):
        if m.group(3):
            el = util.etree.Element(self.tag)
            el.text = util.AtomicString(util.code_escape(m.group(3).strip()))
            return el, m.start(0), m.end(0)
        else:
            return m.group(1).replace('\\\\', self.ESCAPED_BSLASH), m.start(0), m.end(0)


class DoubleTagPattern(SimpleTagPattern):  # pragma: no cover
    """Return a ElementTree element nested in tag2 nested in tag1.

    Useful for strong emphasis etc.

    """
    def handleMatch(self, m):
        tag1, tag2 = self.tag.split(",")
        el1 = util.etree.Element(tag1)
        el2 = util.etree.SubElement(el1, tag2)
        el2.text = m.group(3)
        if len(m.groups()) == 5:
            el2.tail = m.group(4)
        return el1


class DoubleTagInlineProcessor(SimpleTagInlineProcessor):
    """Return a ElementTree element nested in tag2 nested in tag1.

    Useful for strong emphasis etc.

    """
    def handleMatch(self, m, data):
        tag1, tag2 = self.tag.split(",")
        el1 = util.etree.Element(tag1)
        el2 = util.etree.SubElement(el1, tag2)
        el2.text = m.group(2)
        if len(m.groups()) == 3:
            el2.tail = m.group(3)
        return el1, m.start(0), m.end(0)


class HtmlInlineProcessor(InlineProcessor):
    """ Store raw inline html and return a placeholder. """
    def handleMatch(self, m, data):
        rawhtml = self.unescape(m.group(1))
        place_holder = self.md.htmlStash.store(rawhtml)
        return place_holder, m.start(0), m.end(0)

    def unescape(self, text):
        """ Return unescaped text given text with an inline placeholder. """
        try:
            stash = self.md.treeprocessors['inline'].stashed_nodes
        except KeyError:  # pragma: no cover
            return text

        def get_stash(m):
            id = m.group(1)
            value = stash.get(id)
            if value is not None:
                try:
                    return self.md.serializer(value)
                except Exception:
                    return r'\%s' % value

        return util.INLINE_PLACEHOLDER_RE.sub(get_stash, text)


class LinkInlineProcessor(InlineProcessor):
    """ Return a link element from the given match. """
    RE_LINK = re.compile(r'''\(\s*(?:(<[^<>]*>)\s*(?:('[^']*'|"[^"]*")\s*)?\))?''', re.DOTALL | re.UNICODE)
    RE_TITLE_CLEAN = re.compile(r'\s')

    def handleMatch(self, m, data):
        text, index, handled = self.getText(data, m.end(0))

        if not handled:
            return None, None, None

        href, title, index, handled = self.getLink(data, index)
        if not handled:
            return None, None, None

        el = util.etree.Element("a")
        el.text = text

        el.set("href", href)

        if title is not None:
            el.set("title", title)

        return el, m.start(0), index

    def getLink(self, data, index):
        """Parse data between `()` of `[Text]()` allowing recursive `()`. """

        href = ''
        title = None
        handled = False

        m = self.RE_LINK.match(data, pos=index)
        if m and m.group(1):
            # Matches [Text](<link> "title")
            href = m.group(1)[1:-1].strip()
            if m.group(2):
                title = m.group(2)[1:-1]
            index = m.end(0)
            handled = True
        elif m:
            # Track bracket nesting and index in string
            bracket_count = 1
            backtrack_count = 1
            start_index = m.end()
            index = start_index
            last_bracket = -1

            # Primary (first found) quote tracking.
            quote = None
            start_quote = -1
            exit_quote = -1
            ignore_matches = False

            # Secondary (second found) quote tracking.
            alt_quote = None
            start_alt_quote = -1
            exit_alt_quote = -1

            # Track last character
            last = ''

            for pos in util.iterrange(index, len(data)):
                c = data[pos]
                if c == '(':
                    # Count nested (
                    # Don't increment the bracket count if we are sure we're in a title.
                    if not ignore_matches:
                        bracket_count += 1
                    elif backtrack_count > 0:
                        backtrack_count -= 1
                elif c == ')':
                    # Match nested ) to (
                    # Don't decrement if we are sure we are in a title that is unclosed.
                    if ((exit_quote != -1 and quote == last) or (exit_alt_quote != -1 and alt_quote == last)):
                        bracket_count = 0
                    elif not ignore_matches:
                        bracket_count -= 1
                    elif backtrack_count > 0:
                        backtrack_count -= 1
                        # We've found our backup end location if the title doesn't reslove.
                        if backtrack_count == 0:
                            last_bracket = index + 1

                elif c in ("'", '"'):
                    # Quote has started
                    if not quote:
                        # We'll assume we are now in a title.
                        # Brackets are quoted, so no need to match them (except for the final one).
                        ignore_matches = True
                        backtrack_count = bracket_count
                        bracket_count = 1
                        start_quote = index + 1
                        quote = c
                    # Secondary quote (in case the first doesn't resolve): [text](link'"title")
                    elif c != quote and not alt_quote:
                        start_alt_quote = index + 1
                        alt_quote = c
                    # Update primary quote match
                    elif c == quote:
                        exit_quote = index + 1
                    # Update secondary quote match
                    elif alt_quote and c == alt_quote:
                        exit_alt_quote = index + 1

                index += 1

                # Link is closed, so let's break out of the loop
                if bracket_count == 0:
                    # Get the title if we closed a title string right before link closed
                    if exit_quote >= 0 and quote == last:
                        href = data[start_index:start_quote - 1]
                        title = ''.join(data[start_quote:exit_quote - 1])
                    elif exit_alt_quote >= 0 and alt_quote == last:
                        href = data[start_index:start_alt_quote - 1]
                        title = ''.join(data[start_alt_quote:exit_alt_quote - 1])
                    else:
                        href = data[start_index:index - 1]
                    break

                if c != ' ':
                    last = c

            # We have a scenario: [test](link"notitle)
            # When we enter a string, we stop tracking bracket resolution in the main counter,
            # but we do keep a backup counter up until we discover where we might resolve all brackets
            # if the title string fails to resolve.
            if bracket_count != 0 and backtrack_count == 0:
                href = data[start_index:last_bracket - 1]
                index = last_bracket
                bracket_count = 0

            handled = bracket_count == 0

        if title is not None:
            title = self.RE_TITLE_CLEAN.sub(' ', dequote(self.unescape(title.strip())))

        href = self.unescape(href).strip()

        return href, title, index, handled

    def getText(self, data, index):
        """Parse the content between `[]` of the start of an image or link
        resolving nested square brackets.

        """
        bracket_count = 1
        text = []
        for pos in util.iterrange(index, len(data)):
            c = data[pos]
            if c == ']':
                bracket_count -= 1
            elif c == '[':
                bracket_count += 1
            index += 1
            if bracket_count == 0:
                break
            text.append(c)
        return ''.join(text), index, bracket_count == 0


class ImageInlineProcessor(LinkInlineProcessor):
    """ Return a img element from the given match. """

    def handleMatch(self, m, data):
        text, index, handled = self.getText(data, m.end(0))
        if not handled:
            return None, None, None

        src, title, index, handled = self.getLink(data, index)
        if not handled:
            return None, None, None

        el = util.etree.Element("img")

        el.set("src", src)

        if title is not None:
            el.set("title", title)

        el.set('alt', self.unescape(text))
        return el, m.start(0), index


class ReferenceInlineProcessor(LinkInlineProcessor):
    """ Match to a stored reference and return link element. """
    NEWLINE_CLEANUP_RE = re.compile(r'\s+', re.MULTILINE)

    RE_LINK = re.compile(r'\s?\[([^\]]*)\]', re.DOTALL | re.UNICODE)

    def handleMatch(self, m, data):
        text, index, handled = self.getText(data, m.end(0))
        if not handled:
            return None, None, None

        id, end, handled = self.evalId(data, index, text)
        if not handled:
            return None, None, None

        # Clean up linebreaks in id
        id = self.NEWLINE_CLEANUP_RE.sub(' ', id)
        if id not in self.md.references:  # ignore undefined refs
            return None, m.start(0), end

        href, title = self.md.references[id]

        return self.makeTag(href, title, text), m.start(0), end

    def evalId(self, data, index, text):
        """
        Evaluate the id portion of [ref][id].

        If [ref][] use [ref].
        """
        m = self.RE_LINK.match(data, pos=index)
        if not m:
            return None, index, False
        else:
            id = m.group(1).lower()
            end = m.end(0)
            if not id:
                id = text.lower()
        return id, end, True

    def makeTag(self, href, title, text):
        el = util.etree.Element('a')

        el.set('href', href)
        if title:
            el.set('title', title)

        el.text = text
        return el


class ShortReferenceInlineProcessor(ReferenceInlineProcessor):
    """Shorte form of reference: [google]. """
    def evalId(self, data, index, text):
        """Evaluate the id from of [ref]  """

        return text.lower(), index, True


class ImageReferenceInlineProcessor(ReferenceInlineProcessor):
    """ Match to a stored reference and return img element. """
    def makeTag(self, href, title, text):
        el = util.etree.Element("img")
        el.set("src", href)
        if title:
            el.set("title", title)
        el.set("alt", self.unescape(text))
        return el


class AutolinkInlineProcessor(InlineProcessor):
    """ Return a link Element given an autolink (`<http://example/com>`). """
    def handleMatch(self, m, data):
        el = util.etree.Element("a")
        el.set('href', self.unescape(m.group(1)))
        el.text = util.AtomicString(m.group(1))
        return el, m.start(0), m.end(0)


class AutomailInlineProcessor(InlineProcessor):
    """
    Return a mailto link Element given an automail link (`<foo@example.com>`).
    """
    def handleMatch(self, m, data):
        el = util.etree.Element('a')
        email = self.unescape(m.group(1))
        if email.startswith("mailto:"):
            email = email[len("mailto:"):]

        def codepoint2name(code):
            """Return entity definition by code, or the code if not defined."""
            entity = entities.codepoint2name.get(code)
            if entity:
                return "%s%s;" % (util.AMP_SUBSTITUTE, entity)
            else:
                return "%s#%d;" % (util.AMP_SUBSTITUTE, code)

        letters = [codepoint2name(ord(letter)) for letter in email]
        el.text = util.AtomicString(''.join(letters))

        mailto = "mailto:" + email
        mailto = "".join([util.AMP_SUBSTITUTE + '#%d;' %
                          ord(letter) for letter in mailto])
        el.set('href', mailto)
        return el, m.start(0), m.end(0)
