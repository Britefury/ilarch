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


class slider (CompositePres):
	def __init__(self, release_fn=None, slide_fn=None, width=None, value=None, min=None, max=None, step=None,
		     orientation=None, animate=False, disabled=False):
		"""
		Create a JQuery UI slider

		:param release_fn: a function to be invoked when the user releases the slider, of the form function(event, value)
		:param slide_fn: a function to be invoked when the user drags the slider, of the form function(event, value)
		:param width: the width of the slider, specified as a CSS value e.g. 200px (200 pixels) or 50%, or as an integer value that will be converted to pixels
		:param value: the initial value
		:param min: the minimum value
		:param max: the maximum value
		:param step: the size of steps between positions on the slider
		:param orientation: either 'horizontal' or 'vertical'
		:param animate: if True, or if a numeric value in milliseconds specifying the animation length, this will cause the slider to animate when the user clicks to position it directly
		:param disabled: if True, causes the slider to appear disabled
		:return: the slider control
		"""
		self.release = EventHandler()
		self.slide = EventHandler()
		if release_fn is not None:
			self.release.connect(release_fn)
		if slide_fn is not None:
			self.slide.connect(slide_fn)
		self.__channel = MessageChannel()

		self.__width = '{0}px'.format(width) if isinstance(width, int) or isinstance(width, long)   else width

		options = {}
		if value is not None:
			options['value'] = value
		if min is not None:
			options['min'] = min
		if max is not None:
			options['max'] = max
		if step is not None:
			options['step'] = step
		if orientation is not None:
			options['orientation'] = orientation
		if animate is not False:
			options['animate'] = animate
		if disabled:
			options['disabled'] = True

		self.__options = options


	def set_value(self, value):
		self.__channel.send(value)


	def pres(self, pres_ctx):
		if self.__width is None:
			div = Html('<div></div>')
		else:
			div = Html('<div style="width: {0};"></div>'.format(self.__width))
		div = div.js_function_call('larch.controls.initSlider', True, self.__options, self.__channel)
		div = div.with_event_handler("slider_change", lambda event: self.release(event, event.data))
		div = div.with_event_handler("slider_slide", lambda event: self.slide(event, event.data))
		div = div.use_js('/files/static/larch/larch_ui.js').use_css('/files/static/larch/larch_ui.css')
		return div



class range_slider (CompositePres):
	def __init__(self, release_fn=None, slide_fn=None, width=None, values=None, min=None, max=None, step=None,
		 orientation=None, animate=False, disabled=False):
		"""
		Create a JQuery UI slider - with the range option enabled

		:param release_fn: a function to be invoked when the user releases the slider, of the form function(event, value)
		:param slide_fn: a function to be invoked when the user drags the slider, of the form function(event, value)
		:param width: the width of the slider, specified as a CSS value e.g. 200px (200 pixels) or 50%, or as an integer value that will be converted to pixels
		:param values: a pair of values representing the lower and upper bound
		:param min: the minimum value
		:param max: the maximum value
		:param step: the size of steps between positions on the slider
		:param orientation: either 'horizontal' or 'vertical'
		:param animate: if True, or if a numeric value in milliseconds specifying the animation length, this will cause the slider to animate when the user clicks to position it directly
		:param disabled: if True, causes the slider to appear disabled
		:return: the slider control
		"""

		self.release = EventHandler()
		self.slide = EventHandler()
		if release_fn is not None:
			self.release.connect(release_fn)
		if slide_fn is not None:
			self.slide.connect(slide_fn)
		self.__channel = MessageChannel()

		self.__width = '{0}px'.format(width) if isinstance(width, int) or isinstance(width, long)   else width

		options = {}
		if values is not None:
			options['values'] = values
		options['range'] = True
		if min is not None:
			options['min'] = min
		if max is not None:
			options['max'] = max
		if step is not None:
			options['step'] = step
		if orientation is not None:
			options['orientation'] = orientation
		if animate is not False:
			options['animate'] = animate
		if disabled:
			options['disabled'] = True
		self.__options = options


	def set_values(self, values):
		self.__channel.send(values)


	def pres(self, pres_ctx):
		if self.__width is None:
			div = Html('<div></div>')
		else:
			div = Html('<div style="width: {0};"></div>'.format(self.__width))
		div = div.js_function_call('larch.controls.initRangeSlider', True, self.__options, self.__channel)
		div = div.with_event_handler("slider_change", lambda event: self.release(event, event.data))
		div = div.with_event_handler("slider_slide", lambda event: self.slide(event, event.data))
		div = div.use_js('/files/static/larch/larch_ui.js').use_css('/files/static/larch/larch_ui.css')
		return div



