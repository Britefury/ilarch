##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************



class Event (object):
	def __init__(self, page, segment, event_name, event_data):
		self.__page = page
		self.__segment = segment
		self.__event_name = event_name
		self.__event_data = event_data


	@property
	def page(self):
		return self.__page.public_api

	@property
	def segment(self):
		return self.__segment

	@property
	def fragment(self):
		if self.__segment is not None:
			return self.__segment.fragment
		else:
			inc_view = self.__page.inc_view
			if inc_view is not None:
				return inc_view.root_fragment_view
			else:
				return None

	@property
	def name(self):
		return self.__event_name

	@property
	def data(self):
		return self.__event_data
