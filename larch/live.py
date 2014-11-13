##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from copy import deepcopy
import sys

from larch.incremental import IncrementalValueMonitor, IncrementalFunctionMonitor
from larch.inspector import present_exception
from larch.pres.pres import Pres, CompositePres, InnerFragment
from larch.pres.obj_pres import error_box


class AbstractLive (CompositePres):
	class __ValuePres (Pres):
		def __init__(self, live):
			self.__live = live

		def build(self, pres_ctx):
			value = None
			pres_ctx.fragment_view.disable_inspector()
			try:
				value = self.__live.value
			except Exception, e:
				exception_view = present_exception.present_exception_with_traceback(e, sys.exc_info()[1], sys.exc_info()[2])
				p = error_box('Exception during live evaluation', exception_view)
			else:
				p = Pres.coerce(value)

			return p.build(pres_ctx)


	@property
	def incremental_monitor(self):
		raise NotImplementedError, 'abstract'

	def add_listener(self, listener):
		self.incremental_monitor.add_listener(listener)

	def remove_listener(self, listener):
		self.incremental_monitor.remove_listener(listener)



	@property
	def value(self):
		raise NotImplementedError, 'abstract'

	@value.setter
	def value(self, v):
		raise NotImplementedError, 'abstract'

	@property
	def static_value(self):
		raise NotImplementedError, 'abstract'



	def __call__(self):
		return self.value


	def pres(self, pres_ctx):
		return InnerFragment(self.__ValuePres(self))






class LiveValue (AbstractLive):
	def __init__(self, value=None):
		self.__incr = IncrementalValueMonitor(self)
		self.__value = value



	@property
	def incremental_monitor(self):
		return self.__incr


	@property
	def value(self):
		self.__incr.on_access()
		return self.__value

	@value.setter
	def value(self, v):
		self.__value = v
		self.__incr.on_changed()

	@property
	def static_value(self):
		return self.__value


class LiveFunction (AbstractLive):
	def __init__(self, fn):
		self.__incr = IncrementalFunctionMonitor(self)
		self.__fn = fn
		self.__value_cache = None



	@property
	def function(self):
		return self.__fn

	@function.setter
	def function(self, f):
		self.__fn = f
		self.__incr.on_changed()


	@property
	def __name__(self):
		return self.__fn.__name__




	@property
	def incremental_monitor(self):
		return self.__incr


	@property
	def value(self):
		try:
			self.__refresh_value()
		finally:
			self.__incr.on_access()
		return self.__value_cache

	@value.setter
	def value(self, v):
		self.function = lambda: v

	@property
	def static_value(self):
		self.__refresh_value()
		return self.__value_cache



	def __refresh_value(self):
		refresh_state = self.__incr.on_refresh_begin()
		try:
			if refresh_state is not None:
				self.__value_cache = self.__fn()
		finally:
			self.__incr.on_refresh_end(refresh_state)







def _on_tracked_list_set_contents(changeHistory, ls, oldContents, newContents, description):
	if changeHistory is not None:
		for x in oldContents:
			changeHistory.stop_tracking( x )
		changeHistory.add_fn_change( lambda: ls._set_contents( newContents ), lambda: ls._set_contents( oldContents ), description )
		for x in newContents:
			changeHistory.track( x )

def _on_tracked_list_set_item(changeHistory, ls, i, oldX, x, description):
	if changeHistory is not None:
		changeHistory.stop_tracking( oldX )
		changeHistory.add_fn_change( lambda: ls.__setitem__( i, x ), lambda: ls.__setitem__( i, oldX ), description )
		changeHistory.track( x )


def _on_tracked_list_append(changeHistory, ls, x, description):
	if changeHistory is not None:
		changeHistory.add_fn_change( lambda: ls.append( x ), lambda: ls.__delitem__( -1 ), description )
		changeHistory.track( x )

def _on_tracked_list_extend(changeHistory, ls, xs, description):
	if changeHistory is not None:
		n = len( xs )
		def _del():
			del ls[-n:]
		changeHistory.add_fn_change( lambda: ls.extend( xs ), _del, description )
		for x in xs:
			changeHistory.track( x )

def _on_tracked_list_insert(changeHistory, ls, i, x, description):
	if changeHistory is not None:
		changeHistory.add_fn_change( lambda: ls.insert( i, x ), lambda: ls.__delitem__( i ), description )
		changeHistory.track( x )

