##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch.event_handler import EventHandler
from larch.live import AbstractLive, LiveValue, LiveFunction
from larch.pres.pres import post_event_js_code_for_handler, CompositePres
from larch.pres.html import Html



class dropdown_expander (CompositePres):
	def __init__(self, header, content, state=None, on_expand=None):
		"""
		Create a drop-down expander control. Consists of a button that the user clicks to open the control, display the content below

		:param header: the contents of the header button
		:param content: the content that is displayed when open
		:param state: the state; either in the form of a boolean which will be the initial state - True for open, False for closed - or a live value that contains the state
		:param on_expand: a callback invoked when the expander is expanded or contracted; of the form function(state)
		:return: the expander control
		"""
		self.__header = header
		self.__content = content

		self.expand = EventHandler()

		def expand_fn(x):
			self.state.value = x
			if on_expand is not None:
				on_expand(x)

		if state is None:
			self.state = LiveValue(False)
			self.__expand_fn = expand_fn
		elif isinstance(state, bool):
			self.state = LiveValue(state)
			self.__expand_fn = expand_fn
		elif isinstance(state, LiveValue):
			self.state = state
			self.__expand_fn = expand_fn
		elif isinstance(state, AbstractLive):
			self.state = state
			self.__expand_fn = on_expand
		else:
			raise TypeError, 'state must be None, a bool or an AbstractLive, not an {0}'.format(type(state).__name__)



	def pres(self, pres_ctx):
		def on_clicked(event):
			s = self.state.static_value
			new_state = not s
			if self.__expand_fn is not None:
				self.__expand_fn(new_state)
			self.expand(event, new_state)

		@LiveFunction
		def result():
			s = self.state.value
			if s is True:
				hdr = Html('<button onclick="{0}" style="width: 100%; text-align: left">'.format(post_event_js_code_for_handler('clicked')), self.__header, '</button>')
				hdr = hdr.js_function_call('larch.controls.initButton', {'icons': {'primary': 'ui-icon-minus'}})
				hdr = hdr.with_event_handler('clicked', on_clicked)
				ct = Html('<div class="dropdown_expander_content">', self.__content, '</div>')
				return Html(hdr, ct)
			elif s is False:
				hdr = Html('<button onclick="{0}" style="width: 100%; text-align: left">'.format(post_event_js_code_for_handler('clicked')), self.__header, '</button>')
				hdr = hdr.js_function_call('larch.controls.initButton', {'icons': {'primary': 'ui-icon-plus'}})
				hdr = hdr.with_event_handler('clicked', on_clicked)
				return hdr
			else:
				raise TypeError, 'drop down expander: state type unknown'

		return result




