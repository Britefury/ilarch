##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
__author__ = 'Geoff'

from HTMLParser import HTMLParser
from larch import js



class DynamicSegment (object):
	"""A dynamic segment

	Represents a segment of HTML content. Its contents is stored in an HtmlContent object.

	Segments can be nested via references; create a reference using the reference() method and put it into the content of a parent segment to nest this within a parent segment.
	"""
	def __init__(self, page, seg_id, content=None, fragment=None):
		"""
		Constructor

		:param page: The dynamic page that contains this segment
		:param seg_id: A segment identifier string; used on both client and server side to identify this segment; must be unique within the page (auto-generate it with a counter)
		:param content: The content that this segment should contain
		:param fragment: The fragment that this segment is a part of
		"""
		self.__id = seg_id
		assert content is None  or  isinstance(content, HtmlContent)
		self.__page = page
		self.__fragment = fragment
		self.__parent = None
		self.__event_handlers = None
		self.__initialise_scripts = None
		self.__shutdown_scripts = None

		self.__structure_valid = True
		if page._enable_structure_fixing  and  content is not None:
			fixed_content, fixes = content._fix_structure()
			if fixes is not None:
				content = fixed_content
				self.__structure_valid = False
				self.__page._notify_segment_html_structure_fixes(self, fixes)
				self.__page._notify_segment_html_structure_validity_change(self, False)

		self.__content = content
		self.__connect_children()


	@property
	def id(self):
		"""
		The segment ID
		"""
		return self.__id

	@property
	def parent(self):
		"""
		The parent segment
		"""
		return self.__parent


	@property
	def fragment(self):
		"""
		The fragment
		:return: The containing fragment
		"""
		return self.__fragment

	@property
	def page(self):
		"""
		The page
		:return: the page
		"""
		return self.__page


	@property
	def content(self):
		"""The content. Must be either None or an HtmlContent instance.
		"""
		return self.__content

	@content.setter
	def content(self, x):
		"""
		Set the content of the segment
		:param x: new content
		:return: None
		"""
		if x is not None  and not  isinstance(x, HtmlContent):
			raise TypeError, 'Content should be either None or an HtmlContent instance'
		valid = True
		fixes = None
		if self.__page._enable_structure_fixing  and  x is not None:
			fixed_x, fixes = x._fix_structure()
			if fixes is not None:
				valid = False
				x = fixed_x
				self.__page._notify_segment_html_structure_fixes(self, fixes)

		self.__disconnect_children()
		self.__content = x
		if valid != self.__structure_valid:
			self.__structure_valid = valid
			self.__page._notify_segment_html_structure_validity_change(self, valid)
		self.__connect_children()
		self.__page._table._segment_modified(self, x)


	def reference(self):
		"""Create a reference to this segment.
		"""
		return SegmentRef(self)



	# Event handling
	def add_event_handler(self, handler):
		"""Register an event handler
		"""
		if self.__event_handlers is None:
			self.__event_handlers = []
		self.__event_handlers.append(handler)


	def _handle_event(self, event):
		if self.__event_handlers is not None:
			for handler in self.__event_handlers:
				if handler(event):
					return True
		return False


	# Initialisation
	def get_initialise_scripts(self):
		return self.__initialise_scripts

	def add_initialise_script(self, script):
		"""
		Add an initialisation script. Initialisation scripts will be executed when the element is initialised after being inserted into the DOM.

		:param script: a Javascript expression to evaluate. For each DOM element represented by this segment, the code will be evaluated with the element bound to the name 'node'.
		"""
		if self.__initialise_scripts is None:
			self.__initialise_scripts = []
		self.__initialise_scripts.append(script)



	# Shutdown
	def get_shutdown_scripts(self):
		return self.__shutdown_scripts

	def add_shutdown_script(self, script):
		"""
		Add a shutdown script. Shutdown scripts will be executed when the element is shutdown before being removed from the DOM

		:param script: a Javascript expression to evaluate. For each DOM element represented by this segment, the code will be evaluated with the element bound to the name 'node'.
		"""
		if self.__shutdown_scripts is None:
			self.__shutdown_scripts = []
		self.__shutdown_scripts.append(script)



	# Queued scripts
	def queue_script(self, script):
		"""
		Queue a Javascript expression to evaluate

		:param script: a Javascript expression to evaluate. For each DOM element represented by this segment, the code will be evaluated with the element bound to the name 'node'.
		"""
		if isinstance(script, js.JS):
			script = script.build_js(self.__fragment.create_presentation_context())
		self.__page._queue_segment_script(self.__id, script)


	def queue_script_function_call(self, js_fn_name, *args):
		return self.queue_script(js.JSCall(js_fn_name, (js.name_node,) + args))



	# HTML generation
	def _place_holder(self):
		return '<span class="__lch_seg_placeholder" data-larchsegid="{0}"></span>'.format(self.__id)

	def _inline_html(self, ref_resolver):
		items = []
		self._build_inline_html(items, ref_resolver)
		return u''.join(items)

	def _build_inline_html(self, items, ref_resolver):
		items.append('<span class="__lch_seg_begin" data-larchsegid="{0}"></span>'.format(self.__id))
		if self.__content is not None:
			self.__content._build_html(items, ref_resolver)
		items.append('<span class="__lch_seg_end" data-larchsegid="{0}"></span>'.format(self.__id))



	def __connect_children(self):
		if self.__content is not None:
			self.__connect_children_in_content(self.__content)


	def __disconnect_children(self):
		if self.__content is not None:
			self.__disconnect_children_in_content(self.__content)



	def __connect_children_in_content(self, content):
		for x in content:
			if isinstance(x, basestring):
				continue
			elif isinstance(x, SegmentRef):
				seg = x.segment
				seg.__parent = self
			elif isinstance(x, HtmlContent):
				self.__connect_children_in_content(x)
			else:
				raise TypeError, 'contents of HtmlContent should be str, unicode, SegmentRef or HtmlContent'

	def __disconnect_children_in_content(self, content):
		for x in content:
			if isinstance(x, basestring):
				continue
			elif isinstance(x, SegmentRef):
				seg = x.segment
				seg.__parent = None
			elif isinstance(x, HtmlContent):
				self.__disconnect_children_in_content(x)
			else:
				raise TypeError, 'contents of HtmlContent should be str, unicode, SegmentRef or HtmlContent'










