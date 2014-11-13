##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
import unittest

from larch.pres.html import Html



def is_trackable(x):
	"""Determine if an object is trackable

	In order for an object to be trackable, it must have the '__change_history__' and '__trackable_contents__' attributes, even if their value is None

	Will print a warning to the console of one but not both attributes are present
	"""
	history = hasattr(x, '__change_history__')
	trackable = hasattr(x, '__trackable_contents__')
	if history and not trackable:
		print('Warning: Potentially trackable object {0} has __change_history__ but not __trackable_contents__'.format(x))
	if not history and trackable:
		print('Warning: Potentially trackable object {0} has __trackable_contents__ but not __change_history__'.format(x))
	return history and trackable






class CannotMergeChangeError (Exception):
	pass


class AlreadyTrackedError (Exception):
	pass


class ChangeHistoryIsFrozenError (Exception):
	pass




class Change (object):
	"""An abstract class representing a change in a change history

	A change applies to the objects that were modified that caused the change to be created and added to the change history.

	It can be applied or reverted using the apply and revert methods
	"""
	def apply(self):
		"""Apply the change
		"""
		raise NotImplementedError


	def revert(self):
		"""Revert the change
		"""
		raise NotImplementedError


	@property
	def description(self):
		"""Get a description of the change
		"""
		raise NotImplementedError, 'abstract'


	def can_merge_from(self, change):
		"""Determine if @change can be merged into @self

		Returns - True if merge is possible, False if not
		"""
		return False



	def merge_from(self, change):
		"""Merge @change into @self

		Raises CannotMargeChangeError if the merge is not possible
		"""
		raise CannotMergeChangeError


	def __present__(self, fragment):
		return Html('<span>', self.description, '</span>')



class FnChange (Change):
	"""A change whose behaviour is defined by functions that apply/revert
	"""
	def __init__(self, apply_fn, revert_fn, description):
		"""Constructor

		apply_fn - a function of the form function() that applies the change
		revert_fn - a function of the form function() that reverts the change
		description - a textual description of the change
		"""
		self._apply_fn = apply_fn
		self._revert_fn = revert_fn
		self._description = description


	def apply(self):
		"""Apply the change
		"""
		self._apply_fn()

	def revert(self):
		"""Revert the change
		"""
		self._revert_fn()


	description = property(lambda self: self._description, doc='Get the description')





class _ChangeHistoryEntry (object):
	def __init__(self):
		self._changes = []

	def apply(self):
		for change in self._changes:
			change.apply()

	def revert(self):
		for change in reversed(self._changes):
			change.revert()

	def top(self):
		return self._changes[-1]   if len(self._changes) > 0   else None



	is_empty = property(lambda self: len(self._changes)==0)


	def append(self, change):
		self._changes.append(change)


	def __present__(self, fragment):
		contents = ['<div>Change grooup']
		for change in self._changes:
			contents.append('<br>')
			contents.append(change)
		contents.append('</div>')
		return Html(*contents)




