##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
import inspect
from larch.core.abstract_perspective import AbstractPerspective
from larch.util.polymorphic_map import PolymorphicMap


class ObjectPresPerspective (AbstractPerspective):
	__present_method_name__ = NotImplemented
	__fallback_perspective__ = NotImplemented



	def __init__(self):
		self.__presenters = PolymorphicMap()



	def register_presenter(self, obj_type, presenter):
		self.__presenters[obj_type] = presenter
		return presenter


	# Decorator
	def presenter(self, obj_type):
		def deco_fn(presenter):
			self.register_presenter(obj_type, presenter)
		return deco_fn




	def present_model(self, model, fragment_view):
		if self.__present_method_name__ is NotImplemented:
			raise NotImplementedError, 'object pres perspective {0} appears to be abstract; __present_method_name__ not defined'.format(self)

		result = None

		try:
			present_method = getattr(model, self.__present_method_name__)
		except AttributeError:
			present_method = None

		if present_method is not None and  inspect.ismethod(present_method)  and  present_method.im_self is None:
			# Method is unbound - don't try to invoke
			present_method = None

		if present_method is not None:
			result = present_method(fragment_view)

		if result is None:
			# Try object presenters
			try:
				presenter = self.__presenters[type(model)]
			except KeyError:
				pass
			else:
				result = presenter(model, fragment_view)

		if result is None:
			if self.__fallback_perspective__ is NotImplemented:
				raise NotImplementedError, 'object pres perspective {0} appears to be abstract; __fallback_perspective__ not defined'.format(self)
			elif self.__fallback_perspective__ is not None:
				result = self.__fallback_perspective__.present_object(model, fragment_view)
			else:
				raise ValueError, 'Could not present {0}'.format(model)

		return result


