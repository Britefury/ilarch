##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch.core.abstract_perspective import AbstractPerspective
from larch.inspector.primitive import present_primitive_data, is_small_primitive_data, present_string
from larch.controls.expander import dropdown_expander
from larch.pres.obj_pres import horizontal_field, vertical_field
from larch.pres.html import Html


def _field(name, x):
	value = x.__dict__[name]
	if is_small_primitive_data(value):
		return horizontal_field(name, value)
	else:
		return vertical_field(name, value)

def present_python_object(x, fragment_view):
	if hasattr(x, '__dict__'):
		attr_names = sorted(x.__dict__.keys())
		attrs = [_field(name, x)   for name in attr_names]
		attrs = Html(*attrs)

		t = Html.div(dropdown_expander(Html('Type'), type(x)))
		a = Html.div(dropdown_expander(Html('Attributes'), attrs))   if attrs is not None  else None
		s = Html.div(dropdown_expander(Html('repr'), present_string(repr(x))))
		return Html('<div class="pythonobject">', Html(t, a, s)   if a is not None   else Html(t, s), '</div>')
	else:
		t = Html.div(dropdown_expander(Html('Type'), type(x)))
		s = Html.div(present_string(repr(x)))
		return Html('<div class="pythonobject">', Html(t, s), '</div>')



class LLInspectorPerspective (AbstractPerspective):
	def present_model(self, model, fragment_view):
		p = present_primitive_data(model)
		if p is not None:
			return p
		else:
			return present_python_object(model, fragment_view)

LLInspectorPerspective.instance = LLInspectorPerspective()

llinspect = LLInspectorPerspective.instance
