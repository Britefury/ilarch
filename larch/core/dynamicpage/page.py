##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
import threading
import sys

import json

from copy import copy
from larch import js

from larch.util import priority_list
from larch.core.dynamicpage.segment import DynamicSegment, SegmentRef
from larch.core.dynamicpage.event import Event
from larch.core.dynamicpage import messages, dependencies, global_dependencies
from larch.inspector import present_exception


_page_content = u"""
<!doctype html>
<html>
	<head>
		<title>{title}</title>
		<link rel="stylesheet" type="text/css" href="/static/jquery/css/ui-lightness/jquery-ui-1.10.2.custom.min.css"/>
		<link rel="stylesheet" type="text/css" href="/static/larch/larch.css"/>

		<script type="text/javascript" src="/static/jquery/js/jquery-1.9.1.js"></script>
		<script type="text/javascript" src="/static/jquery/js/jquery-ui-1.10.2.custom.min.js"></script>
		<script type="text/javascript" src="/static/jquery/js/jquery.cookie.js"></script>
		<script type="text/javascript" src="/static/noty/jquery.noty.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/bottom.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/bottomLeft.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/bottomCenter.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/bottomRight.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/center.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/centerLeft.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/centerRight.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/inline.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/top.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/topLeft.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/topCenter.js"></script>
		<script type="text/javascript" src="/static/noty/layouts/topRight.js"></script>
		<script type="text/javascript" src="/static/noty/themes/default.js"></script>
		<script type="text/javascript" src="/static/json2.js"></script>
		<script type="text/javascript" src="/static/larch/larch.js"></script>
		<script type="text/javascript">
			<!--
			larch.__view_id="{view_id}";
			larch.__doc_url = "{doc_url}";
			// -->
		</script>

		<!--scripts and css introduced by dependencies-->
		{dependency_tags}

		<!--initialisers; expressions that must be executed to initialise elements or the page-->
		<script type="text/javascript">
			<!--
			$(document).ready(function(){{larch.__onDocumentReady({initialisers});}});
			{init_script}
			// -->
		</script>
	</head>

	<body>
	{content}

	<!-- refresh on back button, adapted from http://www.webdeveloper.com/forum/showthread.php?137518-How-to-refresh-page-after-clicking-quot-Back-quot-button -->
	<input type="hidden" id="__larch_refreshed" value="0">
	<script type="text/javascript">
		onload = function(){{
			var refresh_elem =document.getElementById("__larch_refreshed");
			if(refresh_elem.value=="0") {{
				refresh_elem.value="1";
			}}
			else {{
				refresh_elem.value="0";
				location.reload();
			}}
		}}
	</script>

	</body>
</html>
"""



class EventHandleError (object):
	def __init__(self, event_name, event_seg_id, event_model_type_name, handler_seg_id, handler_model_type_name, exception, exc_value, traceback):
		self.event_name = event_name
		self.event_seg_id = event_seg_id
		self.event_model_type_name = event_model_type_name
		self.handler_seg_id = handler_seg_id
		self.handler_model_type_name = handler_model_type_name
		self.err_html = present_exception.exception_to_html_src(exception, exc_value, traceback)


	def to_message(self):
		return messages.error_handling_event_message(self.err_html, self.event_name, self.event_seg_id, self.event_model_type_name, self.handler_seg_id, self.handler_model_type_name)



def _rsc_retrieve_error_message(rsc_seg_id, rsc_model_type_name, exception, exc_value, traceback):
	err_html = present_exception.exception_to_html_src(exception, exc_value, traceback)
	return messages.error_retrieving_resource(err_html, rsc_seg_id, rsc_model_type_name)



class UnusedSegmentsError (Exception):
	def __init__(self, unused_segment_ids):
		super(UnusedSegmentsError, self).__init__('Segments created but not used: {0}'.format(unused_segment_ids))
		self.unused_segment_ids = unused_segment_ids



