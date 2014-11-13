##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch.util import coroutines


class AsyncApp (object):
	_app_stack = []

	def __init__(self, f, *args,** kwargs):
		self.__f = f
		self.__args = args
		self.__kwargs = kwargs
		self.__outer_co = None
		self.__co = None


	def go(self):
		self.__outer_co = coroutines.getcurrent()
		self.__co = coroutines.coroutine(self.__f)

		self._app_stack.append(self)
		self.__co.switch(*self.__args, **self.__kwargs)
		self._app_stack.pop()


	def _enter_app(self, event):
		self.__co.switch(event)

	def _leave_app(self):
		return self.__outer_co.switch()


	@classmethod
	def getcurrent(cls):
		return cls._app_stack[-1]   if len(cls._app_stack) > 0   else None




class EventHandler (object):
	def __init__(self):
		self._listeners = []
		self._children = []


	def connect(self, listener):
		self._notify_hook()
		self._listeners.append(listener)

	def disconnect(self, listener):
		self._listeners.remove(listener)
		self._notify_unhook()


	def __call__(self, event, *args, **kwargs):
		# Iterate over a copy
		for child in self._children[:]:
			if child(event, *args, **kwargs):
				return True

		for listener in self._listeners[:]:
			if listener(event, *args, **kwargs):
				return True


	def await(self):
		def handler(event):
			self.disconnect(handler)
			app._enter_app(event)


		app = AsyncApp.getcurrent()
		if app is None:
			raise RuntimeError, 'Cannot perform async wait; no async app is running'

		self.connect(handler)
		return app._leave_app()


	def _add_child(self, child):
		self._notify_hook()
		self._children.append(child)

	def _remove_child(self, child):
		self._children.remove(child)
		self._notify_unhook()


	def _has_output(self):
		return len(self._listeners) > 0  or  len(self._children) > 0



	def _notify_hook(self):
		pass

	def _notify_unhook(self):
		pass


	def filter(self, name_or_function):
		if isinstance(name_or_function, basestring):
			return EventHandlerFilterByName(self, name_or_function)
		else:
			return EventHandlerFilterByFunction(self, name_or_function)

	def apply(self, function):
		return EventHandlerApply(self, function)

	def join(self, event_handler):
		return EventHandlerJoin([self, event_handler])

	def __or__(self, event_handler):
		return self.join(event_handler)


class _EventHandlerNode (EventHandler):
	def __init__(self, parents):
		super(_EventHandlerNode, self).__init__()
		self._parents = parents


	def _notify_hook(self):
		if not self._has_output():
			for parent in self._parents:
				parent._add_child(self)

	def _notify_unhook(self):
		if not self._has_output():
			for parent in self._parents:
				parent._remove_child(self)



class EventHandlerFilterByName (_EventHandlerNode):
	def __init__(self, parent, name):
		super(EventHandlerFilterByName, self).__init__([parent])
		self.__name = name


	def __call__(self, event):
		if event.name == self.__name:
			return super(EventHandlerFilterByName, self).__call__(event)
		else:
			return False


class EventHandlerFilterByFunction (_EventHandlerNode):
	def __init__(self, parent, filter_fn):
		super(EventHandlerFilterByFunction, self).__init__([parent])
		self.__filter_fn = filter_fn

	def __call__(self, event):
		if self.__filter_fn(event):
			return super(EventHandlerFilterByFunction, self).__call__(event)
		else:
			return False



class EventHandlerApply (_EventHandlerNode):
	def __init__(self, parent, apply_fn):
		super(EventHandlerApply, self).__init__([parent])
		self.__apply_fn = apply_fn

	def __call__(self, event):
		return super(EventHandlerApply, self).__call__(self.__apply_fn(event))


class EventHandlerJoin (_EventHandlerNode):
	def join(self, event_handler):
		return EventHandlerJoin(self._parents + [event_handler])




import unittest

