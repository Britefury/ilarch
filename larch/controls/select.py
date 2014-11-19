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


class select (CompositePres):
	def __init__(self, option_value_content_pairs, value, on_choose=None):
		"""
		HTML select control

		:param option_value_content_pairs: a sequence of tuple-pairs describing the options. Each pair is of the form (value, text)
		:param value: the initial value
		:param on_choose: a callback function of the form fn(event, value) that is invoked when the user makes a choice
		"""
		self.__options = [Html('<option value="{0}"{1}>'.format(opt_value, (' selected'   if opt_value == value   else '')), content, '</option>')   for opt_value, content in option_value_content_pairs]
		self.choose = EventHandler()
		if on_choose is not None:
			self.choose.connect(on_choose)


	def pres(self, pres_ctx):
		p = Html(*(['<select>'] + self.__options + ['</select>'])).js_function_call('larch.controls.initSelect')
		p = p.with_event_handler('select_choose', lambda event: self.choose(event, event.data))
		p = p.use_js('/files/static/larch/larch_ui.js').use_css('/files/static/larch/larch_ui.css')
		return p
