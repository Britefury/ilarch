##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch.default_perspective import DefaultPerspective






class Subject (object):
	"""
	Subject

	A subject provides the content that is to be displayed within a page. It is part of the location resolution mechanism
	in which the path part of the URL is used to traverse through a hierarchy of content to find the target page.

	Subjects are built by adding steps. Each step consists of a dictionary mapping attribute names to values.
	The value of an attribute can be retrieved (getting the value for that attribute in the *LAST* step that has a value for it) either by calling
	the get_attr method or by accessing it as an attribute.
	Alternatively, an attribute value can be accumulated using the reduce method. Its operation is similar to that of the
	Python reduce function. The values that are used in the accumulation process are those obtained by retrieving
	values from each step that has a value for the attribute.

	There are a few special attributes that should be noted:

		focus - the object that is the focus of the subject
		perspective - the perspective used to present it
		location_trail - each entry should be a list of names that make up steps in the path of the URL used to access this subject. The location property generates a path from these



	Implementing location resolution

	On your objects that will be traversed while resolving a location, you can define the following methods:

	Define __resolve__ to loop up child objects by name; an identifier that is part of the URL, between the slahes
	def __resolve__(self, name, subject):
		target = self.look_up_child_content(name)
		if target is not None:
			# add a step the subject, setting the focus to the target:
			subject.add_step(focus=target)
			return target
		else:
			# Target not found; return None
			return None

	For example, packages within a project define a __resolve__ method that looks up the child entity of that name


	Define __resolve_self__ to 'forward' to a child object
	def __resolve_self__(self, subject):
		subject.add_step(focus=self.child)
		return self.child

	For example, pages within a project define __resolve_self__ to 'forward' to the content within the page.
	"""
	class __NoInitialValue (object):
		pass

	__NoInitialValue.instance = __NoInitialValue()

	def __init__(self):
		self.__steps = []



	@property
	def perspective(self):
		"""
		:return: The perspective, or the default perspective if the subject does not specify a perspective in any of its steps
		"""
		p = self.get_attr('perspective')
		return DefaultPerspective.instance   if p is None   else p


	@property
	def location(self):
		"""
		:return: The location represented by this subject
		"""
		trail = self.reduce('location_trail', lambda cumulative, t: t + cumulative, [])
		loc = '/'.join(trail)
		if loc.startswith('/'):
			return loc
		else:
			return '/' + loc


	@property
	def focii(self):
		"""
		:return: A list of (unique) focii, in reverse step order
		"""
		return self.reduce('focus', lambda cumulative, t: ([t] + cumulative)   if t not in cumulative   else cumulative, [])



	def add_step(self, **attributes):
		"""
		Add a step to the subject

		:param attributes: the attributes that make up the step
		"""
		self.__steps.append(attributes)


	def get_attr(self, item):
		"""Get a named attribute

		:param item: - the name of the attribute
		:raises AttributeError: if no attribute named :param item: can be found
		"""
		for step in reversed(self.__steps):
			try:
				return step[item]
			except KeyError:
				pass
		raise AttributeError, 'Subject has no attribute {0}'.format(item)


	def optional_attr(self, item, default_value=None):
		"""Get an optional named attribute, returning a default value if not found

		:param item: - the name of the attribute
		:param default_value: the default value to return if not found
		:return: None if no attribute named :param item: can be found, otherwise :param default_value:
		"""
		for step in reversed(self.__steps):
			try:
				return step[item]
			except KeyError:
				pass
		return default_value


	def __getattr__(self, item):
		"""Get a named attribute

		:param item: - the name of the attribute
		"""
		return self.get_attr(item)


	def reduce(self, item, reduce_fn, initial_value=__NoInitialValue.instance):
		"""Accumulate values of a named attribute by reduction, from last to first step

		:param item: - the name of the attribute
		:param reduce_fn: - a reduction function of the form function(cumulative_value, value) -> cumulative_value
		:param initial_value: an initial value to pass to the reduction function at the start of the accumulation process

		Note that the direction proceeds from tip to root
		"""
		for step in reversed(self.__steps):
			try:
				value = step[item]
			except KeyError:
				continue

			if initial_value is self.__NoInitialValue.instance:
				initial_value = value
			else:
				initial_value = reduce_fn(initial_value, value)

		if initial_value is self.__NoInitialValue.instance:
			raise AttributeError, 'Subject has no attribute {0}'.format(item)
		else:
			return initial_value


