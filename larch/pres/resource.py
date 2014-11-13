##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
import json
import os

import mimetypes

from larch.core.dynamicpage.segment import HtmlContent
from larch.live import LiveFunction
from larch.pres import pres, html
from larch.core.subject import Subject
from larch import msg, js


class AbstractResource (pres.Pres, js.JS):
	requires_url = False

	def page_ref(self, pres_ctx, rsc_instance):
		pass

	def page_unref(self, pres_ctx, rsc_instance):
		pass

	def on_message(self, rsc_instance, message):
		pass


	def build(self, pres_ctx):
		return HtmlContent([])

	def build_js(self, pres_ctx):
		raise NotImplementedError, 'abstract'

	def _get_instance(self, pres_ctx):
		return pres_ctx.fragment_view.get_resource_instance(self, pres_ctx)




class MessageChannel (AbstractResource):
	def __init__(self):
		self.__message_listeners = []
		self.__instances = set()


	def page_ref(self, pres_ctx, rsc_instance):
		self.__instances.add(rsc_instance)

	def page_unref(self, pres_ctx, rsc_instance):
		self.__instances.remove(rsc_instance)


	def add_listener(self, listener):
		self.__message_listeners.append(listener)

	def remove_listener(self, listener):
		self.__message_listeners.remove(listener)


	def send(self, message):
		m = msg.message('message', message=message)
		for instance in self.__instances:
			instance.send_resource_message(m)

	def on_resource_message(self, rsc_instance, message):
		for listener in self.__message_listeners:
			listener(message)


	def build_js(self, pres_ctx):
		instance = self._get_instance(pres_ctx)
		j = js.JSCall('larch.__createChannelResource', [instance.id])
		return j.build_js(pres_ctx)






class URLResource (AbstractResource):
	requires_url = True

	def __init__(self):
		pass


	def get_data(self):
		raise NotImplementedError, 'abstract'

	def get_mime_type(self):
		raise NotImplementedError, 'abstract'

	def build(self, pres_ctx):
		return HtmlContent([self._url(pres_ctx)])

	def build_js(self, pres_ctx):
		instance = self._get_instance(pres_ctx)
		j = js.JSCall('larch.__createURLResource', [instance.id, instance.resource_url])
		return j.build_js(pres_ctx)

	def _url(self, pres_ctx):
		rsc_instance = pres_ctx.fragment_view.get_resource_instance(self, pres_ctx)
		return rsc_instance.resource_url




class ConstResource (URLResource):
	def __init__(self, data, mime_type):
		super(ConstResource, self).__init__()
		self.__data = data
		self.__mime_type = mime_type


	def get_data(self):
		return self.__data

	def get_mime_type(self):
		return self.__mime_type



class JsonResource (ConstResource):
	def __init__(self, data):
		super(JsonResource, self).__init__(json.dumps(data), 'application/json')



class CSVResource (ConstResource):
	def __init__(self, data):
		super(CSVResource, self).__init__(data, 'text/csv')



class FnResource (URLResource):
	def __init__(self, data_fn, mime_type):
		super(FnResource, self).__init__()
		self.__data_fn = data_fn
		self.__mime_type = mime_type


	def get_data(self):
		return self.__data_fn()

	def get_mime_type(self):
		return self.__mime_type





class JsonFnResource (FnResource):
	def __init__(self, data_fn):
		super(JsonFnResource, self).__init__(lambda: json.dumps(data_fn()), 'application/json')



class CSVFnResource (FnResource):
	def __init__(self, data_fn):
		super(CSVFnResource, self).__init__(data_fn(), 'text/csv')





class LiveFnResource (URLResource):
	def __init__(self, data_fn, mime_type):
		self.__data_fn = LiveFunction(data_fn)
		self.__mime_type = mime_type
		self.__instances = []
		self.__ref_count = 0

	def page_ref(self, pres_ctx, rsc_instance):
		self.__instances.append(rsc_instance)
		if self.__ref_count == 0:
			self.__data_fn.add_listener(self.__live_listener)
		self.__ref_count += 1


	def page_unref(self, pres_ctx, rsc_instance):
		self.__ref_count -= 1
		if self.__ref_count == 0:
			self.__data_fn.remove_listener(self.__live_listener)
		self.__instances.remove(rsc_instance)


	def __live_listener(self, incr):
		modified_message = msg.message('modified')
		for instance in self.__instances:
			instance.send_resource_message(modified_message)


	def get_data(self):
		return self.__data_fn()

	def get_mime_type(self):
		return self.__mime_type



class JsonLiveFnResource (LiveFnResource):
	def __init__(self, data_fn):
		super(JsonLiveFnResource, self).__init__(lambda: json.dumps(data_fn()), 'application/json')