def _on_tracked_list_pop(changeHistory, ls, x, description):
	if changeHistory is not None:
		changeHistory.add_fn_change( lambda: ls.pop(), lambda: ls.append( x ), description )
		changeHistory.stop_tracking( x )

def _on_tracked_list_remove(changeHistory, ls, i, x, description):
	if changeHistory is not None:
		changeHistory.add_fn_change( lambda: ls.__delitem__( i ), lambda: ls.insert( i, x ), description )
		changeHistory.stop_tracking( x )

def _on_tracked_list_reverse(changeHistory, ls, description):
	if changeHistory is not None:
		changeHistory.add_fn_change( lambda: ls.reverse(), lambda: ls.reverse(), description )



class _LiveListIter (object):
	__slots__ = [ '_it', '_incr' ]

	def __init__(self, it, incr):
		self._it = it
		self._incr = incr


	def __iter__(self):
		return self

	def next(self):
		self._incr.on_access()
		return self._it.next()


class TrackedLiveList (object):
	__slots__ = [ '__change_history__', '_items', '_incr', '__change_listener']

	def __init__(self, xs=None):
		self._items = []
		if xs is not None:
			self._items[:] = xs[:]
		self.__change_history__ = None
		self._incr = IncrementalValueMonitor()
		self.__change_listener = None


	@property
	def change_listener(self):
		return self.__change_listener

	@change_listener.setter
	def change_listener(self, x):
		self.__change_listener = x


	def __getstate__(self):
		self._incr.on_access()
		return { 'items' : self._items }

	def __setstate__(self, state):
		self._items = state['items']
		self.__change_history__ = None
		self._incr = IncrementalValueMonitor()
		self.__change_listener = None

	def __copy__(self):
		self._incr.on_access()
		t = type( self )
		return t( self._items )

	def __deepcopy__(self, memo):
		self._incr.on_access()
		t = type( self )
		return t( deepcopy( self._items, memo ) )


	def __eq__(self, other):
		if isinstance( other, TrackedLiveList ):
			other = other._items
		return self._items == other

	def __ne__(self, other):
		if isinstance( other, TrackedLiveList ):
			other = other._items
		return self._items != other


	def __str__(self):
		return str( self._items )

	def __repr__(self):
		return 'LiveList( {0} )'.format( repr( self._items ) )


	def __trackable_contents__(self):
		return self._items


	def __clipboard_copy__(self, memo):
		self._incr.on_access()
		t = type( self )
		return t( [ memo.copy( x )   for x in self ] )



	def __iter__(self):
		self._incr.on_access()
		return _LiveListIter( iter( self._items ), self._incr )

	def __contains__(self, x):
		self._incr.on_access()
		return x in self._items

	def __add__(self, xs):
		self._incr.on_access()
		return self._items + xs

	def __mul__(self, x):
		self._incr.on_access()
		return self._items * x

	def __rmul__(self, x):
		self._incr.on_access()
		return x * self._items

	def __getitem__(self, index):
		self._incr.on_access()
		return self._items[index]

	def __len__(self):
		self._incr.on_access()
		return len( self._items )

	def index(self, x, i=None, j=None):
		self._incr.on_access()
		if i is None:
			return self._items.index( x )
		elif j is None:
			return self._items.index( x, i )
		else:
			return self._items.index( x, i, j )

	def count(self, x):
		self._incr.on_access()
		return self._items.count( x )

	def __setitem__(self, index, x):
		if isinstance( index, int )  or  isinstance( index, long ):
			oldX = self._items[index]
			if self.__change_listener is not None:
				old_contents = self._items[:]
			self._items[index] = x
			_on_tracked_list_set_item( self.__change_history__, self, index, oldX, x, 'Live list set item' )
			if self.__change_listener is not None:
				self.__change_listener( old_contents, self._items[:] )
		else:
			old_contents = self._items[:]
			self._items[index] = x
			newContents = self._items[:]
			_on_tracked_list_set_contents( self.__change_history__, self, old_contents, newContents, 'Live list set item' )
			if self.__change_listener is not None:
				self.__change_listener( old_contents, newContents )
		self._incr.on_changed()

	def __delitem__(self, index):
		oldContents = self._items[:]
		del self._items[index]
		newContents = self._items[:]
		_on_tracked_list_set_contents( self.__change_history__, self, oldContents, newContents, 'Live list del item' )
		if self.__change_listener is not None:
			self.__change_listener( oldContents, newContents )
		self._incr.on_changed()

	def append(self, x):
		if self.__change_listener is not None:
			old_contents = self._items[:]
		self._items.append( x )
		_on_tracked_list_append( self.__change_history__, self, x, 'Live list append' )
		if self.__change_listener is not None:
			self.__change_listener( old_contents, self._items[:] )
		self._incr.on_changed()

	def extend(self, xs):
		if self.__change_listener is not None:
			old_contents = self._items[:]
		self._items.extend( xs )
		_on_tracked_list_extend( self.__change_history__, self, xs, 'Live list extend' )
		if self.__change_listener is not None:
			self.__change_listener( old_contents, self._items[:] )
		self._incr.on_changed()

	def insert(self, i, x):
		if self.__change_listener is not None:
			old_contents = self._items[:]
		self._items.insert( i, x )
		_on_tracked_list_insert( self.__change_history__, self, i, x, 'Live list insert' )
		if self.__change_listener is not None:
			self.__change_listener( old_contents, self._items[:] )
		self._incr.on_changed()

	def pop(self):
		if self.__change_listener is not None:
			old_contents = self._items[:]
		x = self._items.pop()
		_on_tracked_list_pop( self.__change_history__, self, x, 'Live list pop' )
		if self.__change_listener is not None:
			self.__change_listener( old_contents, self._items[:] )
		self._incr.on_changed()
		return x

	def remove(self, x):
		if self.__change_listener is not None:
			old_contents = self._items[:]
		i = self._items.index( x )
		xFromList = self._items[i]
		del self._items[i]
		_on_tracked_list_remove( self.__change_history__, self, i, xFromList, 'Live list remove' )
		if self.__change_listener is not None:
			self.__change_listener( old_contents, self._items[:] )
		self._incr.on_changed()

	def reverse(self):
		if self.__change_listener is not None:
			old_contents = self._items[:]
		self._items.reverse()
		_on_tracked_list_reverse( self.__change_history__, self, 'Live list reverse' )
		if self.__change_listener is not None:
			self.__change_listener( old_contents, self._items[:] )
		self._incr.on_changed()

	def sort(self, cmp_fn=None, key=None, reverse=False):
		old_contents = self._items[:]
		self._items.sort( cmp=cmp_fn, key=key, reverse=reverse )
		newContents = self._items[:]
		_on_tracked_list_set_contents( self.__change_history__, self, old_contents, newContents, 'Live list sort' )
		if self.__change_listener is not None:
			self.__change_listener( old_contents, newContents )
		self._incr.on_changed()

	def _set_contents(self, xs):
		old_contents = self._items[:]
		self._items[:] = xs
		_on_tracked_list_set_contents( self.__change_history__, self, old_contents, xs, 'Live list set contents' )
		if self.__change_listener is not None:
			self.__change_listener( old_contents, self._items[:] )
		self._incr.on_changed()






