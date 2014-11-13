##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
import bisect

__author__ = 'Geoff'


class PriorityList (object):
	"""
	Priority List
	"""
	def __init__(self):
		self.__priotities = []
		self.__items = []


	def add(self, priority, x):
		"""
		Add an item @x with a priority of @priority,
		"""
		try:
			self.remove(x)
		except ValueError:
			pass
		index = bisect.bisect_left(self.__priotities, priority)
		self.__priotities.insert(index, priority)
		self.__items.insert(index, x)

	def remove(self, x):
		index = self.__items.index(x)
		del self.__priotities[index]
		del self.__items[index]


	def __len__(self):
		return len(self.__items)


	def pop(self):
		p = self.__priotities.pop()
		x = self.__items.pop()
		return x


	def __iter__(self):
		return reversed(self.__items)



import unittest

class Test_PriorityList (unittest.TestCase):
	def test_empty_iter(self):
		p = PriorityList()
		self.assertEqual([], list(p))


	def test_add_iter(self):
		p = PriorityList()
		self.assertEqual([], list(p))

		p.add(0, 'a')
		self.assertEqual(['a'], list(p))

		p.add(-1, 'b')
		self.assertEqual(['a', 'b'], list(p))

		p.add(0, 'c')
		self.assertEqual(['a', 'c', 'b'], list(p))

		p.add(1, 'd')
		self.assertEqual(['d', 'a', 'c', 'b'], list(p))

		p.add(-2, 'd')
		self.assertEqual(['a', 'c', 'b', 'd'], list(p))


	def test_remove_iter(self):
		p = PriorityList()
		p.add(0, 'a')
		p.add(-1, 'b')
		p.add(0, 'c')
		p.add(1, 'd')
		self.assertEqual(['d', 'a', 'c', 'b'], list(p))

		p.remove('c')
		self.assertEqual(['d', 'a', 'b'], list(p))

		self.assertRaises(ValueError, lambda: p.remove('c'))


	def test_pop(self):
		p = PriorityList()
		p.add(0, 'a')
		p.add(-1, 'b')
		p.add(0, 'c')
		p.add(1, 'd')
		self.assertEqual(['d', 'a', 'c', 'b'], list(p))

		self.assertEqual('d', p.pop())
		self.assertEqual(['a', 'c', 'b'], list(p))

		self.assertEqual('a', p.pop())
		self.assertEqual(['c', 'b'], list(p))

		self.assertEqual('c', p.pop())
		self.assertEqual(['b'], list(p))

		self.assertEqual('b', p.pop())
		self.assertEqual([], list(p))


	def test_len(self):
		p = PriorityList()
		p.add(0, 'a')
		p.add(-1, 'b')
		p.add(0, 'c')
		p.add(1, 'd')

		self.assertEqual(4, len(p))
