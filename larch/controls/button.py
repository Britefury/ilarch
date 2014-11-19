##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch.event_handler import EventHandler
from larch.pres.pres import post_event_js_code_for_handler, CompositePres
from larch.pres.html import Html


class button (CompositePres):
	def __init__(self, text=None, action_fn=None, primary_icon=None, secondary_icon=None, disabled=False):
		"""
		Create a JQuery UI button
		:param text: the button content (can include HTML)
		:param action_fn: a callback that is invoked when the button is pressed, of the form function(event)
		:param primary_icon: primary icon (see JQuery UI icon classes)
		:param secondary_icon: secondary icon (see JQuery UI icon classes)
		:param disabled: disable the button
		:return: the button control
		"""
		self.__text = text
		self.clicked = EventHandler()
		self.__primary_icon = primary_icon
		self.__secondary_icon = secondary_icon
		self.__disabled = disabled
		if action_fn is not None:
			self.clicked.connect(action_fn)


	def pres(self, pres_ctx):
		options = {}
		if self.__disabled is not False:
			options['disabled'] = True

		if self.__primary_icon is not None  or  self.__secondary_icon is not None:
			icons = {}
			if self.__primary_icon is not None:
				icons['primary'] = self.__primary_icon
			if self.__secondary_icon is not None:
				icons['secondary'] = self.__secondary_icon
			options['icons'] = icons

		if self.__text is not None:
			p = Html('<button type="button" onclick="{0}">'.format(post_event_js_code_for_handler('clicked')), self.__text, '</button>').js_function_call('larch.controls.initButton', options)
		else:
			options['text'] = False
			p = Html('<button type="button" onclick="{0}"></button>').js_function_call('larch.controls.initButton', options)
		p = p.with_event_handler('clicked', self.clicked).use_js('/files/static/larch/larch_ui.js').use_css('/files/static/larch/larch_ui.css')
		return p