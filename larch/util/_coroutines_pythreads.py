##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************

import threading



class CoroutineExit (Exception):
	pass


class CoroutineBase (object):
	_current_coroutine = None

	def __init__(self, name, parent):
		self.__lock = threading.Semaphore(0)
		self.__value_lock = threading.Lock()
		self.__value = None
		self.__name = name
		self.__parent = parent
		self.__raise_on_resume = None


	@property
	def run(self):
		raise NotImplementedError, 'abstract'

	@property
	def parent(self):
		return self.__parent

	@property
	def dead(self):
		raise NotImplementedError, 'abstract'

	def __bool__(self):
		raise NotImplementedError, 'abstract'

	def __nonzero__(self):
		raise NotImplementedError, 'abstract'

	@property
	def name(self):
		return self.__name




	def switch(self, *args, **kwargs):
		"""
		Yield to this co-routine; call this method from within the source co-routine

		:param value:  [optional] value to pass to this coroutine
		:return: value passed from this co-routine that yields back to the source co-routine
		"""
		source = CoroutineBase._current_coroutine
		assert isinstance(source, CoroutineBase)

		if self.dead:
			# Finished; nothing to do
			return None
		else:
			# CONTEXT:
			# self = the target coroutine
			# source = the source coroutine; THE ONE IN WHICH WE ARE RUNNING RIGHT NOW

			# Ensure that the target co-routine has been initialised/started
			self._initialise()

			# Send value to the target co-routine
			self.__set_value((args, kwargs))

			# Set the current co-routine
			CoroutineBase._current_coroutine = self

			# Resume the target co-routine
			self._resume()

			# Halt the source co-routine
			source._halt()

			# CONTEXT
			# source._halt() has returned:
			# The source co-routine has resumed and now has control

			# The _halt() method has returned; the source co-routine has been resumed: check if an exception needs to be baised
			exc_to_throw = source._get_exception_to_throw()
			if exc_to_throw is not None:
				# Raise the exception
				if exc_to_throw[1] is not None:
					raise exc_to_throw[0], exc_to_throw[1]
				else:
					raise exc_to_throw[0]

			# Retrieve any exception that is to be passed up
			t = source._consume_exception_to_throw_on_resume()
			if t is not None:
				raise t

			# Return the value within the source co-routine
			v = source._get_value()
			if v is None:
				return None
			else:
				a, k = v
				if len(a) == 1  and  len(k) == 0:
					return a[0]
				else:
					return a, k



	def throw(self, typ, val=None):
		raise NotImplementedError, 'abstract'


	@staticmethod
	def _co_finish(c, value, caught_exception):
		if c is not getcurrent():
			raise RuntimeError, 'Finishing non-current co-routine {0}, current is {1} (thread={2})'.format(c, CoroutineBase._current_coroutine, threading.current_thread())

		# Switch to the parent co-routine
		new_current = c.__parent
		if new_current is None:
			raise RuntimeError, '_co_finish: c has no parent'

		# Resume it; this thread will continue to run and terminate
		new_current.__set_value(((value,), {}))
		new_current._raise_on_resume(caught_exception)
		CoroutineBase._current_coroutine = new_current
		new_current._resume()


	def _raise_on_resume(self, exc):
		self.__raise_on_resume = exc

	def _consume_exception_to_throw_on_resume(self):
		t = self.__raise_on_resume
		self.__raise_on_resume = None
		return t


	def _initialise(self):
		raise NotImplementedError, 'abstract'

	def _is_root(self):
		raise NotImplementedError, 'abstract'


	def _get_exception_to_throw(self):
		raise NotImplementedError, 'abstract'


	def _halt(self):
		self.__lock.acquire()

	def _resume(self):
		self.__lock.release()



	def _get_value(self):
		self.__value_lock.acquire()
		v = self.__value
		self.__value_lock.release()
		return v

	def __set_value(self, args_and_kwargs):
		self.__value_lock.acquire()
		self.__value = args_and_kwargs
		self.__value_lock.release()



def getcurrent():
	return CoroutineBase._current_coroutine

def terminate(co):
	co.throw(CoroutineExit)






