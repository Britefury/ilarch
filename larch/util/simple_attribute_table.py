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

__author__ = 'Geoff'



class _AttributeValuesMultiple (object):
	def __init__(self, values):
		assert isinstance(values, dict)
		self._values = {}
		self._values.update(values)

		# Compute the hash code
		hashes_and_values = [(key, value)   for key, value in values.items()]
		hashes_and_values.sort(lambda x, y: cmp(x[0], y[0]))
		self._hash_code = hash(tuple(hashes_and_values))


	def __hash__(self):
		return self._hash_code

	def __eq__(self, x):
		if isinstance(x, _AttributeValuesMultiple):
			return self._values == x._values
		else:
			return NotImplemented

	def __ne__(self, x):
		if isinstance(x, _AttributeValuesMultiple):
			return self._values != x._values
		else:
			return NotImplemented



class _AttributeValueSingle (object):
	def __init__(self, attribute, value):
		self._attribute = attribute
		self._value = value
		self._hash_code = hash((self._attribute, self._value))


	def __hash__(self):
		return self._hash_code

	def __eq__(self, x):
		if isinstance(x, _AttributeValueSingle):
			return self._attribute is x._attribute  and  self._value == x._value
		else:
			return NotImplemented

	def __ne__(self, x):
		if isinstance(x, _AttributeValueSingle):
			return self._attribute is not x._attribute  and  self._value != x._value
		else:
			return NotImplemented




class SimpleAttributeTable (object):
	_attribute_table_sets_by_type = {}



	def __init__(self):
		self._values = {}
		self._single_value_derived_tables = weakref.WeakValueDictionary()
		self._multi_value_derived_tables = weakref.WeakValueDictionary()
		self._attrib_table_derived_tables = weakref.WeakValueDictionary()
		self._del_value_derived_tables = weakref.WeakValueDictionary()


	def __getitem__(self, key):
		return self._values[key]

	def get(self, key, default_value=None):
		return self._values.get(key, default_value)



	@classmethod
	def table(cls, **attribs_with_values):
		return cls.instance.with_attrs(attribs_with_values)



	def _create_instance(self):
		return SimpleAttributeTable()



	def with_values(self, **attribs_with_values):
		return self.with_attrs(attribs_with_values)



	def with_attr(self, attribute, value):
		v = _AttributeValueSingle(attribute, value)
		derived = self._single_value_derived_tables.get(v)
		if derived is None:
			derived = self._create_instance()
			derived._values.update(self._values)
			derived._values[attribute] = value
			derived = self._get_unqiue_attribute_table(derived)
			self._single_value_derived_tables[v] = derived
		return derived


	def with_attrs(self, attrs):
		if len(attrs) == 1:
			attr, value = attrs.items()[0]
			return self.with_attr(attr, value)
		
		v = _AttributeValuesMultiple(attrs)
		derived = self._multi_value_derived_tables.get(v)
		if derived is None:
			derived = self._create_instance()
			derived._values.update(self._values)
			for attr, value in attrs.items():
				derived._values[attr] = value
			derived = self._get_unqiue_attribute_table(derived)
			self._multi_value_derived_tables[v] = derived
		return derived


	def with_attrs_from(self, attr_table):
		derived = self._attrib_table_derived_tables.get(attr_table)
		if derived is None:
			derived = self._create_instance()
			derived._values.update(self._values)
			derived._values.update(attr_table._values)
			derived = self._get_unqiue_attribute_table(derived)
			self._attrib_table_derived_tables[attr_table] = derived
		return derived


	def without_attr(self, attr):
		derived = self._del_value_derived_tables.get(attr)
		if derived is None:
			derived = self._create_instance()
			derived._values.update(self._values)
			del derived._values[attr]
			derived = self._get_unqiue_attribute_table(derived)
			self._del_value_derived_tables[attr] = derived
		return derived



	@classmethod
	def _get_attribute_table_set_for_class(cls):
		table_set = SimpleAttributeTable._attribute_table_sets_by_type.get(cls)
		if table_set is None:
			table_set = weakref.WeakValueDictionary()
			SimpleAttributeTable._attribute_table_sets_by_type[cls] = table_set
		return table_set


	@staticmethod
	def _get_unqiue_attribute_table(attr_table):
		table_set = SimpleAttributeTable._get_attribute_table_set_for_class()

		v = _AttributeValuesMultiple(attr_table._values)
		unique_table = table_set.get(v)
		if unique_table is None:
			table_set[v] = attr_table
			return attr_table
		else:
			return unique_table

		
SimpleAttributeTable.instance = SimpleAttributeTable()




class Test_attribute_table (unittest.TestCase):
	def test_construction(self):
		self.assertEquals(0, len(SimpleAttributeTable.instance._values))

		self.assertRaises(KeyError, lambda: SimpleAttributeTable.instance['a'])

		a2 = SimpleAttributeTable.table(a=2)
		self.assertEquals(1, len(a2._values))
		self.assertEquals(2, a2['a'])
		self.assertEquals(2, a2.get('a'))
		self.assertIs(None, a2.get('x'))
		del a2
		gc.collect()


	def test_derivation(self):
		self.assertIs(SimpleAttributeTable.instance.with_attr('a', 2), SimpleAttributeTable.instance.with_attr('a', 2))
		self.assertIs(SimpleAttributeTable.instance.with_attrs({'a': 2, 'b': -2}), SimpleAttributeTable.instance.with_attrs({'b': -2, 'a': 2}))
		self.assertIs(SimpleAttributeTable.instance.with_attrs({'a': 2}), SimpleAttributeTable.instance.with_attrs({'a': 2}))
		t1 = SimpleAttributeTable.table(a=-1, b=-2, c=-3)
		t2 = SimpleAttributeTable.table(c=-3, b=-2, a=-1)
		self.assertIs(t1, t2)
		self.assertIs(SimpleAttributeTable.instance.with_attrs_from(t1), SimpleAttributeTable.instance.with_attrs_from(t2))
		self.assertIs(t1.without_attr('b'), t1.without_attr('b'))
		self.assertIs(t1.with_attrs({'x': -1, 'y': -2}), t1.with_values(x=-1, y=-2))

		x = SimpleAttributeTable.instance.with_attr('a', -1)
		y = SimpleAttributeTable.instance.with_attr('b', -2)
		xx = x.with_attr('b', -2)
		yy = y.with_attr('a', -1)
		self.assertIs(xx, yy)

		gc.collect()


	def test_cleanup(self):
		x = SimpleAttributeTable.instance.with_attr('a', -1)
		y = SimpleAttributeTable.instance.with_attr('b', -2)
		xx = x.with_attr('b', -2)
		yy = y.with_attr('a', -1)

		wxx = weakref.ref(xx)

		gc.collect()
		self.assertTrue(wxx() is not None)

		del x
		del y
		del xx
		del yy
		gc.collect()
		self.assertFalse(wxx() is not None)

		self.assertEqual(0, len(SimpleAttributeTable.instance._single_value_derived_tables))


