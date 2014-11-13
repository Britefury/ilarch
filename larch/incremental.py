##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
import weakref
import unittest
import gc



class IncrementalEvaluationCycleError (Exception):
	pass



class IncrementalMonitor (object):
	UNINITIALISED = 'UNINITIALISED'
	REFRESH_REQUIRED = 'REFRESH_REQUIRED'
	REFRESH_NOT_REQUIRED = 'REFRESH_NOT_REQUIRED'


	_current_computation = None


	def __init__(self, owner=None):
		self._owner = owner
		self._incremental_state = IncrementalMonitor.UNINITIALISED
		self._outgoing_dependencies = None
		self._listeners = None



	owner = property(lambda self: self._owner)
	has_listeners = property(lambda self: (self._listeners is not None  and  len(self._listeners) > 0))
	outgoing_dependences = property(lambda self: (set(self._outgoing_dependencies.keys())   if self._outgoing_dependencies is not None   else set()))
	has_outgoing_dependences = property(lambda self: (self._outgoing_dependencies is not None  and  len(self._outgoing_dependencies) > 0))



	def add_listener(self, listener):
		if self._listeners is None:
			self._listeners = []
		if listener in self._listeners:
			return
		self._listeners.append(listener)

	def remove_listener(self, listener):
		if self._listeners is not None:
			try:
				self._listeners.remove(listener)
			except ValueError:
				pass



	def _on_value_access(self):
		if IncrementalMonitor._current_computation is not None:
			IncrementalMonitor._current_computation._on_incoming_dependency_access(self)

	def _notify_changed(self):
		if self._incremental_state != IncrementalMonitor.REFRESH_REQUIRED:
			self._incremental_state = IncrementalMonitor.REFRESH_REQUIRED
			self._emit_changed()

			if self._outgoing_dependencies is not None:
				for dep in self._outgoing_dependencies.keys():
					dep._notify_changed()

	def _notify_refreshed(self):
		self._incremental_state = IncrementalMonitor.REFRESH_NOT_REQUIRED


	def _emit_changed(self):
		if self._listeners is not None:
			for listener in self._listeners:
				listener(self)


	@staticmethod
	def _push_current_computation(computation):
		f = IncrementalMonitor._current_computation
		IncrementalMonitor._current_computation = computation
		return f

	@staticmethod
	def _pop_current_computation(prev_computation):
		IncrementalMonitor._current_computation = prev_computation



	@staticmethod
	def block_access_tracking():
		return IncrementalMonitor._push_current_computation(None)

	@staticmethod
	def unblock_access_tracking(prev_computation):
		IncrementalMonitor._pop_current_computation(prev_computation)



	def _add_outgoing_dependency(self, dep):
		if self._outgoing_dependencies is None:
			self._outgoing_dependencies = weakref.WeakKeyDictionary()
		self._outgoing_dependencies[dep] = None

	def _remove_outgoing_dependency(self, dep):
		if self._outgoing_dependencies is not None:
			del self._outgoing_dependencies[dep]
			if len(self._outgoing_dependencies) == 0:
				self._outgoing_dependencies = None
		else:
			raise KeyError






class IncrementalValueMonitor (IncrementalMonitor):
	def on_access(self):
		self._notify_refreshed()
		self._on_value_access()

	def on_changed(self):
		self._notify_changed()