class Coroutine (CoroutineBase):
	def __init__(self, function, parent=None, name=None):
		if parent is None:
			parent = getcurrent()
		super(Coroutine, self).__init__(name, parent)
		self.__function = function
		self.__running = False
		self.__dead = False
		self.__exception_to_throw = None
		self.__thread = None


	@property
	def run(self):
		return self.__function

	@property
	def dead(self):
		return self.__dead

	def __bool__(self):
		return self.__running

	def __nonzero__(self):
		return self.__running



	def throw(self, typ, val=None):
		if not self.__dead  and  self.__running:
			# Set the exception fields and resume
			self.__exception_to_throw = typ, val
			self.switch()


	def __run(self):
		# Wait until this co-routine is yielded to
		self._halt()

		caught_exception = None

		v = self._get_value()

		# Do the work
		try:
			if v is None:
				self.__function()
			else:
				a, kw = v
				v = self.__function(*a, **kw)
		except CoroutineExit, e:
			pass
		except Exception, e:
			caught_exception = e

		self.__exception_to_throw = None

		# We are done; clear up
		self.__dead = True
		self.__running = False
		CoroutineBase._co_finish(self, v, caught_exception)

		# Null the thread; no longer running
		self.__thread = None


	def _initialise(self):
		if self.__thread is None:
			self.__thread = threading.Thread(target=self.__run)
			self.__running = True
			self.__thread.start()

	def _is_root(self):
		return False

	def _get_exception_to_throw(self):
		return self.__exception_to_throw


	def __str__(self):
		return 'Coroutine({0}, id={1}, thread={2})'.format(self.name, id(self), self.__thread)

	def __repr__(self):
		return 'Coroutine({0}, id={1}, thread={2})'.format(self.name, id(self), self.__thread)




def coroutine(f):
	return Coroutine(f, None, f.__name__)





class RootCoroutine (CoroutineBase):
	def __init__(self):
		super(RootCoroutine, self).__init__('<root>', None)
		self.__thread = threading.current_thread()
		CoroutineBase._current_coroutine = self


	@property
	def run(self):
		return None

	@property
	def dead(self):
		return False

	def __bool__(self):
		return True

	def __nonzero__(self):
		return True



	def throw(self, typ, val=None):
		raise TypeError, 'Cannot throw exceptions on root co-routine'


	def _initialise(self):
		pass

	def _is_root(self):
		return True

	def _get_exception_to_throw(self):
		return None


	def __str__(self):
		return 'RootCoroutine({0}, id={1}, thread={2})'.format(self.name, id(self), self.__thread)

	def __repr__(self):
		return 'RootCoroutine({0}, id={1}, thread={2})'.format(self.name, id(self), self.__thread)




RootCoroutine._root = RootCoroutine()


import unittest
import time