class DynamicPagePublicAPI (object):
	"""
	The public API for DynamicPage

	This API provides functions for performing page-level operations, e.g. executing Javascript code that should not be attached to a specific
	piece of content

	Rather than hand over an instance of DynamicPage, we pass one of these, which wraps it and provides the required API.
	"""
	def __init__(self, page):
		self._page = page


	@property
	def subject(self):
		"""
		:return: The subject
		"""
		inc_view = self._page.inc_view
		return inc_view.subject   if inc_view is not None   else None



	def page_js_eval(self, expr):
		"""
		Schedule a page-level script to be executed

		:param expr: the Javascript script to execute, either in the form of a js.JS subclass or a string
		:return: None
		"""
		if isinstance(expr, basestring):
			expr = js.JSExprSrc(expr)
		elif not isinstance(expr, js.JS):
			raise TypeError, 'Javascript expression must be a string or a JS object'

		# TODO: passing None as the presentation context will cause Resource instances to break
		expr_src = expr.build_js(None)

		self._page.queue_js_to_execute(expr_src)
		# Notifying the page of a modification causes it to schedule a refresh, which will cause the script to be executed
		self._page._notify_page_modified()


	def page_js_function_call(self, js_fn_name, *args):
		"""
		Convenience function for scheduling a Javascript function call (constructs an expression and passes it over to page_js_eval.

		:param js_fn_name: the name of the function to call
		:param args: the arguments to pass
		:return: None
		"""
		self.page_js_eval(js.JSCall(js_fn_name, args))


	@property
	def focused_segment(self):
		"""
		The focused segment
		"""
		return self._page.focused_segment