class CSVLiveFnResource (LiveFnResource):
	def __init__(self, data_fn):
		super(CSVLiveFnResource, self).__init__(data_fn, 'text/csv')





class ImageFromFile (URLResource):
	def __init__(self, filename, width=None, height=None):
		super(ImageFromFile, self).__init__()
		self.__filename = filename
		self.__width = width
		self.__height = height
		self.__data = None
		self.__mime_type = ''



	def get_data(self):
		if self.__data is None:
			if os.path.exists(self.__filename)  and  os.path.isfile(self.__filename):
				f = open(self.__filename, 'rb')
				self.__data = f.read()
				self.__mime_type = mimetypes.guess_type(self.__filename)[0]
				f.close()
		return self.__data

	def get_mime_type(self):
		return self.__mime_type


	def build(self, pres_ctx):
		url = self._url(pres_ctx)
		w = ' width="{0}"'.format(self.__width)   if self.__width is not None   else ''
		h = ' height="{0}"'.format(self.__height)   if self.__height is not None   else ''
		return HtmlContent(['<img src="', url, '"{0}{1}>'.format(w, h)])




class ImageFromBinary (ConstResource):
	def __init__(self, data, mime_type, width=None, height=None):
		super(ImageFromBinary, self).__init__(data, mime_type)
		self.__width = width
		self.__height = height



	def build(self, pres_ctx):
		url = self._url(pres_ctx)
		w = ' width="{0}"'.format(self.__width)   if self.__width is not None   else ''
		h = ' height="{0}"'.format(self.__height)   if self.__height is not None   else ''
		return HtmlContent(['<img src="', url, '"{0}{1}>'.format(w, h)])




class SubjectResource (URLResource):
	def __init__(self, subject):
		super(SubjectResource, self).__init__()
		self.__subject = subject
		self.__data = None
		self.__mime_type = ''


	def page_ref(self, pres_ctx, rsc_instance):
		if self.__data is None:
			self.__data = pres_ctx.fragment_view.service.page_for_subject(self.__subject, rsc_instance.resource_url.strip('/'))
			self.__mime_type = 'text/html'


	def get_data(self):
		return self.__data

	def get_mime_type(self):
		return self.__mime_type




class PresResource (URLResource):
	def __init__(self, contents):
		super(PresResource, self).__init__()
		self.__contents = contents
		self.__data = None
		self.__mime_type = ''


	def page_ref(self, pres_ctx, rsc_instance):
		subj = Subject()
		subj.add_step(focus=self.__contents, perspective=pres_ctx.perspective, title='Resource')
		self.__data = pres_ctx.fragment_view.service.page_for_subject(subj, rsc_instance.resource_url.strip('/'))
		self.__mime_type = 'text/html'


	def get_data(self):
		return self.__data

	def get_mime_type(self):
		return self.__mime_type





class SubjectIFrame (SubjectResource):
	def __init__(self, subject, width, height):
		super(SubjectIFrame, self).__init__(subject)
		self.__width = width
		self.__height = height



	def build(self, pres_ctx):
		url = self._url(pres_ctx)
		w = ' width="{0}"'.format(self.__width)   if self.__width is not None   else ''
		h = ' height="{0}"'.format(self.__height)   if self.__height is not None   else ''
		return HtmlContent(['<iframe src="{0}"{1}{2}></iframe>'.format(url, w, h)])



class PresIFrame (PresResource):
	def __init__(self, contents, width, height):
		super(PresIFrame, self).__init__(contents)
		self.__width = width
		self.__height = height



	def build(self, pres_ctx):
		url = self._url(pres_ctx)
		w = ' width="{0}"'.format(self.__width)   if self.__width is not None   else ''
		h = ' height="{0}"'.format(self.__height)   if self.__height is not None   else ''
		return HtmlContent(['<iframe src="{0}"{1}{2}></iframe>'.format(url, w, h)])






class SubjectLink (SubjectResource):
	def __init__(self, subject, link_content):
		super(SubjectLink, self).__init__(subject)
		self.__link_content = html.Html.coerce(link_content)



	def build(self, pres_ctx):
		url = self._url(pres_ctx)
		content = self.__link_content.build(pres_ctx)
		return HtmlContent(['<a href="{0}" target="_blank">'.format(url), content, '</a>'])




class PresLink (PresResource):
	def __init__(self, contents, link_content):
		super(PresLink, self).__init__(contents)
		self.__link_content = html.Html.coerce(link_content)



	def build(self, pres_ctx):
		url = self._url(pres_ctx)
		content = self.__link_content.build(pres_ctx)
		return HtmlContent(['<a href="{0}" target="_blank">'.format(url), content, '</a>'])