import unittest
import random

from larch.core.change_history import ChangeHistory


class Test_TrackedLiveList (unittest.TestCase):
	class _Value (object):
		def __init__(self, x):
			self.__change_history__ = None
			self.x = x


		def __trackable_contents__(self):
			return [ self.x ]


		def is_tracked(self):
			return self.__change_history__ is not None


		def __eq__(self, x):
			return isinstance( x, Test_TrackedLiveList._Value )  and  self.x == x.x

		def __str__(self):
			return 'Value( %s )'  %  str( self.x )

		def __repr__(self):
			return 'Value( %s )'  %  str( self.x )

		def __cmp__(self, x):
			return cmp( self.x, x.x )




	def setUp(self):
		self.history = ChangeHistory()
		self.ls = TrackedLiveList()
		self.history.track( self.ls )
		self.prevxs = None
		self.newxs = None
		self.ls.change_listener = self._onChanged

	def tearDown(self):
		self.ls.change_listener = None
		self.history.stop_tracking( self.ls )
		self.ls = None
		self.history = None
		self.prevxs = None
		self.newxs = None


	def _onChanged(self, old_contents, new_contents):
		self.prevxs = old_contents
		self.newxs = new_contents


	def _test_changes(self, expected_old_contents, expected_new_contents):
		self.assertEqual(self.prevxs, expected_old_contents)
		self.assertEqual(self.newxs, expected_new_contents)
		self.prevxs = None
		self.newxs = None


	def test_setitem(self):
		self.assertEqual( self.ls[:], [] )

		_two = Test_TrackedLiveList._Value( -2 )
		self.ls.append( _two )
		self.assertEqual( self.ls[:], [ _two ] )
		self.assertTrue( _two.is_tracked() )
		self._test_changes( [], [ _two ] )

		_one = Test_TrackedLiveList._Value( -1 )
		self.ls[0] = _one
		self.assertEqual( self.ls[:], [ _one ] )
		self.assertFalse( _two.is_tracked() )
		self.assertTrue( _one.is_tracked() )
		self._test_changes( [ _two ], [ _one ] )

		_rng = [ Test_TrackedLiveList._Value( x )   for x in xrange( 5 ) ]
		self.ls[1:] = _rng
		self.assertEqual( self.ls[:], [ _one ] + _rng )
		self.assertFalse( _two.is_tracked() )
		self.assertTrue( _one.is_tracked() )
		for x in _rng:
			self.assertTrue( x.is_tracked() )
		self._test_changes( [ _one ], [ _one ] + _rng )


		self.history.undo()
		self.assertEqual( self.ls[:], [ _one ] )
		self.assertFalse( _two.is_tracked() )
		self.assertTrue( _one.is_tracked() )
		for x in _rng:
			self.assertFalse( x.is_tracked() )
		self._test_changes( [ _one ] + _rng, [ _one ] )


		self.history.undo()
		self.assertEqual( self.ls[:], [ _two ] )
		self.assertFalse( _one.is_tracked() )
		self.assertTrue( _two.is_tracked() )
		self._test_changes( [ _one ], [ _two ] )


		self.history.redo()
		self.assertEqual( self.ls[:], [ _one ] )
		self.assertFalse( _two.is_tracked() )
		self.assertTrue( _one.is_tracked() )
		for x in _rng:
			self.assertFalse( x.is_tracked() )
		self._test_changes( [ _two ], [ _one ] )


		self.history.redo()
		self.assertEqual( self.ls[:], [ _one ] + _rng )
		self.assertFalse( _two.is_tracked() )
		self.assertTrue( _one.is_tracked() )
		for x in _rng:
			self.assertTrue( x.is_tracked() )
		self._test_changes( [ _one ], [ _one ] + _rng )




	def test_delitem(self):
		self.assertEqual( self.ls[:], [] )

		_rng = [ Test_TrackedLiveList._Value( x )   for x in xrange( 5 ) ]
		self.ls[:] = _rng
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( [], _rng )


		del self.ls[0]
		self.assertEqual( self.ls[:], _rng[1:] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ False, True, True, True, True ] )
		self._test_changes( _rng, _rng[1:] )


		del self.ls[1:3]
		self.assertEqual( self.ls[:], [ _rng[1], _rng[4] ] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ False, True, False, False, True ] )
		self._test_changes( _rng[1:], [ _rng[1], _rng[4] ] )


		self.history.undo()
		self.assertEqual( self.ls[:], _rng[1:] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ False, True, True, True, True ] )
		self._test_changes( [ _rng[1], _rng[4] ], _rng[1:] )


		self.history.undo()
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( _rng[1:], _rng )


		self.history.redo()
		self.assertEqual( self.ls[:], _rng[1:] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ False, True, True, True, True ] )
		self._test_changes( _rng, _rng[1:] )


		self.history.redo()
		self.assertEqual( self.ls[:], [ _rng[1], _rng[4] ] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ False, True, False, False, True ] )
		self._test_changes( _rng[1:], [ _rng[1], _rng[4] ] )



	def test_append(self):
		self.assertEqual( self.ls[:], [] )

		v = Test_TrackedLiveList._Value( 2 )
		self.ls.append( v )
		self.assertTrue( v.is_tracked() )

		self.assertEqual( self.ls[:], [ Test_TrackedLiveList._Value( 2 ) ] )
		self._test_changes( [], [ v ] )

		self.history.undo()
		self.assertEqual( self.ls[:], [] )
		self.assertFalse( v.is_tracked() )
		self._test_changes( [ v ], [] )

		self.history.redo()
		self.assertEqual( self.ls[:], [ Test_TrackedLiveList._Value( 2 ) ] )
		self.assertTrue( v.is_tracked() )
		self._test_changes( [], [ v ] )



	def test_extend(self):
		_rng = [ Test_TrackedLiveList._Value( x )   for x in xrange( 5 ) ]
		self.assertEqual( self.ls[:], [] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ False, False, False, False, False ] )

		self.ls.extend( _rng )
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( [], _rng )

		self.history.undo()
		self.assertEqual( self.ls[:], [] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ False, False, False, False, False ] )
		self._test_changes( _rng, [] )

		self.history.redo()
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( [], _rng )



	def test_insert(self):
		v = Test_TrackedLiveList._Value( 20 )
		_rng = [ Test_TrackedLiveList._Value( x )   for x in xrange( 5 ) ]

		self.ls[:] = _rng
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self.assertFalse( v.is_tracked() )
		self._test_changes( [], _rng )

		self.ls.insert( 2, v )
		self.assertEqual( self.ls[:], _rng[:2] + [ v ] + _rng[2:] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self.assertTrue( v.is_tracked() )
		self._test_changes( _rng, _rng[:2] + [ v ] + _rng[2:] )

		self.history.undo()
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self.assertFalse( v.is_tracked() )
		self._test_changes( _rng[:2] + [ v ] + _rng[2:], _rng )

		self.history.redo()
		self.assertEqual( self.ls[:], _rng[:2] + [ v ] + _rng[2:] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self.assertTrue( v.is_tracked() )
		self._test_changes( _rng, _rng[:2] + [ v ] + _rng[2:] )



	def test_pop(self):
		_rng = [ Test_TrackedLiveList._Value( x )   for x in xrange( 5 ) ]

		self.ls[:] = _rng
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( [], _rng )

		v = self.ls.pop()
		self.assertTrue( v is _rng[-1] )
		self.assertEqual( self.ls[:], _rng[:-1] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, False ] )
		self._test_changes( _rng, _rng[:-1] )

		self.history.undo()
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( _rng[:-1], _rng )

		self.history.redo()
		self.assertEqual( self.ls[:], _rng[:-1] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, False ] )
		self._test_changes( _rng, _rng[:-1] )



	def test_remove(self):
		_rng = [ Test_TrackedLiveList._Value( x )   for x in xrange( 5 ) ]

		self.ls[:] = _rng
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( [], _rng )

		self.ls.remove( Test_TrackedLiveList._Value( 2 ) )
		self.assertEqual( self.ls[:], _rng[:2] + _rng[3:] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, False, True, True ] )
		self._test_changes( _rng, _rng[:2] + _rng[3:] )

		self.history.undo()
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( _rng[:2] + _rng[3:], _rng )

		self.history.redo()
		self.assertEqual( self.ls[:], _rng[:2] + _rng[3:] )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, False, True, True ] )
		self._test_changes( _rng, _rng[:2] + _rng[3:] )



	def test_reverse(self):
		_rng = [ Test_TrackedLiveList._Value( x )   for x in xrange( 5 ) ]
		_rev = _rng[:]
		_rev.reverse()

		self.ls[:] = _rng
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( [], _rng )

		self.ls.reverse()
		self.assertEqual( self.ls[:], _rev )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( _rng, _rev )

		self.history.undo()
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( _rev, _rng )

		self.history.redo()
		self.assertEqual( self.ls[:], _rev )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( _rng, _rev )



	def test_sort(self):
		_rng = [ Test_TrackedLiveList._Value( x )   for x in xrange( 5 ) ]

		_shuf = _rng[:]
		r = random.Random( 12345 )
		r.shuffle( _shuf )

		self.ls[:] = _shuf
		self.assertEqual( self.ls[:], _shuf )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( [], _shuf )

		self.ls.sort()
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( _shuf, _rng )

		self.history.undo()
		self.assertEqual( self.ls[:], _shuf )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( _rng, _shuf )

		self.history.redo()
		self.assertEqual( self.ls[:], _rng )
		self.assertEqual( [ x.is_tracked() for x in _rng ],  [ True, True, True, True, True ] )
		self._test_changes( _shuf, _rng )



	def test_eq(self):
		self.ls[:] = range( 0, 5 )

		self.assertTrue( self.ls == range( 0, 5 ) )
		self.assertTrue( self.ls == TrackedLiveList( range( 0, 5 ) ) )
		self.assertFalse( self.ls == range( 0, 6 ) )
		self.assertFalse( self.ls == TrackedLiveList( range( 0, 6 ) ) )

		self.assertTrue( self.ls != range( 0, 6 ) )
		self.assertTrue( self.ls != TrackedLiveList( range( 0, 6 ) ) )
		self.assertFalse( self.ls != range( 0, 5 ) )
		self.assertFalse( self.ls != TrackedLiveList( range( 0, 5 ) ) )



	def test_str(self):
		self.ls[:] = range( 0, 5 )

		self.assertEqual( str( self.ls ), str( range( 0, 5 ) ) )


	def test_repr(self):
		self.ls[:] = range( 0, 5 )

		self.assertEqual( repr( self.ls ), 'LiveList( ' + repr( range( 0, 5 ) ) + ' )' )