class DynamicPage (object):
	__FIX_HTML_STRUCTURE_PARAM_NAME = 'fix_html_structure'
	_REFRESH_PRIORITY = -1000000

	"""
	A dynamic web page, composed of segments.

	Create segments by calling the new_segment method. Remove them with remove_segment when you are done.

	:param service: The dynamic page service that spawned this page
	:param view_id: The view ID used to identify this page
	:param location: The browser location
	:param get_params: The parameters that were provided as part of the location

	You must create and set the root segment before using the page. Create using new_segment, then set the root_segment attribute.

	"""
	def __init__(self, service, view_id):
		self.__service = service
		self._view_id = view_id

		print 'Warning, structure fixing was enabled by HTTP GET parameters, re-implementation required'
		self._enable_structure_fixing = False

		self.__public_api = DynamicPagePublicAPI(self)

		self._table = _SegmentTable(self)

		# Popups
		self._popup_segment_id_to_close_function = {}

		self.__queued_tasks = priority_list.PriorityList()
		self.__queue_synchronize_callbacks = []

		# Global dependencies
		self.__global_deps_version = 0
		self.__global_deps = set()

		# Page event handlers
		self.__page_event_handlers = []

		# Dependencies
		self.__dependencies = []
		self.__all_dependencies = set()

		# Page modification message and flag
		self.__page_modifications_message = None
		self.__page_modified = False

		# Queue of JS expressions that must be executed; will be put on the client in one batch later
		self.__js_queue = []
		self.__execute_js_message = None
		self.__segment_id_to_queued_scripts = {}

		# Segments with invalid structure
		self.__segments_with_invalid_html_structure = set()
		self.__segment_html_structure_fixes = {}

		# Page reload queued
		self.__queued_page_reload = None

		# The root segment
		self.__root_segment = None

		# Focused segment
		self.__focused_segment = None

		# Resources
		self.__rsc_id_counter = 1
		self.__rsc_id_to_rsc_instance = {}
		self.__url_rsc_id_to_rsc_instance = {}
		self.__resource_to_resource_instance = {}
		self.__resource_id_and_message_pairs = []
		self.__disposed_rsc_instance_ids = set()
		self.__resource_error_messages = []

		# Segment dispose listeners
		self.__segment_dispose_listeners = {}

		# Threading lock, required for servers such as CherryPy
		self.__lock = None

		# Incremental view
		self.__inc_view = None


		# Register the broken HTML structure event handler
		self.add_page_event_handler('notify_popup_closed', self.__notify_popup_closed)
		self.add_page_event_handler('broken_html_structure', self.__on_broken_html_structure)
		self.add_page_event_handler('resource_message', self.__on_resource_message)
		self.add_page_event_handler('close_page', self.__on_close_page)




	@property
	def service(self):
		return self.__service


	@property
	def public_api(self):
		return self.__public_api



	@property
	def inc_view(self):
		return self.__inc_view

	@inc_view.setter
	def inc_view(self, value):
		self.__inc_view = value



	#
	#
	# Threads/locking
	#
	#

	def lock(self):
		if self.__lock is None:
			self.__lock = threading.Lock()
		self.__lock.acquire()

	def unlock(self):
		if self.__lock is not None:
			self.__lock.release()




	#
	#
	# Broken HTML structure event handler
	#
	#

	def __on_broken_html_structure(self, event):
		raise NotImplementedError
		if self.__FIX_HTML_STRUCTURE_PARAM_NAME not in self.__get_params:
			get_params = {}
			get_params.update(self.__get_params)

			get_params[self.__FIX_HTML_STRUCTURE_PARAM_NAME] = ''

			# The HTML structure is broken
			self.queue_page_reload(None, get_params)




	#
	#
	# Close page event handler
	#
	#

	def __on_close_page(self, event):
		print 'CLOSING PAGE {0}'.format(self._view_id)
		self.__service._close_page(self)





	#
	#
	# Dependencies
	#
	#

	def add_dependency(self, dep):
		"""Register a dependency; such as a JS script or a CSS stylesheet

		dep - the dependency to register
		"""
		if not isinstance(dep, dependencies.PageDependency):
			raise TypeError, 'Dependencies must be an instance of DocumentDependency'

		if dep not in self.__all_dependencies:
			self.__all_dependencies.add(dep)

			for d in dep.dependencies:
				self.add_dependency(d)

			self.__dependencies.append(dep)







	#
	#
	# Segment creation and destruction
	#
	#


	def new_segment(self, content=None, desc=None, fragment=None):
		"""
		Create a new segment

		:param content: an HTMLContent instance that contains the content of the segment that is to be created (or None, in which case you must initialise it by setting the segment's content attribute/property
		:param desc: a description string that is appended to the segment's ID. This is passed to the browser in order to allow you to figure out what e.g. seg27 is representing.
		:param fragment: the segment's containing fragment
		:return: the new segment
		"""
		return self._table._new_segment(content, desc, fragment)

	def remove_segment(self, segment):
		"""Remove a segment from the page. You should remove segments when you don't need them anymore.
		"""
		if segment is self.__focused_segment:
			self.__focused_segment = None

		if self._enable_structure_fixing:
			if segment in self.__segments_with_invalid_html_structure:
				self.__segments_with_invalid_html_structure.remove(segment)
				self._check_for_structurally_valid_page()
		self._table._remove_segment(segment)

		seg_id = segment.id
		if seg_id in self.__segment_dispose_listeners:
			for listener in self.__segment_dispose_listeners[seg_id]:
				listener(segment)
			del self.__segment_dispose_listeners[seg_id]



	def add_segment_dispose_listener(self, segment, listener_fn):
		"""
		Add a segment dispose listener. The listener is invoked when the attached segment is disposed of.

		:param segment: the segment to receive events for
		:param listener_fn: the listener function of the form function(segment)
		:return: None
		"""
		self.__segment_dispose_listeners.setdefault(segment.id, list()).append(listener_fn)




	#
	#
	# Popups
	#
	#

	def new_popup_segment(self, initialisation_js_src, on_close, content=None, desc=None, fragment=None):
		"""
		Create a new popup segment

		:param initialisation_js_src: Javascript source that will show the popup
		:param on_close: close function, invoked to perform cleanup when the popup is closed on the client, takes the form function()
		:param content: an HTMLContent instance that contains the content of the segment that is to be created (or None, in which case you must initialise it by setting the segment's content attribute/property
		:param desc: a description string that is appended to the segment's ID. This is passed to the browser in order to allow you to figure out what e.g. seg27 is representing.
		:param fragment: the segment's containing fragment
		:return: the new segment
		"""
		seg = self.new_segment(content, desc, fragment)
		self._table._add_popup_segment(seg, initialisation_js_src)
		self._popup_segment_id_to_close_function[seg.id] = on_close
		return seg


	def __notify_popup_closed(self, event):
		content_segment_id = event.data
		close_fn = self._popup_segment_id_to_close_function.get(content_segment_id)
		if close_fn is not None:
			close_fn()
			del self._popup_segment_id_to_close_function[content_segment_id]




	#
	#
	# QUEUED SEGMENT SCRIPTS
	#
	#

	def _queue_segment_script(self, segment_id, script):
		scripts = self.__segment_id_to_queued_scripts.get(segment_id)
		if scripts is None:
			self.__segment_id_to_queued_scripts[segment_id] = [script]
		else:
			scripts.append(script)
		self._notify_page_modified()




	#
	#
	# Resources
	#
	#

	def get_resource_instance(self, resource, pres_ctx):
		"""
		Get an instance of a resource

		If an instance of the specified resource has already been created, the existing instance will be returned

		:param resource: a resource
		:param pres_ctx: context data, used by the resource object at initialisation and disposal time
		:return: the resource instance
		"""
		rsc_instance = self.__resource_to_resource_instance.get(resource)
		if rsc_instance is None:
			rsc_id = 'r{0}'.format(self.__rsc_id_counter)
			self.__rsc_id_counter += 1
			rsc_instance = DynamicPageResourceInstance(self, rsc_id, resource)
			self.__rsc_id_to_rsc_instance[rsc_id] = rsc_instance

		rsc_instance.ref(pres_ctx)

		return rsc_instance


	def unref_resource_instance(self, rsc_instance):
		if rsc_instance.unref() == 0:
			del self.__rsc_id_to_rsc_instance[rsc_instance.id]


	def _send_resource_message(self, rsc_instance, message):
		"""Notify of resource modification
		"""
		pair = (rsc_instance.id, message)
		self.__resource_id_and_message_pairs.append(pair)


	def _resource_disposed(self, rsc_instance):
		"""Notify of resource disposal
		"""
		self.__disposed_rsc_instance_ids.add(rsc_instance.id)


	def __on_resource_message(self, event):
		resource_id = event.data['resource_id']
		message = event.data['message']
		rsc_instance = self.__rsc_id_to_rsc_instance.get(resource_id)
		rsc_instance.on_resource_message(message)



	def __resource_msgs_message(self):
		if len(self.__resource_id_and_message_pairs) > 0:
			pairs = [pair   for pair in self.__resource_id_and_message_pairs   if pair[0] not in self.__disposed_rsc_instance_ids]
			rsc_mod_message = messages.resource_messages_message(pairs)
			self.__resource_id_and_message_pairs = []
			return rsc_mod_message
		else:
			return None


	def __resources_disposed_message(self):
		if len(self.__disposed_rsc_instance_ids) > 0:
			rsc_disp_message = messages.resources_disposed_message(self.__disposed_rsc_instance_ids)
			self.__disposed_rsc_instance_ids = set()
			return rsc_disp_message
		else:
			return None


	def _allocate_resource_url(self, rsc_instance):
		self.__url_rsc_id_to_rsc_instance[rsc_instance.id] = rsc_instance

	def _deallocate_resource_url(self, rsc_instance):
		del self.__url_rsc_id_to_rsc_instance[rsc_instance.id]



	# Resource retrieval
	def get_url_resource_data(self, rsc_id):
		try:
			rsc = self.__url_rsc_id_to_rsc_instance[rsc_id]
		except KeyError:
			return None
		else:
			try:
				data = rsc.get_data()
				mime_type = rsc.get_mime_type()
			except Exception, e:
				fragment = rsc.pres_ctx.fragment_view
				msg = _rsc_retrieve_error_message(fragment.segment_id, type(fragment.model).__name__, e, sys.exc_info()[1], sys.exc_info()[2])
				self.__resource_error_messages.append(msg)
				data = ''
				mime_type = ''

			return data, mime_type




	#
	#
	# Segment acquisition
	#
	#


	@property
	def root_segment(self):
		"""The root segment
		Defaults to None. You must set this before using the page.
		"""
		return self.__root_segment

	@root_segment.setter
	def root_segment(self, seg):
		if isinstance(seg, SegmentRef):
			seg = seg.segment
		self.__root_segment = seg


	@property
	def focused_segment(self):
		"""
		Focused segment
		:return: The segment that has focus, or None
		"""
		return self.__focused_segment



	#
	#
	# Events, tasks and synchronization
	#
	#

	def synchronize(self):
		"""Synchronise

		Executes all queued tasks, that were queued using the queue_task method.
		The resulting list of client messages is returned. These normally consist of modifications to perform to the browser DOM.
		"""
		# Execute queued tasks
		self.__execute_queued_tasks()

		# Build message list
		msg_list = []

		# Dependencies
		deps_list = []

		if self.__queued_page_reload is not None:
			location, get_params = self.__queued_page_reload

			# Just add the page reload message; no need for anything else since this dynamic page will no longer be in use
			msg_list.append(messages.reload_page_message(location, get_params))
			# Close the page; it's dead
			self.__service._close_page(self)
		else:
			# Get new global dependencies
			if not global_dependencies.are_global_dependencies_up_to_date(self.__global_deps_version):
				# Get the global dependencies
				global_deps = set()
				global_deps.update(global_dependencies.get_global_dependencies())
				# Get the dependencies which have been added since last time
				deps_list.extend(global_deps.difference(self.__global_deps))
				# Update our view of the global dependencies
				self.__global_deps = global_deps
				self.__global_deps_version = global_dependencies.get_global_dependencies_version()

			# Add any local dependencies
			deps_list.extend(self.__dependencies)
			self.__dependencies = []

			# Page modifications message
			if self.__page_modifications_message is not None:
				msg_list.append(self.__page_modifications_message)
				self.__page_modifications_message = None

			# Execute JS message
			if self.__execute_js_message is not None:
				msg_list.append(self.__execute_js_message)
				self.__execute_js_message = None

			# Resource modification message
			rsc_mod_message = self.__resource_msgs_message()
			if rsc_mod_message is not None:
				msg_list.append(rsc_mod_message)

			# Resource disposal message
			rsc_disp_message = self.__resources_disposed_message()
			if rsc_disp_message is not None:
				msg_list.append(rsc_disp_message)


			# Structure validity message
			structure_validity_message = self.__structure_validity_message()
			if structure_validity_message is not None:
				msg_list.append(structure_validity_message)


			# Resource errors
			if len(self.__resource_error_messages) > 0:
				print 'Page.sync: Adding rsc error messages'
				msg_list.extend(self.__resource_error_messages)
				self.__resource_error_messages = []


		return msg_list, deps_list



	def queue_task(self, task, priority=0):
		"""
		Queue a task

		:param task: callable
		:param priority: [optional] task priority
		"""
		self.__queued_tasks.add(priority, task)
		for callback in self.__queue_synchronize_callbacks:
			callback(self)


	def register_queue_synchronize_callback(self, callback):
		self.__queue_synchronize_callbacks.append(callback)

	def unregister_queue_synchronize_callback(self, callback):
		self.__queue_synchronize_callbacks.remove(callback)



	# Event handling
	def handle_event(self, segment_id, event_name, ev_data):
		if segment_id is None:
			for handler_ev_name, handler_fn in self.__page_event_handlers:
				if handler_ev_name == event_name:
					try:
						event = Event(self, None, event_name, ev_data)
						if handler_fn(event):
							return True
					except Exception, e:
						return EventHandleError(event_name, None, None, None, None, e, sys.exc_info()[1], sys.exc_info()[2])
			return False
		else:
			try:
				event_segment = self._table[segment_id]
			except KeyError:
				return False

			segment = event_segment

			if event_name == 'gain_focus':
				self.__focused_segment = segment
			elif event_name == 'lose_focus'  and  segment is self.__focused_segment:
				self.__focused_segment = None

			while segment is not None:
				try:
					event = Event(self, event_segment, event_name, ev_data)
					if segment._handle_event(event):
						return True
				except Exception, e:
					return EventHandleError(event_name, segment_id, type(event_segment.fragment.model).__name__, segment.id, type(segment.fragment.model).__name__, e, sys.exc_info()[1], sys.exc_info()[2])
				segment = segment.parent
			return False


	def add_page_event_handler(self, event_name, event_response_function):
		self.__page_event_handlers.append((event_name, event_response_function))




	#
	#
	# Page reload
	#
	#

	def queue_page_reload(self, location=None, get_params=None):
		self.__queued_page_reload = location, get_params




	#
	#
	# Invalid content structure
	#
	#

	def _notify_segment_html_structure_validity_change(self, segment, valid):
		if not valid:
			self.__segments_with_invalid_html_structure.add(segment)
		else:
			self.__segments_with_invalid_html_structure.remove(segment)
			self._check_for_structurally_valid_page()



	def _check_for_structurally_valid_page(self):
		if len(self.__segments_with_invalid_html_structure) == 0:
			# Validity problems have been fixed: queue a reload
			get_params = {}
			get_params.update(self.__get_params)
			if self.__FIX_HTML_STRUCTURE_PARAM_NAME in get_params:
				del get_params[self.__FIX_HTML_STRUCTURE_PARAM_NAME]
			self.queue_page_reload(None, get_params)


	def _notify_segment_html_structure_fixes(self, segment, fixes):
		self.__segment_html_structure_fixes[segment] = fixes


	def __structure_validity_message(self):
		if len(self.__segment_html_structure_fixes) > 0:
			fixes_by_model_id = {}

			for seg, fixes in self.__segment_html_structure_fixes.items():
				model = seg.fragment.model
				fixes_for_model = fixes_by_model_id.setdefault(id(model), (model, []))
				fixes_for_model[1].extend(fixes)

			fixed_by_model_json = []
			for model, fixes in fixes_by_model_id.values():
				fixes_json = {
					'model_type_name': type(model).__name__,
					'fixes': [fix.to_json() for fix in fixes]
				}
				fixed_by_model_json.append(fixes_json)

			self.__segment_html_structure_fixes = {}
			return messages.html_structure_fixes_message(fixed_by_model_json)
		else:
			return None







	def __execute_queued_tasks(self):
		"""
		Execute the tasks in the task queue
		:return: None
		"""
		while len(self.__queued_tasks) > 0:
			f = self.__queued_tasks.pop()
			f()


	def queue_js_to_execute(self, js):
		self.__js_queue.append( js )


	def _notify_page_modified(self):
		# Segment changes notification. Called by _new_segment, _remove_segment and _segment_modified in _SegmentTable
		if not self.__page_modified:
			self.__page_modified = True
			self.queue_task(self.__refresh_page, self._REFRESH_PRIORITY)


	def __refresh_page(self):
		# Refresh the page

		segment_id_to_queued_scripts = self.__segment_id_to_queued_scripts
		self.__segment_id_to_queued_scripts = {}

		# Get the change set
		change_set = self._table._get_recent_changes(segment_id_to_queued_scripts)
		# Clear changes
		self._table._clear_changes()
		# Compose the modify page message
		self.__page_modifications_message = messages.modify_page_message(change_set.json())

		# Build the execute JS message
		if len(self.__js_queue) > 0:
			self.__execute_js_message = messages.execute_js_message('\n'.join(self.__js_queue))
			self.__js_queue = []

		self.__page_modified = False


	def initial_content(self):
		if self.__root_segment is None:
			raise RuntimeError, 'Root segment has not been set.'
		root_content = self.__root_segment.reference()._complete_html()


		self.__global_deps.update(global_dependencies.get_global_dependencies())
		deps_list = list(self.__global_deps)  +  self.__dependencies
		self.__global_deps_version = global_dependencies.get_global_dependencies_version()

		self.__dependencies = []

		initialisers = self._table._get_all_initialisers()

		self._table._clear_changes()


		return self._view_id, root_content, self.__js_queue, initialisers, deps_list