class SegmentRef (object):
	"""A reference to a segment. Put these in HtmlContent objects to nest segments.
	"""
	def __init__(self, segment):
		assert isinstance(segment, DynamicSegment)
		self.__segment = segment


	@property
	def segment(self):
		return self.__segment

	def _build_html(self, items, ref_resolver=None):
		"""Generate the HTML source represented by this SegmentRef instance.

		items - the list of strings that is constructed during the build process, they are concatenated to make the HTML source
		ref_resolver - a function used to resolve segment references
		"""
		if ref_resolver is not None:
			ref_resolver(items, self.__segment)
		else:
			items.append(self.__segment._place_holder())


	def _complete_html(self):
		"""Build the HTML content of the complete segment subtree rooted at the segment pointed to by this reference

		All references are inlined.
		"""
		items = []
		self._build_html(items, self.__resolve_complete)
		return ''.join(items)


	def __resolve_complete(self, items, seg):
		return seg._build_inline_html(items, self.__resolve_complete)







class HtmlContent (list):
	"""HTML Content

	Used to represent the HTML content of a dynamic segment.

	It is a sequence of items, each of which can be a string/unicode, a SegmentRef or an HtmlContent.
	"""
	def __init__(self, contents):
		for x in contents:
			assert isinstance(x, basestring)  or  isinstance(x, SegmentRef)  or  isinstance(x, HtmlContent)
		super(HtmlContent, self).__init__(contents)


	def _build_html(self, items, ref_resolver=None):
		"""Generate the HTML source represented by this HtmlContent instance.

		items - the list of strings that is constructed during the build process, they are concatenated to make the HTML source
		ref_resolver - a function used to resolve segment references
		"""
		for x in self:
			if isinstance(x, basestring):
				items.append(x)
			else:
				x._build_html(items, ref_resolver)


	def _fix_structure(self):
		c = _HtmlContentStructureFixer()
		xs = []
		fixes = []
		for x in self:
			if isinstance(x, basestring):
				c.item(x)
				item_fixes = c.item_fixes()
				if len(item_fixes) > 0:
					xs.append(c.output)
					fixes.extend(item_fixes)
				else:
					xs.append(x)
			elif isinstance(x, HtmlContent):
				fixed, item_fixes = x._fix_structure()
				if item_fixes is not None:
					xs.append(fixed)
					fixes.extend(item_fixes)
				else:
					xs.append(x)
			else:
				xs.append(x)

		c.finish()

		item_fixes = c.item_fixes()
		if len(item_fixes) > 0:
			xs.append(c.output)
			fixes.extend(item_fixes)

		if len(fixes) > 0:
			return HtmlContent(xs), fixes
		else:
			return self, None






