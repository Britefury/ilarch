##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from IPython.display import display, Javascript


_global_dependencies = set()
_global_deps_version = 1



def _register_global_dependency(dep):
	global _global_deps_version
	_global_dependencies.add(dep)
	_global_deps_version += 1

def are_global_dependencies_up_to_date(version):
	return version == _global_deps_version

def get_global_dependencies():
	return _global_dependencies

def get_global_dependencies_version():
	return _global_deps_version





class GlobalDependency (object):
	def __init__(self):
		_register_global_dependency(self)

	def ipython_setup(self):
		raise NotImplementedError, 'abstract'



class GlobalCSS (GlobalDependency):
	def __init__(self, url):
		super(GlobalCSS, self).__init__()
		self.__url = url

	def ipython_setup(self):
		if self.__url is not None:
			display(Javascript(css=self.__url))
		else:
			raise RuntimeError, 'This should not have happened, due to being checked earlier'



class GlobalJS (GlobalDependency):
	def __init__(self, url=None, source=None):
		super(GlobalJS, self).__init__()
		self.__url = url
		self.__source = source
		if url is None  and  source is None:
			raise ValueError, 'either a URL or source text must be provided'

	def ipython_setup(self):
		if self.__url is not None:
			display(Javascript(url=self.__url))
		elif self.__source is not None:
			display(Javascript(self.__source))
		else:
			raise RuntimeError, 'This should not have happened, due to being checked earlier'