class _ChangeSet (object):
	"""A change set

	Represents a set of DOM changes that must be applied by the client.
	"""
	def __init__(self, added_segs, removed_segs, modified_segs, popup_segs_to_js_src, segment_id_to_queued_scripts):
		"""Constructor

		added_segs - the set of new segments added
		removed_segs - the set of segments that were removed
		modified_segs - the set of modified segments
		popup_segs - the set of popup segments

		Processes the changes, eliminating the added segments in the process; new segments should be children of modified segments, into which
		they are 'inlined'. By the time the inline process has finished, only removal and modification operations remain.
		"""
		self.__added_segs = added_segs

		self.__added_seg_to_html_bits = {}

		popup_segs = set(popup_segs_to_js_src.keys())

		self.removed = [seg.id   for seg in removed_segs]
		self.modified = []
		self.popups = [[seg.id, seg.reference()._complete_html()]   for seg in popup_segs]
		self.popup_scripts = [[seg.id, init_js_src]   for seg, init_js_src in popup_segs_to_js_src.items()]
		self.initialise_scripts = []
		self.shutdown_scripts = []

		# Schedule the execution of the shutdown scripts of the segments that are being removed.
		for seg in removed_segs:
			# If there are any scripts queued for this segment, execute them before the shutdown scripts
			queued_scripts = segment_id_to_queued_scripts.get(seg.id)
			if queued_scripts is not None:
				self.shutdown_scripts.append((seg.id, queued_scripts))
				del segment_id_to_queued_scripts[seg.id]
			shutdown_scripts = seg.get_shutdown_scripts()
			if shutdown_scripts is not None:
				self.shutdown_scripts.append((seg.id, shutdown_scripts))

		assert isinstance(self.__added_segs, set)
		while len(self.__added_segs) > 0:
			seg = added_segs.pop()
			initialise_scripts = seg.get_initialise_scripts()
			if initialise_scripts is not None:
				self.initialise_scripts.append((seg.id, initialise_scripts))
			items = []
			seg._build_inline_html(items, self.__resolve_reference)
			self.__added_seg_to_html_bits[seg] = items

		for seg in modified_segs:
			html = seg._inline_html(self.__resolve_reference)
			self.modified.append((seg.id, html))
			initialise_scripts = seg.get_initialise_scripts()
			if initialise_scripts is not None:
				self.initialise_scripts.append((seg.id, initialise_scripts))


		# Add any scripts that are queued to the list of initialisation scripts
		for seg_id, scripts in segment_id_to_queued_scripts.items():
			self.initialise_scripts.append((seg_id, scripts))


		if len(self.__added_segs) > 0:
			raise UnusedSegmentsError, set(self.__added_seg_to_html_bits.keys()).union(set(self.__added_segs))

		if set(self.__added_seg_to_html_bits.keys()) != popup_segs:
			raise UnusedSegmentsError, set(self.__added_seg_to_html_bits.keys()).difference(popup_segs)




	def print_contents(self):
		print 'CHANGES TO SEND: {0} removed, {1} modified, {2} popups, {3} popup scripts, {4} initialise scripts, {5} shutdown scripts'.format(len(self.removed), len(self.modified), len(self.popups),
																		       len(self.popup_scripts), len(self.initialise_scripts), len(self.shutdown_scripts))




	def json(self):
		"""Generates a JSON object describing the changes
		"""
		return {'removed': self.removed, 'modified': self.modified, 'popups': self.popups, 'popup_scripts': self.popup_scripts, 'initialise_scripts': self.initialise_scripts, 'shutdown_scripts': self.shutdown_scripts}


	def __resolve_reference(self, items, seg):
		if seg in self.__added_seg_to_html_bits:
			html_bits = self.__added_seg_to_html_bits[seg]
			del self.__added_seg_to_html_bits[seg]
			items.extend(html_bits)
		elif seg in self.__added_segs:
			self.__added_segs.remove(seg)
			initialisers = seg.get_initialise_scripts()
			if initialisers is not None:
				self.initialise_scripts.append((seg.id, initialisers))
			seg._build_inline_html(items, self.__resolve_reference)
		else:
			items.append(seg._place_holder())