class _HtmlContentStructureFixer (HTMLParser):
	__self_closing_tags = {'img', 'input', 'br', 'hr', 'frame', 'area', 'base', 'basefont', 'col', 'isindex', 'link', 'meta', 'param'}

	def __init__(self):
		HTMLParser.__init__(self)

		self.__tag_stack = []
		self.__item_index = 0

		self.__end_tags_to_insert = []

		self.__out = []
		self.__fixes = []


	def item(self, x):
		# Reset
		self.__out = []
		self.__fixes = []

		# Feed the data
		self.feed(x)

		# Close off
		self.close()


	def finish(self):
		self.__out = []
		self.__fixes = []

		# Close unclosed tags
		while len(self.__tag_stack) > 0:
			tag = self.__tag_stack.pop()
			self._emit('</' + tag + '>')
			self.__fixes.append(_CloseUnclosedTagFix(tag))



	@property
	def output(self):
		return ''.join(self.__out)

	def item_fixes(self):
		return self.__fixes


	def _emit(self, text):
		self.__out.append(text)


	def handle_starttag(self, tag, attrs):
		t = tag.strip().lower()
		if t not in self.__self_closing_tags:
			self.__tag_stack.append(t)
		self._emit(self.get_starttag_text())

	def handle_endtag(self, tag):
		# If there are tags to close
		if len(self.__tag_stack) > 0:
			t = tag.strip().lower()
			if t == self.__tag_stack[-1]:
				# The tag matches the tag at the top of the stack: close it
				self._emit('</' + tag + '>')
				self.__tag_stack.pop()
			else:
				if t in self.__tag_stack:
					# There are tags that must be closed before this one
					while t != self.__tag_stack[-1]:
						tag_to_close = self.__tag_stack.pop()
						self._emit('</' + tag_to_close + '>')
						self.__fixes.append(_CloseUnclosedTagFix(tag_to_close))
					# We have reached the matching start tag: close it
					self._emit('</' + tag + '>')
				else:
					# There is no tag on the tag stack by this name waiting to be closed: drop it
					self.__fixes.append(_DropCloseTagWithNoMatchingOpenTag(t))
					pass
		else:
			# No tags left to close: drop it
			self.__fixes.append(_DropCloseTagWithNoMatchingOpenTag(tag))
			pass

	def handle_startendtag(self, tag, attrs):
		self._emit(self.get_starttag_text())

	def handle_data(self, data):
		self._emit(data)

	def handle_entityref(self, name):
		self._emit('&' + name + ';')

	def handle_charref(self, name):
		self._emit('&#' + name + ';')

	def handle_comment(self, data):
		self._emit('<!--' + data + '-->')

	def handle_decl(self, decl):
		self._emit('<!' + decl + '>')

	def handle_pi(self, data):
		self._emit('<?' + data + '>')

	def unknown_decl(self, data):
		self._emit('<![' + data + ']>')




class _HtmlFix (object):
	def to_json(self):
		raise NotImplementedError, 'abstract'


class _CloseUnclosedTagFix (_HtmlFix):
	def __init__(self, tag):
		self.__tag = tag

	def __eq__(self, other):
		if isinstance(other, _CloseUnclosedTagFix):
			return self.__tag == other.__tag
		else:
			return False

	def to_json(self):
		return {'fix_type': 'close_unclosed_tag', 'tag': self.__tag}

	def __str__(self):
		return 'INSERT(</{0}>)'.format(self.__tag)


class _DropCloseTagWithNoMatchingOpenTag (_HtmlFix):
	def __init__(self, tag):
		self.__tag = tag

	def __eq__(self, other):
		if isinstance(other, _DropCloseTagWithNoMatchingOpenTag):
			return self.__tag == other.__tag
		else:
			return False

	def to_json(self):
		return {'fix_type': 'drop_close_tag_with_no_matching_open_tag', 'tag': self.__tag}

	def __str__(self):
		return 'DELETE(</{0}>)'.format(self.__tag)




import unittest

class Test_FixHtmlContent (unittest.TestCase):
	def test_valid(self):
		c = HtmlContent(['<button>', 'Test', '</button>'])
		f, fixes = c._fix_structure()
		self.assertEqual(fixes, None)
		self.assertIs(f, c)

	def test_unclosed(self):
		c = HtmlContent(['<div>', 'Test',])
		f, fixes = c._fix_structure()
		self.assertEqual(fixes, [_CloseUnclosedTagFix('div')])
		self.assertEqual(f, HtmlContent(['<div>', 'Test', '</div>']))