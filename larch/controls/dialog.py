##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch import js
from larch.pres import pres, popup


_js_createDialog = js.JSName('larch.controls.createDialog')


class dialog (object):
	def __init__(self, contents, **options):
		self.__contents = pres.Pres.coerce(contents).use_js('/files/static/larch/larch_ui.js').use_css('/files/static/larch/larch_ui.css')
		self.__options = options


	def show_on(self, target):
		p = popup.Popup(self.__contents, target)
		p.show_using_js_function_call(_js_createDialog, self.__options)


	@staticmethod
	def close_containing_dialog(target):
		seg = popup.Popup.coerce_target_to_segment(target)
		seg.queue_script_function_call('larch.controls.closeContainingDialog')