class ChangeHistory (object):
	def __init__(self):
		self._past = []
		self._future = []
		self._commands_are_blocked = False
		self._is_frozen = False
		self._freeze_count = 0
		self._listener = None
		self._pres_state_listeners = None


	def set_listener(self, listener):
		self._listener = listener


	def add_change(self, change):
		if not self._commands_are_blocked:
			del self._future[:]
			top = self._top_change()

			# Attempt to merge @change into @top
			if top is not None  and  top.can_merge_from(change):
				top.merge_from(change)
			else:
				if self._is_frozen:
					self._past[-1].append(change)
				else:
					entry = _ChangeHistoryEntry()
					entry.append(change)
					self._past.append(entry)

			self._on_modified()


	def add_fn_change(self, apply_fn, revert_fn, description):
		self.add_change(FnChange(apply_fn, revert_fn, description))


	def undo(self):
		if self._is_frozen:
			raise ChangeHistoryIsFrozenError

		if len(self._past) >= 1:
			entry = self._past.pop()
			self._revert_entry(entry)
			self._future.append(entry)

			self._on_modified()


	def redo(self):
		if self._is_frozen:
			raise ChangeHistoryIsFrozenError

		if len(self._future) >= 1:
			entry = self._future.pop()
			self._apply_entry(entry)
			self._past.append(entry)

			self._on_modified()



	def clear(self):
		del self._past[:]
		del self._future[:]

		self._on_modified()


	def freeze(self):
		if not self._is_frozen:
			# Add a new empty multi entry
			self._past.append(_ChangeHistoryEntry())

		self._is_frozen = True
		self._freeze_count += 1


	def thaw(self):
		self._freeze_count -= 1
		if self._freeze_count == 0:
			# If there is an existing top entry, and it is empty, remove it.
			top = self._top_entry()
			if top is not None  and  top.is_empty:
				self._past.pop()
			self._is_frozen = False



	def can_undo(self):
		return len(self._past) > 0

	def can_redo(self):
		return len(self._future) > 0

	num_undo_changes = property(lambda self: len(self._past))
	num_redo_changes = property(lambda self: len(self._future))



	def track(self, x):
		if is_trackable(x):
			history = x.__change_history__
			if history is None:
				x.__change_history__ = self
				trackable_contents_fn = x.__trackable_contents__
				if trackable_contents_fn is not None:
					for c in trackable_contents_fn():
						self.track(c)
			elif history != self:
				raise AlreadyTrackedError, 'Object \'{0}\' is already being tracked by a different change history'.format(x)


	def stop_tracking(self, x):
		if is_trackable(x):
			trackable_contents_fn = x.__trackable_contents__
			if trackable_contents_fn is not None:
				for c in trackable_contents_fn():
					self.stop_tracking(c)
			x.__change_history__ = None



	def is_tracking(self, x):
		try:
			history = x.__change_history__
		except AttributeError:
			return False
		else:
			return history is self



	def _top_change(self):
		if len(self._past) > 0:
			return self._past[-1].top()
		else:
			return None


	def _top_entry(self):
		if len(self._past) > 0:
			return self._past[-1]
		else:
			return None



	def _block_changes(self):
		self._commands_are_blocked = True


	def _unblock_changes(self):
		self._commands_are_blocked = False



	def _apply_entry(self, entry):
		self._block_changes()
		entry.apply()
		self._unblock_changes()

	def _revert_entry(self, entry):
		self._block_changes()
		entry.revert()
		self._unblock_changes()




	def _on_modified(self):
		if self._listener is not None:
			self._listener(self)

		#self._pres_state_listeners = presentation_state_listener_list.on_presentation_state_changed(self._pres_state_listeners, self)








	# def present(self, fragment, inherited_state):
	# 	self._pres_state_listeners = presentation_state_listener_list.add_listener(self._pres_state_listeners, fragment)
	#
	# 	pastTitleTop = self._past_title_style.applyTo( Row( [ Arrow( Arrow.Direction.DOWN, 14.0 ).align_v_centre(), Label( "Past" ) ] ) )
	# 	pastContents = Column( Pres.map_coerce( past ) )
	# 	pastTitleBottom = self._past_title_style.applyTo( Row( [ Arrow( Arrow.Direction.UP, 14.0 ).align_v_centre(), Label( "Past" ) ] ) )
	# 	pastBox = self._past_border_style.applyTo( Border( self._list_box_style.applyTo( Column( [ pastTitleTop, pastContents, pastTitleBottom ] ) ) ) )
	#
	# 	futureTitleTop = self._future_title_style.applyTo( Row( [ Arrow( Arrow.Direction.DOWN, 14.0 ).align_v_centre(), Label( "Future" ) ] ) )
	# 	futureContents = Column( Pres.map_coerce( future ) )
	# 	futureTitleBottom = self._future_title_style.applyTo( Row( [ Arrow( Arrow.Direction.UP, 14.0 ).align_v_centre(), Label( "Future" ) ] ) )
	# 	futureBox = self._future_border_style.applyTo( Border( self._list_box_style.applyTo( Column( [ futureTitleTop, futureContents, futureTitleBottom ] ) ) ) )
	#
	# 	mainBox = self._change_history_column_style.applyTo( Column( [ pastBox, futureBox ] ) )
	#
	# 	return ObjectBox( "ChangeHistory", mainBox )


