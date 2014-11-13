##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
import cgi
from larch.core.dynamicpage.global_dependencies import GlobalCSS

from larch.pres.html import Html



GlobalCSS('/static/larch/python.css')


def _punct_html(x):
	return u'<span class="pyprim_punctuation">{0}</span>'.format(x)


_none = Html('<span class="pyprim_none">None</span>')
def present_none(x=None):
	return _none


_true = Html('<span class="pyprim_bool">True</span>')
_false = Html('<span class="pyprim_bool">False</span>')
def present_bool(x):
	return _true   if x   else _false


_quote = _punct_html('"')
_triple_quote = _punct_html('"""')

def present_string(x):
	xx = cgi.escape(x)
	print 'TODO: handle escape characters when presenting strings'
	if '\n' in x:
		lines = [u'<span class="pyprim_string">{0}</span>'.format(line)   for line in xx.split('\n')]
		lines[0] = _triple_quote + lines[0]
		lines[-1] += _triple_quote
		lines = [u'<div>{0}</div>'.format(line)   for line in lines]
		return Html(u''.join(lines))
	else:
		return Html(_quote + u'<span class="pyprim_string">{0}</span>'.format(xx) + _quote)


def present_int(x):
	return Html('<span class="pyprim_int">{0}</span>'.format(x))


def present_long(x):
	return Html('<span class="pyprim_long">{0}</span><span class="pyprim_punctuation">L</span>'.format(x))


def _present_si_real(txt, exp_index):
	return Html('<span class="pyprim_float">{0}*10</span><sup>{1}</sup></span>'.format(txt[:exp_index], txt[exp_index+1:]))


def present_float(x):
	s = str(x)
	if 'e' in s:
		return _present_si_real(s, s.index('e'))
	elif 'E' in s:
		return _present_si_real(s, s.index('E'))
	else:
		return Html('<span class="pyprim_float">{0}</span>'.format(s))


def present_complex(x):
	if x.real == 0.0:
		return Html(present_float(x.imag), _complex_j)
	else:
		return Html(_open_paren, present_float(x.real), _plus, present_float(x.imag), _complex_j + _close_paren)


_open_paren = _punct_html('(')
_close_paren = _punct_html(')')
_open_bracket = _punct_html('[')
_close_bracket = _punct_html(']')
_open_brace = _punct_html('{')
_close_brace = _punct_html('}')
_comma = _punct_html(',')
_comma_space = _punct_html(',') + ' '
_colon = _punct_html(':')
_plus = _punct_html('+')
_complex_j = '<span class="pyprim_complex_j">j</span>'



def present_tuple(xs):
	if len(xs) == 0:
		return Html(_open_paren + _close_paren)
	if len(xs) == 1:
		return Html(_open_paren, xs[0], _comma + _close_paren)
	else:
		contents = [_open_paren]
		first = True
		for x in xs:
			if not first:
				contents.append(_comma_space)
			contents.append(x)
			first = False
		contents.append(_close_paren)
		return Html(*contents)


def present_list(xs):
	contents = [_open_bracket]
	first = True
	for x in xs:
		if not first:
			contents.append(_comma_space)
		contents.append(x)
		first = False
	contents.append(_close_bracket)
	return Html(*contents)


def present_set(xs):
	contents = [_open_brace]
	first = True
	for x in xs:
		if not first:
			contents.append(_comma_space)
		contents.append(x)
		first = False
	contents.append(_close_brace)
	return Html(*contents)


def present_dict(xs):
	contents = [_open_brace]
	first = True
	for key, value in xs.items():
		if not first:
			contents.append(_comma_space)
		contents.append(key)
		contents.append(_colon)
		contents.append(value)
		first = False
	contents.append(_close_brace)
	return Html(*contents)


_present_data_fn_table = {
	type(None) : present_none,
	bool : present_bool,
	str : present_string,
	unicode : present_string,
	int : present_int,
	long : present_long,
	float : present_float,
	complex : present_complex,
	tuple : present_tuple,
	list : present_list,
	set : present_set,
	dict : present_dict
}

_small_primitive_types = {
	type(None), bool, str, unicode, int, long, float, complex
}

def is_small_primitive_data(x):
	return type(x) in _small_primitive_types

def is_primitive_data(x):
	return type(x) in _present_data_fn_table


def present_primitive_data(x):
	fn = _present_data_fn_table.get(type(x))
	if fn is not None:
		return fn(x)
	else:
		return None




_present_fn_table = {
	type(None) : present_none,
	bool : present_bool,
	str : present_string,
	unicode : present_string,
	int : present_int,
	long : present_long,
	float : present_float,
	complex : present_complex,
	tuple : present_tuple,
	list : present_list,
	set : present_set,
	dict : present_dict
}

def is_primitive(x):
	return type(x) in _present_fn_table


def present_primitive_object(x):
	fn = _present_fn_table.get(type(x))
	if fn is not None:
		return fn(x)
	else:
		return None