class IncrementalFunctionMonitor (IncrementalMonitor):
	""" Incremental Function Monitor

	Monitor a value acquired by evaluating a function.

	When acquiring the value:
		def get_value():
			try:
				refresh_value()
			finally:
				inc_fn_mon.on_access()
			return value_cache


		def refresh_value():
			refresh_state = inc_fn_mon.on_refresh_begin()
			try:
				if refresh_state is not None:
					value_cache = evaluate_function()
			finally:
				inc_fn_mon.on_refresh_end(refresh_state)
	"""
	_FLAG_CYCLE_LOCK = 0x1
	_FLAG_BLOCK_INCOMING_DEPENDENCIES = 0x2

	def __init__(self, owner=None):
		super(IncrementalFunctionMonitor, self).__init__(owner)
		self._incoming_dependencies = None
		self.__flags = 0


	incoming_dependencies = property(lambda self: (self._incoming_dependencies   if self._incoming_dependencies is not None   else set()))


	def on_access(self):
		self._on_value_access()

	def on_changed(self):
		self._notify_changed()

	def block_and_clear_incoming_dependencies(self):
		self.__set_flag(self._FLAG_BLOCK_INCOMING_DEPENDENCIES)
		self._incoming_dependencies = None


	def on_refresh_begin(self):
		if self.__test_flag(self._FLAG_CYCLE_LOCK):
			raise IncrementalEvaluationCycleError

		self.__clear_flag(self._FLAG_BLOCK_INCOMING_DEPENDENCIES)
		self.__set_flag(self._FLAG_CYCLE_LOCK)

		if self._incremental_state != IncrementalMonitor.REFRESH_NOT_REQUIRED:
			# Push current computation
			old_computation = IncrementalMonitor._push_current_computation(self)

			refresh_state = old_computation, self._incoming_dependencies
			self._incoming_dependencies = None
			return refresh_state
		else:
			return None


	def on_refresh_end(self, refresh_state):
		if self._incremental_state != IncrementalMonitor.REFRESH_NOT_REQUIRED:
			old_computation, prev_incoming_dependencies = refresh_state

			# Restore current computation
			IncrementalMonitor._pop_current_computation(old_computation)

			# Disconnect the dependencies that are being removed
			if prev_incoming_dependencies is not None:
				for inc in prev_incoming_dependencies:
					if self._incoming_dependencies is None  or  inc not in self._incoming_dependencies:
						inc._remove_outgoing_dependency(self)

			# Connect new dependencies
			if self._incoming_dependencies is not None:
				for inc in self._incoming_dependencies:
					if prev_incoming_dependencies is None  or  inc not in prev_incoming_dependencies:
						inc._add_outgoing_dependency(self)


			self._incremental_state = IncrementalMonitor.REFRESH_NOT_REQUIRED

		self.__clear_flag(self._FLAG_CYCLE_LOCK)


	def _on_incoming_dependency_access(self, inc):
		self._add_incoming_dependency(inc)


	def _add_incoming_dependency(self, dep):
		if not self.__test_flag(self._FLAG_BLOCK_INCOMING_DEPENDENCIES):
			if self._incoming_dependencies is None:
				self._incoming_dependencies = set()
			self._incoming_dependencies.add(dep)





	#
	#
	# Flags
	#
	#

	def __clear_flag(self, flag):
		self.__flags &= ~flag


	def __set_flag(self, flag):
		self.__flags |= flag


	def __set_flag_value(self, flag, value):
		if value:
			self.__flags |= flag
		else:
			self.__flags &= ~flag


	def __test_flag(self, flag):
		return (self.__flags & flag) != 0





class Test_IncrementalMonitor (unittest.TestCase):
	class _Counter (object):
		def __init__(self):
			self.count = 0

		def __call__(self, *args, **kwargs):
			self.count += 1


	def signal_counter(self):
		return Test_IncrementalMonitor._Counter()



	@staticmethod
	def _get_listeners(inc):
		if inc._listeners is not None:
			return inc._listeners
		else:
			return []


	def test_listener_refs(self):
		inc = IncrementalMonitor()

		l1 = self.signal_counter()
		l2 = self.signal_counter()
		l3 = self.signal_counter()
		l4 = self.signal_counter()


		inc.add_listener(l1)
		inc.add_listener(l2)
		inc.add_listener(l3)
		inc.add_listener(l4)

		self.assertEqual({l1, l2, l3, l4}, set(self._get_listeners(inc)))

		inc.remove_listener(l4)
		self.assertEqual({l1, l2, l3}, set(self._get_listeners(inc)))

		inc.remove_listener(l3)
		self.assertEqual({l1, l2}, set(self._get_listeners(inc)))

		l3 = self.signal_counter()
		inc.add_listener(l3)
		inc.add_listener(l3)
		self.assertEqual({l1, l2, l3}, set(self._get_listeners(inc)))

		inc.remove_listener(l3)
		inc.remove_listener(l2)
		self.assertEqual({l1}, set(self._get_listeners(inc)))
		self.assertTrue(inc.has_listeners)

		inc.remove_listener(l1)
		self.assertEqual(set(), set(self._get_listeners(inc)))
		self.assertFalse(inc.has_listeners)





class Test_IncrementalValueMonitor (Test_IncrementalMonitor):
	def test_listener(self):
		counter = self.signal_counter()
		self.assertEqual(0, counter.count)

		inc = IncrementalValueMonitor()

		inc.add_listener(counter)

		inc.on_changed()
		self.assertEqual(1, counter.count)

		inc.on_changed()
		self.assertEqual(1, counter.count)

		inc.on_access()
		inc.on_changed()
		self.assertEqual(2, counter.count)





