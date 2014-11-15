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
	"""
	def __init__(self, focus, perspective=None):
		self.focus = focus
		if perspective is None:
			perspective = DefaultPerspective.instance
		self.perspective = perspective
