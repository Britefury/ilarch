##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch.event_handler import EventHandler
from larch.pres.html import Html
from larch.pres.pres import CompositePres
from larch.pres.resource import MessageChannel




class text_entry (CompositePres):
	def __init__(self, text, immediate_events=False, on_edit=None, width=None):
		"""
		Create a text entry control
		:param text: the initial text to display in the control
		:param immediate_events: if True, an event will be emitted each time the text is edited (on each keypress)
		:param on_edit: a callback invoked in response to edits, of the form function(modified_text)
		:param width: width of the control; ints or longs will be interpreted as width in pixels, otherwise use string in CSS form, e.g. '100px', '10em' or '50%'
		:return: the editor control
		"""
		self.edit = EventHandler()

		if isinstance(width, int)  or  isinstance(width, long):
			width = '{0}px'.format(width)

		self.__text = text
		self.__immediate_events = immediate_events
		self.__width = width

		if on_edit is not None:
			self.edit.connect(on_edit)

		self.__channel = MessageChannel()


	def set_text(self, text):
		self.__channel.send(text)


	def pres(self, pres_ctx):
		sz = ''
		if self.__width is not None:
			sz = ' style="width: {0};"'.format(self.__width)
		p = Html('<input type="text" value="{0}"{1}></input>'.format(self.__text, sz)).js_function_call('larch.controls.initTextEntry', self.__immediate_events, self.__channel)
		p = p.with_event_handler('text_entry_edit', lambda event: self.edit(event, event.data))
		p = p.use_js('/files/static/larch/larch_ui.js').use_css('/files/static/larch/larch_ui.css')
		return p




class live_text_entry (CompositePres):
	def __init__(self, live, immediate_events=False, width=None):
		"""
		Text entry control that edits a live value

		:param live: live value object whose value is to be edited
		:param immediate_events: if True, an event will be emitted each time the text is edited (on each keypress)
		:param width: width, controlled by CSS
		:return: the editor control
		"""
		self.__live = live
		self.__immediate_events = immediate_events
		self.__width = width


	def pres(self, pres_ctx):
		refreshing = [False]

		def set_value():
			s.set_text(self.__live.value)

		def on_change(incr):
			if not refreshing[0]:
				pres_ctx.fragment_view.queue_task(set_value)

		def __on_edit(event, value):
			refreshing[0] = True
			self.__live.value = value
			refreshing[0] = False

		self.__live.add_listener(on_change)

		s = text_entry(self.__live.static_value, self.__immediate_events, width=self.__width)
		s.edit.connect(__on_edit)
		return s

