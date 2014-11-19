##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch.pres.pres import post_event_js_code_for_handler, CompositePres
from larch.pres.html import Html
from larch.event_handler import EventHandler


class action_link (CompositePres):
	def __init__(self, link_text, action_fn=None, css_class=None):
		"""
		Create an action link that invokes a function in response to the user clicking it
		:param link_text: the link text
		:param action_fn:  a callback that is called when the link is clicked, of the form function(event)
		:param css_class: an optional css class
		:return: the control
		"""
		self.__link_text = link_text
		self.clicked = EventHandler()
		if action_fn is not None:
			self.clicked.connect(action_fn)
		self.__css_class = css_class

	def pres(self, pres_ctx):
		css = ' class="{0}"'.format(self.__css_class)   if self.__css_class is not None   else ''
		p = Html('<a {2}href="javascript:" onclick="{0}">{1}</a>'.format(post_event_js_code_for_handler('clicked'), self.__link_text, css))
		p = p.with_event_handler('clicked', self.clicked)
		return p