class _SegmentTable (object):
	def __init__(self, page):
		self.__page = page

		self.__id_counter = 1
		self.__id_to_segment = {}

		self.__changes_added = set()
		self.__changes_removed = set()
		self.__changes_modified = set()
		self.__changes_popups = {}		# Dictionary used as a sort of set: maps popup segment to the initialisation JS source



	def __getitem__(self, segment_id):
		return self.__id_to_segment[segment_id]


	def __contains__(self, segment_id):
		return segment_id in self.__id_to_segment


	@property
	def all_segments(self):
		return self.__id_to_segment.values()



	def _clear_changes(self):
		self.__changes_added = set()
		self.__changes_removed = set()
		self.__changes_modified = set()
		self.__changes_popups = {}


	def _get_recent_changes(self, segment_id_to_queued_scripts):
		return _ChangeSet(copy(self.__changes_added), copy(self.__changes_removed), copy(self.__changes_modified), copy(self.__changes_popups), segment_id_to_queued_scripts)


	def _get_all_initialisers(self):
		initialisers = []
		for segment in self.__id_to_segment.values():
			init_scripts = segment.get_initialise_scripts()
			if init_scripts is not None:
				initialisers.append((segment.id, init_scripts))
		return initialisers



	def _new_segment(self, content=None, desc=None, fragment=None):
		desc_str = ('_' + desc)   if desc is not None   else ''
		seg_id = 'seg{0}{1}'.format(self.__id_counter, desc_str)
		self.__id_counter += 1
		seg = DynamicSegment(self.__page, seg_id, content, fragment)
		self.__id_to_segment[seg_id] = seg

		self.__changes_added.add(seg)

		self.__page._notify_page_modified()

		return seg


	def _remove_segment(self, segment):
		del self.__id_to_segment[segment.id]

		if segment in self.__changes_added:
			self.__changes_added.remove(segment)
		else:
			self.__changes_removed.add(segment)

		self.__page._notify_page_modified()


	def _segment_modified(self, segment, content):
		if segment not in self.__changes_added:
			self.__changes_modified.add(segment)

		self.__page._notify_page_modified()


	def _add_popup_segment(self, segment, initialisation_js_src):
		self.__changes_popups[segment] = initialisation_js_src





