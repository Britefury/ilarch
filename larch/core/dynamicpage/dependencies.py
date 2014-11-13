##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************


class PageDependency (object):
	def __init__(self, deps=None):
		if deps is None:
			deps = []

		self.__deps = deps


	@property
	def dependencies(self):
		return self.__deps


	def to_html(self):
		raise NotImplementedError, 'abstract'



class _RegisteredDependency (PageDependency):
	_deps = None

	@classmethod
	def dep_for(cls, x):
		dep = cls._deps.get(x)
		if dep is None:
			dep = cls(x)
			cls._deps[x] = dep
		return dep



class CSSURLDependency (_RegisteredDependency):
	_deps = {}

	def __init__(self, url, deps=None):
		super(CSSURLDependency, self).__init__(deps)
		self.__url = url

	def to_html(self):
		return '<link rel="stylesheet" type="text/css" href="{0}"/>'.format(self.__url)




class JSURLDependency (_RegisteredDependency):
	_deps = {}

	def __init__(self, url, deps=None):
		super(JSURLDependency, self).__init__(deps)
		self.__url = url

	def to_html(self):
		return '<script type="text/javascript" src="{0}"></script>'.format(self.__url)



class CSSSourceDependency (_RegisteredDependency):
	_deps = {}

	def __init__(self, source, deps=None):
		super(CSSSourceDependency, self).__init__(deps)
		self.__source = source

	def to_html(self):
		return '<style>\n{0}\n</style>'.format(self.__source)



class JSSourceDependency (_RegisteredDependency):
	_deps = {}

	def __init__(self, source, deps=None):
		super(JSSourceDependency, self).__init__(deps)
		self.__source = source

	def to_html(self):
		return '<script type="text/javascript">\n{0}\n</script>'.format(self.__source)