class live_slider (CompositePres):
	def __init__(self, live, update_on_slide=False, width=None, min=None, max=None, step=None, orientation=None, animate=False,
		disabled=False):
		"""
		Create a JQuery UI slider that edits a live value

		:param live: the live value to edit
		:param update_on_slide: if True, the live value is updated in response to the user dragging, otherwise it only updates when the user lets the slider go
		:param width: the width of the slider, specified as a CSS value e.g. 200px (200 pixels) or 50%, or as an integer value that will be converted to pixels
		:param min: the minimum value
		:param max: the maximum value
		:param step: the size of steps between positions on the slider
		:param orientation: either 'horizontal' or 'vertical'
		:param animate: if True, or if a numeric value in milliseconds specifying the animation length, this will cause the slider to animate when the user clicks to position it directly
		:param disabled: if True, causes the slider to appear disabled
		:return: the slider control
		"""
		self.__live = live
		self.__update_on_slide = update_on_slide
		self.__width = width
		self.__min = min
		self.__max = max
		self.__step = step
		self.__orientation = orientation
		self.__animate = animate
		self.__disabled = disabled


	def pres(self, pres_ctx):
		refreshing = [False]

		def set_value():
			s.set_value(self.__live.value)

		def on_live_change(incr):
			if not refreshing[0]:
				pres_ctx.fragment_view.queue_task(set_value)

		def __on_slide(event, value):
			refreshing[0] = True
			self.__live.value = value
			refreshing[0] = False

		self.__live.add_listener(on_live_change)

		slide_fn = __on_slide if self.__update_on_slide   else None
		s = slider(__on_slide, slide_fn, self.__width, value=self.__live.static_value, min=self.__min, max=self.__max, step=self.__step,
			      orientation=self.__orientation, animate=self.__animate, disabled=self.__disabled)
		return s



class live_range_slider(CompositePres):
	def __init__(self, live, update_on_slide=False, width=None, min=None, max=None, step=None, orientation=None,
		      animate=False, disabled=False):
		"""
		Create a JQuery UI range slider that edits a live value

		:param live: the live value to edit
		:param update_on_slide: if True, the live value is updated in response to the user dragging, otherwise it only updates when the user lets the slider go
		:param width: the width of the slider, specified as a CSS value e.g. 200px (200 pixels) or 50%, or as an integer value that will be converted to pixels
		:param min: the minimum value
		:param max: the maximum value
		:param step: the size of steps between positions on the slider
		:param orientation: either 'horizontal' or 'vertical'
		:param animate: if True, or if a numeric value in milliseconds specifying the animation length, this will cause the slider to animate when the user clicks to position it directly
		:param disabled: if True, causes the slider to appear disabled
		:return: the slider control
		"""
		self.__live = live
		self.__update_on_slide = update_on_slide
		self.__width = width
		self.__min = min
		self.__max = max
		self.__step = step
		self.__orientation = orientation
		self.__animate = animate
		self.__disabled = disabled


	def pres(self, pres_ctx):
		refreshing = [False]

		def set_value():
			s.set_values(self.__live.value)

		def on_live_change(incr):
			if not refreshing[0]:
				pres_ctx.fragment_view.queue_task(set_value)

		def __on_slide(event, value):
			refreshing[0] = True
			self.__live.value = value
			refreshing[0] = False

		self.__live.add_listener(on_live_change)


		slide_fn = __on_slide if self.__update_on_slide   else None
		s = range_slider(__on_slide, slide_fn, self.__width, values=self.__live.static_value, min=self.__min, max=self.__max, step=self.__step,
				    orientation=self.__orientation, animate=self.__animate, disabled=self.__disabled)
		return s
