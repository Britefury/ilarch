##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************

try:
	from greenlet import greenlet, getcurrent, GreenletExit
except ImportError:
	coroutine = None
else:
	def coroutine(f):
		return greenlet(f)

	def terminate(co):
		co.throw(GreenletExit)