class TestCoroutine (unittest.TestCase):
	def test_empty_coroutine(self):
		@coroutine
		def empty():
			pass

		empty.switch()


	def test_parent(self):
		@coroutine
		def empty():
			pass

		empty.switch()

		self.assertIs(RootCoroutine._root, empty.parent)
		self.assertIs(RootCoroutine._root, getcurrent())


	def test_simple_argument_passing(self):
		@coroutine
		def a(x):
			self.assertEqual(x, 1)
			x = a.parent.switch(42)
			self.assertEqual(x, 'hello')
			return 101

		x = a.switch(1)
		self.assertEqual(x, 42)
		x = a.switch('hello')
		self.assertEqual(x, 101)



	def test_argument_passing(self):
		@coroutine
		def a(*args, **kwargs):
			self.assertEqual(args, (1,))
			self.assertEqual(kwargs, {'b': 2})
			args, kwargs = a.parent.switch(3.141, e=2.71828)
			self.assertEqual(args, (0.707,))
			self.assertEqual(kwargs, {'s2': 1.414})

		args, kwargs = a.switch(1, b=2)
		self.assertEqual(args, (3.141,))
		self.assertEqual(kwargs, {'e': 2.71828})
		x = a.switch(0.707, s2=1.414)
		self.assertIsNone(x)



	def test_exception_catching(self):
		@coroutine
		def raiser():
			raise NotImplementedError

		caught = False
		try:
			raiser.switch()
		except NotImplementedError:
			caught = True

		self.assertTrue(caught)

		self.assertIs(RootCoroutine._root, raiser.parent)
		self.assertIs(RootCoroutine._root, getcurrent())


	# def test_unfinished_coroutine(self):
	# 	def f():
	# 		getcurrent().parent.switch()
	#
	# 	co = Coroutine(f, 'unfinished')
	# 	co.switch()


	def test_throw(self):
		x = [0]

		@coroutine
		def throw():
			x[0] = 1
			getcurrent().parent.switch()
			x[0] = 2

		self.assertFalse(bool(throw))
		self.assertFalse(throw.dead)
		self.assertEqual(x[0], 0)

		throw.switch()

		self.assertTrue(throw)
		self.assertFalse(throw.dead)
		self.assertEqual(x[0], 1)

		try:
			throw.throw(ValueError, 1)
		except ValueError, x:
			self.assertEqual(x.args, (1,))
		else:
			self.fail()

		self.assertEqual(x[0], 1)
		self.assertTrue(throw.dead)


	def test_throw_exit(self):
		x = [0]

		@coroutine
		def throw():
			x[0] = 1
			getcurrent().parent.switch()
			x[0] = 2

		self.assertFalse(bool(throw))
		self.assertFalse(throw.dead)
		self.assertEqual(x[0], 0)

		throw.switch()

		self.assertTrue(throw)
		self.assertFalse(throw.dead)
		self.assertEqual(x[0], 1)

		throw.throw(CoroutineExit)

		self.assertEqual(x[0], 1)
		self.assertTrue(throw.dead)


	def test_serial_coroutines(self):
		@coroutine
		def co1():
			getcurrent().parent.switch()
			getcurrent().parent.switch()

		co1.switch()
		co1.switch()
		co1.switch()

		@coroutine
		def co2():
			getcurrent().parent.switch()
			getcurrent().parent.switch()

		co2.switch()
		co2.switch()
		co2.switch()


	def test_flow_of_three_coroutines(self):
		x = []

		@coroutine
		def co_a():
			x.append('a')
			co_b.switch()
			x.append('e')
			co_c.switch()
			x.append('g')

		@coroutine
		def co_b():
			x.append('b')
			co_c.switch()
			x.append('d')
			co_a.switch()

		@coroutine
		def co_c():
			x.append('c')
			co_b.switch()
			x.append('f')
			co_a.switch()

		self.assertEqual(x, [])
		self.assertFalse(co_a)
		self.assertFalse(co_b)
		self.assertFalse(co_c)

		co_a.switch()
		self.assertEqual(x, ['a', 'b', 'c', 'd', 'e', 'f', 'g'])
		self.assertFalse(co_a)
		self.assertTrue(co_b)
		self.assertTrue(co_c)
		self.assertTrue(co_a.dead)
		self.assertFalse(co_b.dead)
		self.assertFalse(co_c.dead)

		co_b.switch()
		self.assertTrue(co_a.dead)
		self.assertTrue(co_b.dead)
		self.assertFalse(co_c.dead)

		co_c.switch()
		self.assertTrue(co_a.dead)
		self.assertTrue(co_b.dead)
		self.assertTrue(co_c.dead)


	def test_flow_of_three_coroutines_with_value_passing(self):
		p = []

		@coroutine
		def co_a(x):
			self.assertEqual(x, '0')
			p.append('a')
			x = co_b.switch('1')
			self.assertEqual(x, '2')
			p.append('e')
			x = co_a.parent.switch('1')
			self.assertEqual(x, '2')
			p.append('i')
			x = co_b.switch('1')
			self.assertEqual(x, '0')

		@coroutine
		def co_b(x):
			self.assertEqual(x, '1')
			p.append('b')
			x = co_c.switch('2')
			self.assertEqual(x, '3')
			p.append('d')
			x = co_a.switch('2')
			self.assertEqual(x, '3')
			p.append('h')
			x = co_a.switch('2')
			self.assertEqual(x, '1')
			p.append('j')
			x = co_c.switch('2')
			self.assertEqual(x, '0')

		@coroutine
		def co_c(x):
			self.assertEqual(x, '2')
			p.append('c')
			x = co_b.switch('3')
			self.assertEqual(x, '0')
			p.append('g')
			x = co_b.switch('3')
			self.assertEqual(x, '2')
			p.append('k')

		x = co_a.switch('0')
		self.assertEqual(x, '1')
		p.append('f')

		self.assertTrue(co_a)
		self.assertTrue(co_b)
		self.assertTrue(co_c)
		self.assertFalse(co_a.dead)
		self.assertFalse(co_b.dead)
		self.assertFalse(co_c.dead)

		x = co_c.switch('0')
		self.assertEqual(x, None)
		p.append('l')

		self.assertEqual(p, ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l'])
		self.assertTrue(co_a)
		self.assertTrue(co_b)
		self.assertFalse(co_c)
		self.assertFalse(co_a.dead)
		self.assertFalse(co_b.dead)
		self.assertTrue(co_c.dead)

		x = co_a.switch('0')
		self.assertEqual(x, None)

		self.assertTrue(co_a.dead)
		self.assertFalse(co_b.dead)
		self.assertTrue(co_c.dead)

		x = co_b.switch('0')
		self.assertEqual(x, None)

		self.assertTrue(co_a.dead)
		self.assertTrue(co_b.dead)
		self.assertTrue(co_c.dead)


if __name__ == '__main__':
	unittest.main()