class DynamicPageResourceInstance (object):
	def __init__(self, page, rsc_id, resource):
		self.__page = page
		self.__rsc_id = rsc_id
		self.__resource = resource
		self.__pres_ctx = None
		self.__ref_count = 0


	def ref(self, pres_ctx):
		if self.__ref_count == 0:
			self.__pres_ctx = pres_ctx
			self.__resource.page_ref(pres_ctx, self)
			if self.__resource.requires_url:
				self.__page._allocate_resource_url(self)
		self.__ref_count += 1
		return self.__ref_count

	def unref(self):
		self.__ref_count -= 1
		if self.__ref_count == 0:
			self.__resource.page_unref(self.__pres_ctx, self)
			if self.__resource.requires_url:
				self.__page._deallocate_resource_url(self)
			self.__page._resource_disposed(self)
		return self.__ref_count



	def send_resource_message(self, message):
		self.__page._send_resource_message(self, message)

	def on_resource_message(self, message):
		self.__resource.on_resource_message(self, message)


	@property
	def page(self):
		return self.__page

	@property
	def pres_ctx(self):
		return self.__pres_ctx

	@property
	def id(self):
		return self.__rsc_id

	def get_data(self):
		return self.__resource.get_data()

	def get_mime_type(self):
		return self.__resource.get_mime_type()


	@property
	def resource_url(self):
		if not self.__resource.requires_url:
			raise RuntimeError, 'Attempting to acquire a URL for a resource that does not support URL based access'
		return '/rsc/{0}/{1}/{2}'.format(self.__page._doc_url, self.__page._view_id, self.__rsc_id)
