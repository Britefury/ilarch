##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
import traceback

from larch.pres.obj_pres import error_box
from larch.pres.html import Html




def present_exception_no_traceback(exc):
	content = Html('<span class="exception_name">{0}</span>'.format(type(exc).__name__), '<br>',
		       '<span class="exception_message">{0}</span>'.format(Html.escape_str(exc.message)))
	return error_box('Exception', content)


def present_exception_with_traceback(exc, val, tb):
	traceback_str = '<br>\n'.join(Html.escape_str(traceback.format_exc(tb)).split('\n'))
	content = Html('<span class="exception_name">{0}</span>'.format(type(exc).__name__), '<br>',
		       '<span class="exception_message">{0}</span>'.format(Html.escape_str(exc.message)), '<br>',
		       '<span class="exception_message">{0}</span>'.format(Html.escape_str(str(val))), '<br>',
		       '<div class="exception_traceback">{0}</div>'.format(traceback_str))
	return error_box('Exception', content)



def exc_box_to_html_src(caption, contents_str):
	return '<div class="error_box"><span class="error_box_caption">{0}</span><br><div class="error_box_content">{1}</div></div>'.format(caption, contents_str)


def exception_to_html_src(exc, val, tb):
	traceback_str = '<br>\n'.join(Html.escape_str(traceback.format_exc(tb)).split('\n'))
	val_str = '<br>\n'.join(Html.escape_str(str(val)).split('\n'))
	content = ('<span class="exception_name">{0}</span><br>' + \
		  '<span class="exception_message">{1}</span><br>' + \
		  '<span class="exception_message">{2}</span><br>' + \
		  '<div class="exception_traceback">{3}</div>').format(type(exc).__name__, Html.escape_str(exc.message), val_str, traceback_str)
	return exc_box_to_html_src('Exception', content)
