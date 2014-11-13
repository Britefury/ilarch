##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch import js
from larch.core.dynamicpage import segment, page, event
from larch.core import incremental_view
from larch.default_perspective import DefaultPerspective



_popup_id_js = js.JSName('popup_id')
_nodes_js = js.JSName('nodes')



class Popup (object):
	def __init__(self, popup_contents, show_on_target):
		self.__popup_contents = popup_contents

		if isinstance(show_on_target, event.Event):
			fragment = show_on_target.fragment
			self.__inc_view = fragment.view   if fragment is not None   else show_on_target.page._page.inc_view
			self.__perspective = fragment.perspective
		elif isinstance(show_on_target, page.DynamicPage):
			self.__inc_view = show_on_target.inc_view
			self.__perspective = DefaultPerspective.instance
		elif isinstance(show_on_target, page.DynamicPagePublicAPI):
			self.__inc_view = show_on_target._page.inc_view
			self.__perspective = DefaultPerspective.instance
		elif isinstance(show_on_target, incremental_view._FragmentView):
			self.__inc_view = show_on_target.view
			self.__perspective = show_on_target.perspective
		elif isinstance(show_on_target, incremental_view.IncrementalView):
			self.__inc_view = show_on_target
			self.__perspective = DefaultPerspective.instance
		elif isinstance(show_on_target, segment.DynamicSegment):
			self.__inc_view = show_on_target.page.inc_view
			self.__perspective = show_on_target.fragment.perspective
		else:
			raise TypeError, 'Cannot show popup over type {0}'.format(type(show_on_target))


	def show_using_js_eval(self, js_expr):
		"""
		Show the popup using a supplied Javascript expression

		:param js_expr: a javascript expression to be evaluated. The variables popup_id and nodes will be available in the local scope, providing the ID of the popup and the DOM nodes that it is to contain.
		:return: the segment ID of the popup
		"""
		if isinstance(js_expr, basestring):
			js_expr = js.JSExprSrc(js_expr)
		elif not isinstance(js_expr, js.JS):
			raise TypeError, 'Javascript expression must be a string or a JS object'
		seg = self.__inc_view.create_popup_segment(self.__popup_contents, self.__perspective, js_expr)
		return seg.id


	def show_using_js_function_call(self, js_fn_name, *args):
		"""
		Show the popup using a javascript function call

		:param js_fn_name: the name of the Javscript function to call. It will be passed two arguments; the popup ID and the nodes that the popup is to contain
		:param args: subsequent arguments to supply to the popup show function
		:return:
		"""
		return self.show_using_js_eval( js.JSCall(js_fn_name, (_popup_id_js, _nodes_js,) + args))


	@staticmethod
	def coerce_target_to_segment(target):
		if isinstance(target, event.Event):
			return target.segment
		elif isinstance(target, segment.DynamicSegment):
			return target
		else:
			raise TypeError, 'Cannot coerce {0} to segment'.format(type(target))






