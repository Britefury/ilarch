##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch.core.abstract_perspective import AbstractPerspective
from larch.inspector.llinspector import llinspect
from larch.inspector.primitive import present_primitive_object
from larch.inspector.python_constructs import present_python


class InspectorPerspective (AbstractPerspective):
	def present_model(self, model, fragment_view):

		p = present_primitive_object(model)
		if p is not None:
			return p

		p = present_python(model)
		if p is not None:
			return p

		return llinspect.present_object(model, fragment_view)


InspectorPerspective.instance = InspectorPerspective()

inspect = InspectorPerspective.instance