#	_past_title_style = StyleSheet.style( Primitive.foreground( Color( 0.5, 0.0, 0.5 ) ), Primitive.shapePainter( FillPainter( Color( 0.5, 0.0, 0.5 ) ) ), Primitive.fontFace( "Serif" ), Primitive.fontSmallCaps( True ) )
#	_future_title_style = StyleSheet.style( Primitive.foreground( Color( 0.0, 0.25, 0.5 ) ), Primitive.shapePainter( FillPainter( Color( 0.0, 0.25, 0.5 ) ) ), Primitive.fontFace( "Serif" ), Primitive.fontSmallCaps( True ) )
#	_past_border_style = StyleSheet.style( Primitive.border( SolidBorder( 2.0, 3.0, 10.0, 10.0, Color( 0.5, 0.0, 0.5 ), None ) ) )
#	_future_border_style = StyleSheet.style( Primitive.border( SolidBorder( 2.0, 3.0, 10.0, 10.0, Color( 0.0, 0.25, 0.5 ), None ) ) )
#	_list_box_style = StyleSheet.style( Primitive.columnSpacing( 10.0 ) )
#	_change_history_column_style = StyleSheet.style( Primitive.columnSpacing( 20.0 ) )




class Test_change_history (unittest.TestCase):
	class _DataYChange (object):
		def __init__(self, d, old_y, y):
			self._d = d
			self._old_y = old_y
			self._y = y


		def apply(self):
			self._d.y = self._y

		def revert(self):
			self._d.y = self._old_y


		description = 'Test: Data.y'


		def can_merge_from(self, change):
			return isinstance(change, Test_change_history._DataYChange)  and  self._d is change._d


		def merge_from(self, change):
			if self.can_merge_from(change):
				self._y = change._y
			else:
				raise CannotMergeChangeError



	class _Data (object):
		def __init__(self, x, y):
			self._x = x
			self._y = y
			self.__change_history__ = None

		__trackable_contents__ = None


		def _setX(self, x):
			old_x = self._x
			self._x = x
			if self.__change_history__ is not None:
				self.__change_history__.add_fn_change(lambda: self._setX(x), lambda: self._setX(old_x), 'Test: Data.x')


		def _setY(self, y):
			old_y = self._y
			self._y = y
			if self.__change_history__ is not None:
				self.__change_history__.add_change(Test_change_history._DataYChange(self, old_y, y))


		x = property(lambda self: self._x, _setX)
		y = property(lambda self: self._y, _setY)



	class _DataZ (object):
		def __init__(self, x, y):
			self._x = x
			self._y = y
			self.__change_history__ = None


		def __trackable_contents__(self):
			return [self._x, self._y]


		def _setX(self, x):
			old_x = self._x
			self._x = x
			if self.__change_history__ is not None:
				self.__change_history__.stop_tracking(old_x)
				self.__change_history__.add_fn_change(lambda: self._setX(x), lambda: self._setX(old_x), 'Test: DataZ.x')
				self.__change_history__.track(x)


		def _setY(self, y):
			old_y = self._y
			self._y = y
			if self.__change_history__ is not None:
				self.__change_history__.stop_tracking(old_y)
				self.__change_history__.add_fn_change(lambda: self._setY(y), lambda: self._setY(old_y), 'Test: DataZ.y')
				self.__change_history__.track(y)


		x = property(lambda self: self._x, _setX)
		y = property(lambda self: self._y, _setY)





	def test_undo_redo_clear(self):
		h = ChangeHistory()
		d = Test_change_history._Data( 0, -1 )

		h.track( d )

		self.assertEqual( d.x, 0 )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.x = 1
		self.assertEqual( d.x, 1 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.x = 2
		self.assertEqual( d.x, 2 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.x = 3
		self.assertEqual( d.x, 3 )
		self.assertEqual( h.num_undo_changes, 3 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.x = 4
		self.assertEqual( d.x, 4 )
		self.assertEqual( h.num_undo_changes, 4 )
		self.assertEqual( h.num_redo_changes, 0 )

		h.undo()
		self.assertEqual( d.x, 3 )
		self.assertEqual( h.num_undo_changes, 3 )
		self.assertEqual( h.num_redo_changes, 1 )

		h.undo()
		self.assertEqual( d.x, 2 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 2 )

		h.redo()
		self.assertEqual( d.x, 3 )
		self.assertEqual( h.num_undo_changes, 3 )
		self.assertEqual( h.num_redo_changes, 1 )

		d.x = 5
		self.assertEqual( d.x, 5 )
		self.assertEqual( h.num_undo_changes, 4 )
		self.assertEqual( h.num_redo_changes, 0 )

		h.undo()
		self.assertEqual( d.x, 3 )
		self.assertEqual( h.num_undo_changes, 3 )
		self.assertEqual( h.num_redo_changes, 1 )

		h.undo()
		self.assertEqual( d.x, 2 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 2 )

		h.clear()
		self.assertEqual( d.x, 2 )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 0 )




	def test_command_joining(self):
		h = ChangeHistory()
		d = Test_change_history._Data( -1, 0 )

		h.track( d )

		self.assertEqual( d.y , 0 )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.y = 1
		self.assertEqual( d.y , 1 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.y = 2
		self.assertEqual( d.y , 2 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.y = 3
		self.assertEqual( d.y , 3 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.y = 4
		self.assertEqual( d.y , 4 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		h.undo()
		self.assertEqual( d.y , 0 )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 1 )

		h.redo()
		self.assertEqual( d.y , 4 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.y = 5
		self.assertEqual( d.y , 5 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		h.undo()
		self.assertEqual( d.y , 0 )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 1 )





	def test_freeze_thaw(self):
		h = ChangeHistory()
		d = Test_change_history._Data( 0, -1 )

		h.track( d )

		self.assertEqual( d.x, 0 )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.x = 1
		self.assertEqual( d.x, 1 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		h.freeze()
		self.assertEqual( d.x, 1 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 0 )

		# Ensure the immediately thawing does not cause problems
		h.thaw()
		self.assertEqual( d.x, 1 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		# Re-freeze
		h.freeze()

		d.x = 2
		self.assertEqual( d.x, 2 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.x = 3
		self.assertEqual( d.x, 3 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.x = 4
		self.assertEqual( d.x, 4 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 0 )

		# Ensure that undo() and redo() raise exceptions when the change history is frozen
		self.assertRaises(ChangeHistoryIsFrozenError, lambda: h.undo())
		self.assertRaises(ChangeHistoryIsFrozenError, lambda: h.redo())

		h.thaw()
		self.assertEqual( d.x, 4 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 0 )

		h.undo()
		self.assertEqual( d.x, 1 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 1 )

		h.undo()
		self.assertEqual( d.x, 0 )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 2 )

		h.redo()
		self.assertEqual( d.x, 1 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 1 )

		h.redo()
		self.assertEqual( d.x, 4 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 0 )




	def test_listener(self):
		count = [0]

		def listener(h):
			count[0] += 1



		h = ChangeHistory()
		h.set_listener(listener)


		d = Test_change_history._Data( 0, -1 )

		h.track( d )

		self.assertEqual( d.x, 0 )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.x = 1
		self.assertEqual( d.x, 1 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.x = 2
		self.assertEqual( d.x, 2 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 0 )


		self.assertEqual(2, count[0])

		h.undo()
		self.assertEqual(3, count[0])

		h.undo()
		self.assertEqual(4, count[0])




	def test_stop_tracking(self):
		h = ChangeHistory()
		d = Test_change_history._Data( 0, -1 )

		self.assertEqual( d.x, 0 )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.x = 1
		self.assertEqual( d.x, 1 )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 0 )

		h.track( d )

		d.x = 2
		self.assertEqual( d.x, 2 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.x = 3
		self.assertEqual( d.x, 3 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 0 )

		h.stop_tracking(d)

		d.x = 4
		self.assertEqual( d.x, 4 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 0 )




	def test_children(self):
		h = ChangeHistory()
		x = Test_change_history._Data( -1, -2 )
		y = Test_change_history._Data( -1, -2 )
		d = Test_change_history._DataZ( x, y )
		x2 = Test_change_history._Data( -3, -4 )
		y2 = Test_change_history._Data( -30, -40 )

		h.track( d )

		self.assertTrue(h.is_tracking(d))
		self.assertTrue(h.is_tracking(x))
		self.assertTrue(h.is_tracking(y))

		self.assertIs( d.x, x )
		self.assertIs( d.y, y )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 0 )

		x.x = 1
		self.assertEqual( x.x, 1 )
		self.assertEqual( h.num_undo_changes, 1 )
		self.assertEqual( h.num_redo_changes, 0 )

		y.x = 2
		self.assertEqual( y.x, 2 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 0 )

		x.y = 3
		self.assertEqual( x.y, 3 )
		self.assertEqual( h.num_undo_changes, 3 )
		self.assertEqual( h.num_redo_changes, 0 )

		y.y = 4
		self.assertEqual( y.y, 4 )
		self.assertEqual( h.num_undo_changes, 4 )
		self.assertEqual( h.num_redo_changes, 0 )

		h.undo()
		self.assertEqual( x.y, 3 )
		self.assertEqual( h.num_undo_changes, 3 )
		self.assertEqual( h.num_redo_changes, 1 )

		h.undo()
		self.assertEqual( y.x, 2 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 2 )

		h.redo()
		self.assertEqual( x.y, 3 )
		self.assertEqual( h.num_undo_changes, 3 )
		self.assertEqual( h.num_redo_changes, 1 )

		x.x = 5
		self.assertEqual( x.x, 5 )
		self.assertEqual( h.num_undo_changes, 4 )
		self.assertEqual( h.num_redo_changes, 0 )

		h.undo()
		self.assertEqual( y.x, 2 )
		self.assertEqual( h.num_undo_changes, 3 )
		self.assertEqual( h.num_redo_changes, 1 )

		h.undo()
		self.assertEqual( x.x, 1 )
		self.assertEqual( h.num_undo_changes, 2 )
		self.assertEqual( h.num_redo_changes, 2 )

		d.x = x2
		self.assertFalse(h.is_tracking(x))
		self.assertTrue(h.is_tracking(x2))
		self.assertIs(x2, d.x)
		self.assertEqual( h.num_undo_changes, 3 )
		self.assertEqual( h.num_redo_changes, 0 )

		d.y = y2
		self.assertFalse(h.is_tracking(y))
		self.assertTrue(h.is_tracking(y2))
		self.assertIs(y2, d.y)
		self.assertEqual( h.num_undo_changes, 4 )
		self.assertEqual( h.num_redo_changes, 0 )

		y2.x = 5
		self.assertEqual( y2.x, 5 )
		self.assertEqual( h.num_undo_changes, 5 )
		self.assertEqual( h.num_redo_changes, 0 )

		h.undo()
		self.assertEqual( y2.x, -30 )
		self.assertEqual( h.num_undo_changes, 4 )
		self.assertEqual( h.num_redo_changes, 1 )

		h.clear()
		self.assertIs( d.x, x2 )
		self.assertEqual( h.num_undo_changes, 0 )
		self.assertEqual( h.num_redo_changes, 0 )