class TestCaseEventHandler (unittest.TestCase):
	class _Event (object):
		def __init__(self, name, x):
			self.name = name
			self.x = x

	def test_connect_disconnect_invoke(self):
		aa = [None]
		bb = [None]

		def a(x):
			aa[0] = x

		def b(x):
			bb[0] = x

		h = EventHandler()
		self.assertEqual(None, aa[0])
		self.assertEqual(None, bb[0])

		h(1)
		self.assertEqual(None, aa[0])
		self.assertEqual(None, bb[0])

		h.connect(a)
		h(1)
		self.assertEqual(1, aa[0])
		self.assertEqual(None, bb[0])

		h.connect(b)
		h(2)
		self.assertEqual(2, aa[0])
		self.assertEqual(2, bb[0])

		h.disconnect(a)
		h(3)
		self.assertEqual(2, aa[0])
		self.assertEqual(3, bb[0])

		h.disconnect(b)
		h(4)
		self.assertEqual(2, aa[0])
		self.assertEqual(3, bb[0])


	def test_children(self):
		aa = [None]
		bb = [None]

		def a(x):
			aa[0] = x

		def b(x):
			bb[0] = x

		h1 = EventHandler()
		h2 = EventHandlerJoin([h1])

		self.assertEqual(None, aa[0])
		self.assertEqual(None, bb[0])

		h1(1)
		self.assertEqual(None, aa[0])
		self.assertEqual(None, bb[0])

		h1.connect(a)
		h1(1)
		self.assertEqual(1, aa[0])
		self.assertEqual(None, bb[0])

		h2.connect(b)
		h1(2)
		self.assertEqual(2, aa[0])
		self.assertEqual(2, bb[0])


	def test_flow(self):
		def f(x):
			pass

		h1 = EventHandler()
		self.assertFalse(h1._has_output())

		h1.connect(f)
		self.assertTrue(h1._has_output())

		h1.disconnect(f)
		self.assertFalse(h1._has_output())

		h2 = EventHandlerJoin([h1])
		self.assertEqual([h1], h2._parents)
		self.assertEqual([], h1._children)
		self.assertFalse(h1._has_output())
		self.assertFalse(h2._has_output())

		h2.connect(f)
		self.assertEqual([h1], h2._parents)
		self.assertEqual([h2], h1._children)
		self.assertTrue(h1._has_output())
		self.assertTrue(h2._has_output())

		h2.disconnect(f)
		self.assertEqual([h1], h2._parents)
		self.assertEqual([], h1._children)
		self.assertFalse(h1._has_output())
		self.assertFalse(h2._has_output())



	def test_filter_by_name(self):
		aa = [None]

		def a(ev):
			aa[0] = ev.x


		h1 = EventHandler()
		h2 = h1.filter('b')
		h2.connect(a)
		self.assertEqual(None, aa[0])

		h1(self._Event('a', 1))
		self.assertEqual(None, aa[0])

		h1(self._Event('b', 2))
		self.assertEqual(2, aa[0])



	def test_filter_by_function(self):
		aa = [None]

		def a(ev):
			aa[0] = ev.x

		h1 = EventHandler()
		h2 = h1.filter(lambda ev: (ev.x % 2) == 0)
		h2.connect(a)
		self.assertEqual(None, aa[0])

		h1(self._Event('a', 1))
		self.assertEqual(None, aa[0])

		h1(self._Event('b', 2))
		self.assertEqual(2, aa[0])


	def test_apply(self):
		aa = [None]

		def a(ev):
			aa[0] = ev.x

		h1 = EventHandler()
		h2 = h1.apply(lambda ev: self._Event(ev.name, ev.x * 2))
		h2.connect(a)
		self.assertEqual(None, aa[0])

		h1(self._Event('a', 1))
		self.assertEqual(2, aa[0])

		h1(self._Event('b', 3))
		self.assertEqual(6, aa[0])


	def test_join(self):
		aa = [None]

		def a(ev):
			aa[0] = ev.x

		h1 = EventHandler()
		h2 = EventHandler()
		h3 = EventHandler()
		hh = h1 | h2 | h3
		hh.connect(a)
		self.assertEqual(None, aa[0])

		h1(self._Event('a', 1))
		self.assertEqual(1, aa[0])

		h2(self._Event('a', 2))
		self.assertEqual(2, aa[0])

		h3(self._Event('a', 3))
		self.assertEqual(3, aa[0])