class Test_IncrementalFunctionMonitor (Test_IncrementalMonitor):
	def test_listener(self):
		counter = self.signal_counter()
		self.assertEqual(0, counter.count)

		inc = IncrementalFunctionMonitor()

		inc.add_listener(counter)

		inc.on_changed()
		self.assertEqual(1, counter.count)

		inc.on_changed()
		self.assertEqual(1, counter.count)

		refresh_state = inc.on_refresh_begin()
		inc.on_refresh_end(refresh_state)
		inc.on_changed()
		self.assertEqual(2, counter.count)





	def test_chain(self):
		inc1 = IncrementalFunctionMonitor()
		inc2 = IncrementalFunctionMonitor()
		inc3 = IncrementalFunctionMonitor()
		inc4 = IncrementalFunctionMonitor()

		l1 = self.signal_counter()
		l2 = self.signal_counter()
		l3 = self.signal_counter()
		l4 = self.signal_counter()
		inc1.add_listener(l1)
		inc2.add_listener(l2)
		inc3.add_listener(l3)
		inc4.add_listener(l4)

		rs1 = inc1.on_refresh_begin()
		inc1.on_refresh_end( rs1 )
		inc1.on_changed()
		self.assertEqual( 1, l1.count )

		rs2 = inc2.on_refresh_begin()
		rs1 = inc1.on_refresh_begin()
		inc1.on_refresh_end( rs1 )
		inc1.on_access()
		inc2.on_refresh_end( rs2 )

		self.assertEqual({inc2}, inc1.outgoing_dependences )
		self.assertEqual({inc1}, inc2.incoming_dependencies )

		rs3 = inc3.on_refresh_begin()
		inc2.on_access()
		inc3.on_refresh_end( rs3 )

		self.assertEqual({inc3}, inc2.outgoing_dependences )
		self.assertEqual({inc2}, inc3.incoming_dependencies )

		rs4 = inc4.on_refresh_begin()
		inc2.on_access()
		inc4.on_refresh_end( rs4 )

		self.assertEqual({inc3, inc4}, inc2.outgoing_dependences )
		self.assertEqual({inc2}, inc4.incoming_dependencies )


		inc1.on_changed()
		self.assertEqual( 2, l1.count )
		self.assertEqual( 1, l2.count )
		self.assertEqual( 1, l3.count )
		self.assertEqual( 1, l4.count )

		rs1 = inc1.on_refresh_begin()
		inc1.on_refresh_end( rs1 )
		inc1.on_changed()
		self.assertEqual( 3, l1.count )
		self.assertEqual( 1, l2.count )
		self.assertEqual( 1, l3.count )
		self.assertEqual( 1, l4.count )

		rs4 = inc4.on_refresh_begin()
		rs2 = inc2.on_refresh_begin()
		rs1 = inc1.on_refresh_begin()
		inc1.on_refresh_end( rs1 )
		inc1.on_access()
		inc2.on_refresh_end( rs2 )
		inc2.on_access()
		inc4.on_refresh_end( rs4 )
		rs3 = inc3.on_refresh_begin()
		inc2.on_access()
		inc3.on_refresh_end( rs3 )

		self.assertEqual({inc2}, inc1.outgoing_dependences )
		self.assertEqual({inc3, inc4}, inc2.outgoing_dependences )
		self.assertEqual( set(), inc3.outgoing_dependences )
		self.assertEqual( set(), inc4.outgoing_dependences )
		self.assertEqual( set(),  inc1.incoming_dependencies )
		self.assertEqual({inc1}, inc2.incoming_dependencies )
		self.assertEqual({inc2}, inc3.incoming_dependencies )
		self.assertEqual({inc2}, inc4.incoming_dependencies )

		inc1.on_changed()
		self.assertEqual( 4, l1.count )
		self.assertEqual( 2, l2.count )
		self.assertEqual( 2, l3.count )
		self.assertEqual( 2, l4.count )



	def test_block_access_tracking(self):
		inc1 = IncrementalFunctionMonitor()
		inc2 = IncrementalFunctionMonitor()
		inc3 = IncrementalFunctionMonitor()
		inc4 = IncrementalFunctionMonitor()

		l1 = self.signal_counter()
		l2 = self.signal_counter()
		l3 = self.signal_counter()
		l4 = self.signal_counter()
		inc1.add_listener(l1)
		inc2.add_listener(l2)
		inc3.add_listener(l3)
		inc4.add_listener(l4)


		rs4 = inc4.on_refresh_begin()
		rs2 = inc2.on_refresh_begin()
		rs1 = inc1.on_refresh_begin()
		inc1.on_refresh_end( rs1 )
		inc1.on_access()
		inc2.on_refresh_end( rs2 )
		inc2.on_access()
		inc4.on_refresh_end( rs4 )
		rs3 = inc3.on_refresh_begin()
		f = IncrementalMonitor.block_access_tracking()
		inc2.on_access()
		IncrementalMonitor.unblock_access_tracking( f )
		inc3.on_refresh_end( rs3 )

		self.assertEqual({inc2}, inc1.outgoing_dependences )
		self.assertEqual({inc4}, inc2.outgoing_dependences )
		self.assertEqual(set(), inc3.outgoing_dependences )
		self.assertEqual(set(), inc4.outgoing_dependences )
		self.assertEqual(set(), inc1.incoming_dependencies )
		self.assertEqual({inc1}, inc2.incoming_dependencies )
		self.assertEqual(set(), inc3.incoming_dependencies )
		self.assertEqual({inc2}, inc4.incoming_dependencies )

		inc1.on_changed()
		self.assertEqual(1, l1.count )
		self.assertEqual(1, l2.count )
		self.assertEqual(0, l3.count )
		self.assertEqual(1, l4.count )



	def test_cycle(self):
		inc1 = IncrementalFunctionMonitor()

		rs1 = inc1.on_refresh_begin()

		def _cycle():
			inc1.on_refresh_begin()

		self.assertRaises(IncrementalEvaluationCycleError, _cycle)

		inc1.on_refresh_end( rs1 )



	def test_unnecessary_refresh(self):
		# This test is for coverage purposes only
		inc1 = IncrementalFunctionMonitor()

		rs1 = inc1.on_refresh_begin()
		inc1.on_refresh_end( rs1 )

		# Another refresh, without sending an 'on_changed'
		rs1 = inc1.on_refresh_begin()
		inc1.on_refresh_end( rs1 )



	def test_deps(self):
		inc1 = IncrementalFunctionMonitor()
		inc2 = IncrementalFunctionMonitor()
		inc3 = IncrementalFunctionMonitor()
		inc4 = IncrementalFunctionMonitor()

		rs4 = inc4.on_refresh_begin()
		rs3 = inc3.on_refresh_begin()
		rs2 = inc2.on_refresh_begin()
		rs1 = inc1.on_refresh_begin()
		inc1.on_refresh_end( rs1 )
		inc1.on_access()
		inc2.on_refresh_end( rs2 )
		inc2.on_access()
		inc3.on_refresh_end( rs3 )
		inc3.on_access()
		inc4.on_refresh_end( rs4 )


		self.assertEqual({inc2}, inc1.outgoing_dependences )
		self.assertEqual({inc3}, inc2.outgoing_dependences )
		self.assertEqual({inc4}, inc3.outgoing_dependences )
		self.assertEqual(set(), inc4.outgoing_dependences )
		self.assertEqual(set(), inc1.incoming_dependencies )
		self.assertEqual({inc1}, inc2.incoming_dependencies )
		self.assertEqual({inc2}, inc3.incoming_dependencies )
		self.assertEqual({inc3}, inc4.incoming_dependencies )

		inc4.on_changed()
		rs4 = inc4.on_refresh_begin()
		inc4.on_refresh_end( rs4 )

		self.assertEqual({inc2}, inc1.outgoing_dependences )
		self.assertEqual({inc3}, inc2.outgoing_dependences )
		self.assertEqual(set(), inc3.outgoing_dependences )
		self.assertEqual(set(), inc4.outgoing_dependences )
		self.assertEqual(set(), inc1.incoming_dependencies )
		self.assertEqual({inc1}, inc2.incoming_dependencies )
		self.assertEqual({inc2}, inc3.incoming_dependencies )
		self.assertEqual(set(), inc4.incoming_dependencies )

		del inc4
		del rs4
		del rs3
		del rs2
		del rs1
		gc.collect()

		self.assertEqual({inc2}, inc1.outgoing_dependences )
		self.assertEqual({inc3}, inc2.outgoing_dependences )
		self.assertEqual(set(), inc3.outgoing_dependences )
		self.assertEqual(set(), inc1.incoming_dependencies )
		self.assertEqual({inc1}, inc2.incoming_dependencies )
		self.assertEqual({inc2}, inc3.incoming_dependencies )

