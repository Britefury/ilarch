##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch.pres.pres import Pres, ApplyPerspective


class AbstractPerspective (object):
	def present_model(self, model, fragment_view):
		raise NotImplementedError, 'abstract'


	def present_object(self, x, fragment_view):
		if isinstance(x, Pres):
			return x
		else:
			return self.present_model(x, fragment_view)


	def apply_to(self, x):
		return ApplyPerspective(self, x)

	def __call__(self, x):
		return ApplyPerspective(self, x)
