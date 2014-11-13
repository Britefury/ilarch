##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
import json



class Key (object):
	def __init__(self, key_code, alt=None, ctrl=None, shift=None, meta=None):
		if isinstance(key_code, basestring):
			key_code = ord(key_code)
		elif isinstance(key_code, int)  or  key_code is None:
			pass
		else:
			raise TypeError, 'invalid key_code type; should be string, integer or None'
		self._key_code = key_code

		self._alt = alt
		self._ctrl = ctrl
		self._shift = shift
		self._meta = meta


	@property
	def key_code(self):
		return self._key_code

	@property
	def key_char(self):
		return chr(self._key_code)


	@property
	def alt(self):
		return self._alt

	@property
	def ctrl(self):
		return self._ctrl

	@property
	def shift(self):
		return self._shift

	@property
	def meta(self):
		return self._meta


	def __to_json__(self):
		k = {}

		if self._key_code is not None:
			k['keyCode'] = self._key_code

		if self._alt is not None:
			k['altKey'] = 1   if self._alt   else 0
		if self._ctrl is not None:
			k['ctrlKey'] = 1   if self._ctrl   else 0
		if self._shift is not None:
			k['shiftKey'] = 1   if self._shift   else 0
		if self._meta is not None:
			k['metaKey'] = 1   if self._meta   else 0

		return k




class KeyAction (Key):
	KEY_DOWN = 'KEY_DOWN'
	KEY_UP = 'KEY_UP'
	KEY_PRESS = 'KEY_PRESS'


	def __init__(self, event_type, key_code, alt=None, ctrl=None, shift=None, meta=None, prevent_default=False):
		if event_type != self.KEY_DOWN  and  event_type != self.KEY_UP  and  event_type != self.KEY_PRESS:
			raise ValueError, 'invalid event_type; should be KEY_DOWN, KEY_UP, or KEY_PRESS'
		self._event_type = event_type

		super(KeyAction, self).__init__(key_code, alt=alt, ctrl=ctrl, shift=shift, meta=meta)

		self._prevent_default = prevent_default


	@property
	def event_type(self):
		return self._event_type


	@property
	def prevent_default(self):
		return self._prevent_default


	def matches(self, filter):
		return (self._event_type == filter._event_type)  and\
		       (self._key_code == filter._key_code  or  filter._key_code is None)  and\
		       (self._alt == filter._alt  or  filter._alt is None)  and\
		       (self._ctrl == filter._ctrl  or  filter._ctrl is None)  and\
		       (self._shift == filter._shift  or  filter._shift is None)  and\
		       (self._meta == filter._meta  or  filter._meta is None)


	def __to_json__(self):
		k = {'event_type' : self._event_type}

		if self._key_code is not None:
			k['keyCode'] = self._key_code

		if self._alt is not None:
			k['altKey'] = 1   if self._alt   else 0
		if self._ctrl is not None:
			k['ctrlKey'] = 1   if self._ctrl   else 0
		if self._shift is not None:
			k['shiftKey'] = 1   if self._shift   else 0
		if self._meta is not None:
			k['metaKey'] = 1   if self._meta   else 0
		k['preventDefault'] = 1   if self._prevent_default   else 0

		return k


	@staticmethod
	def __from_json__(event_type, json):
		key_code = json.get('keyCode', 0)
		alt = json.get('altKey') == 1
		ctrl = json.get('ctrlKey') == 1
		shift = json.get('shiftKey') == 1
		meta = json.get('metaKey') == 1
		prevent_default = json.get('preventDefault') == 1
		return KeyAction(event_type, key_code, alt, ctrl, shift, meta, prevent_default)


	@staticmethod
	def __from_keydown_json__(json):
		return KeyAction.__from_json__(KeyAction.KEY_DOWN, json)


	@staticmethod
	def __from_keyup_json__(json):
		return KeyAction.__from_json__(KeyAction.KEY_UP, json)


	@staticmethod
	def __from_keypress_json__(json):
		return KeyAction.__from_json__(KeyAction.KEY_PRESS, json)


