##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
import sys
from collections import deque

from larch.util.simple_attribute_table import SimpleAttributeTable
from larch.pres.presctx import PresentationContext
from larch.pres.pres import Pres
from larch.pres.html import Html
from larch.incremental import IncrementalMonitor, IncrementalFunctionMonitor
from larch.inspector.present_exception import present_exception_with_traceback
from larch.core.dynamicpage.page import  DynamicPage
from larch.core.dynamicpage.segment import  HtmlContent




def _exception_during_presentation(exc_pres):
	return Html('<div class="exception_during_presentation"><span class="exception_during_pres_title">Exception during presentation</span>', exc_pres, '</div>')

def _exception_during_presentation_to_html(exc_pres):
	return Html('<div class="exception_during_presentation"><span class="exception_during_pres_title">Exception while converting presentation to HTML</span>', exc_pres, '</div>')



def _inspector_event_handler(event):
	if event.name == '__larch_invoke_inspector':
		fragment = event.fragment

		# Find the first fragment for which inspection is not disabled
		while fragment is not None  and  not fragment.is_inspector_enabled():
			fragment = fragment.parent

		fragment.view._inspect_fragment(event, fragment)

		return True
	else:
		return False






class _FragmentView (object):
	_FLAG_SUBTREE_REFRESH_REQUIRED = 0x1
	_FLAG_NODE_REFRESH_REQUIRED = 0x2
	_FLAG_NODE_REFRESH_IN_PROGRESS = 0x4
	_FLAG_DISABLE_INSPECTOR = 0x8

	_FLAG_REFSTATE_MULTIPLIER_ = 0x10
	_FLAG_REFSTATE_NONE = 0x0 * _FLAG_REFSTATE_MULTIPLIER_
	_FLAG_REFSTATE_REFED = 0x1 * _FLAG_REFSTATE_MULTIPLIER_
	_FLAG_REFSTATE_UNREFED = 0x2 * _FLAG_REFSTATE_MULTIPLIER_
	_FLAG_REFSTATEMASK_ = 0x3 * _FLAG_REFSTATE_MULTIPLIER_

	_FLAGS_FRAGMENTVIEW_END = 0x4 * _FLAG_REFSTATE_MULTIPLIER_


	def __init__(self, model, inc_view):
		self.__flags = 0

		self.__set_flag(self._FLAG_SUBTREE_REFRESH_REQUIRED)
		self.__set_flag(self._FLAG_NODE_REFRESH_REQUIRED)

		self.__inc_view = inc_view
		self.__model = model

		self.__parent = None
		self.__next_sibling = None
		self.__children_head = None
		self.__children_tail = None

		self.__fragment_factory = None
		self.__incr = IncrementalFunctionMonitor(self)
		self.__incr.add_listener(self.__on_incremental_monitor_changed)

		# Segments
		self.__segment = self.__inc_view.dynamic_page.new_segment(desc='{0}'.format(type(self.__model).__name__), fragment=self)
		self.__segment.add_event_handler(_inspector_event_handler)
		self.__segment.add_initialise_script('larch.controls.initObjectInspector(node);')
		self.__sub_segments = []

		# Resources
		self.__resource_instances = set()


	def _dispose(self):
		self.__incr.remove_listener(self.__on_incremental_monitor_changed)
		for rsc_instance in self.__resource_instances:
			self.__inc_view.dynamic_page.unref_resource_instance(rsc_instance)
		for sub_seg in self.__sub_segments:
			self.__inc_view.dynamic_page.remove_segment(sub_seg)
		self.__inc_view.dynamic_page.remove_segment(self.__segment)



	def queue_task(self, task, priority=0):
		"""
		Queue a task

		:param task: callable
		:param priority: [optional] task priority
		"""
		self.__inc_view.queue_task(task, priority)


	#
	#
	# Segment acquisition
	#
	#

	@property
	def __segment_reference(self):
		"""
		Get a reference to the segment that corresponds to this fragment

		Called from present_inner_fragment, which is called while conerting an InnerFragment Pres to HtmlContent
		"""
		return self.__segment.reference()

	@property
	def _refreshed_segment_reference(self):
		self.refresh()
		return self.__segment.reference()

	@property
	def segment_id(self):
		return self.__segment.id



	def disable_inspector(self):
		self.__set_flag(self._FLAG_DISABLE_INSPECTOR)

	def is_inspector_enabled(self):
		return not self.__test_flag(self._FLAG_DISABLE_INSPECTOR)



	@property
	def is_active(self):
		return self.__parent is not None



	#
	#
	# Structure / model
	#
	#

	@property
	def view(self):
		return self.__inc_view

	@property
	def page(self):
		return self.__inc_view.dynamic_page.public_api

	@property
	def parent(self):
		return self.__parent

	@property
	def children(self):
		c = self.__children_head
		while c is not None:
			yield c
			c = c.__next_sibling

	@property
	def model(self):
		return self.__model


	def compute_subtree_size(self):
		size = 1
		for c in self.children:
			size += c.compute_subtree_size()
		return size


	def find_enclosing_model(self, filter_fn_or_type):
		"""
		Walk the fragment tree through parents towards the root. Return the first model that matches the filter

		:param filter_fn_or_type: either a function of the form function(model) -> boolean   or   a type
		:return: the matching model or None
		"""
		if isinstance(filter_fn_or_type, type):
			filter_fn = lambda model: isinstance(model, filter_fn_or_type)
		else:
			filter_fn = filter_fn_or_type

		fragment = self
		while fragment is not None:
			m = fragment.model
			if filter_fn(m):
				return m
			fragment = fragment.parent

		return None




	#
	#
	# Context
	#
	#

	@property
	def dynamic_page(self):
		return self.__inc_view.dynamic_page

	@property
	def service(self):
		return self.__inc_view.service

	@property
	def subject(self):
		return self.__inc_view.subject

	@property
	def perspective(self):
		return self.fragment_factory._perspective

	def create_presentation_context(self):
		f = self.fragment_factory
		return PresentationContext(self, f._perspective, f._inherited_state)



	#
	#
	# Sub-segments
	#
	#

	def create_sub_segment(self, content):
		sub_seg = self.__inc_view.dynamic_page.new_segment(content, desc='subseg_{0}'.format(type(self.__model).__name__), fragment=self)
		self.__sub_segments.append(sub_seg)
		return sub_seg



	def get_resource_instance(self, resource, pres_ctx):
		rsc_instance = self.__inc_view.dynamic_page.get_resource_instance(resource, pres_ctx)
		self.__resource_instances.add(rsc_instance)
		return rsc_instance



	#
	#
	# Fragment factory
	#
	#

	@property
	def fragment_factory(self):
		return self.__fragment_factory


	@fragment_factory.setter
	def fragment_factory(self, f):
		if f is not self.__fragment_factory:
			self.__fragment_factory = f
			self.__incr.on_changed()




	#
	#
	# Refresh
	#
	#

	def refresh(self):
		if self.__test_flag(self._FLAG_SUBTREE_REFRESH_REQUIRED):
			self.__refresh_subtree()
			self.__clear_flag(self._FLAG_SUBTREE_REFRESH_REQUIRED)


	def queue_refresh(self):
		"""
		Manually queue a refresh. Use when automatic refresh is disabled.
		:return: None
		"""
		self.__incr.on_changed()


	def disable_auto_refresh(self):
		"""
		Disable automatic refresh

		This fragment will no longer refresh its presentation in response to changes detected by the incremental computation system;
		changes reported from data that this fragment depends on (IncrementValueMonitor, LiveValue, etc) will be ignored

		Queue a refresh with the queue_refresh method

		:return: None
		"""
		self.__incr.block_and_clear_incoming_dependencies()



	def __refresh_subtree(self):
		self.__set_flag(self._FLAG_NODE_REFRESH_IN_PROGRESS)

		content = self.__segment.content
		self.__inc_view.on_fragment_content_change_from(self, content)

		if self.__test_flag(self._FLAG_NODE_REFRESH_REQUIRED):
			# Compute result for this fragment, and refresh all children
			refresh_state = self.__incr.on_refresh_begin()
			if refresh_state is not None:
				content = self.__compute_fragment_content()
			self.__incr.on_refresh_end(refresh_state)

		# Refresh each child
		child = self.__children_head
		while child is not None:
			child.refresh()
			child = child.__next_sibling

		if self.__test_flag(self._FLAG_NODE_REFRESH_REQUIRED):
			self.__incr.on_access()
			# Set the content
			self.__segment.content = content

		self.__inc_view.on_fragment_content_change_to(self, content)
		self.__clear_flag(self._FLAG_NODE_REFRESH_REQUIRED)
		self.__clear_flag(self._FLAG_NODE_REFRESH_IN_PROGRESS)


	@staticmethod
	def _unref_subtree(inc_view, fragment):
		q = deque()

		q.append(fragment)

		while len(q) > 0:
			f = q.popleft()

			if f.__ref_state != _FragmentView._FLAG_REFSTATE_UNREFED:
				inc_view._node_table._unref_fragment_view(f)

				child = f.__children_head
				while child is not None:
					q.append(child)
					child = child.__next_sibling



	@staticmethod
	def _ref_subtree(inc_view, fragment):
		q = deque()

		q.append(fragment)

		while len(q) > 0:
			f = q.popleft()

			if f.__ref_state != _FragmentView._FLAG_REFSTATE_REFED:
				inc_view._node_table._ref_fragment_view(f)

				child = f.__children_head
				while child is not None:
					q.append(child)
					child = child.__next_sibling



	def __child_disconnected(self):
		# ONLY INVOKE AGAINST A FRAGMENT WHICH HAS BEEN UNREFED, AND DURING A REFRESH

		# Clear the links between fragments
		child = self.__children_head
		while child is not None:
			next = child.__next_sibling

			child.__parent = None
			child.__next_sibling = None

			child = next
		self.__children_head = self.__children_tail = None

		if not self.__test_flag(self._FLAG_NODE_REFRESH_REQUIRED):
			self.__set_flag(self._FLAG_NODE_REFRESH_REQUIRED)
			self.__request_subtree_refresh()



	def __compute_fragment_content(self):
		# Clear the existing content
		self._clear_existing_content()

		# Generate new content
		self.__on_compute_node_result_begin()
		self.__clear_flag(self._FLAG_DISABLE_INSPECTOR)

		content = None
		try:
			if self.__fragment_factory is not None:
				content = self.__fragment_factory.build_html_content_for_fragment(self.__inc_view, self, self.__model)   if self.__fragment_factory is not None   else None
		finally:
			self.__on_compute_node_result_end()
		return content


	def _clear_existing_content(self):
		# Unregister existing child relationships
		child = self.__children_head
		while child is not None:
			next = child.__next_sibling

			_FragmentView._unref_subtree(self.__inc_view, child)
			child.__parent = None
			child.__next_sibling = None

			child = next
		self.__children_head = self.__children_tail = None

		# Remove sub segments
		for sub_seg in self.__sub_segments:
			self.__inc_view.dynamic_page.remove_segment(sub_seg)
		del self.__sub_segments[:]



	#
	#
	# Child / parent relationship
	#
	#

	def __register_child(self, child):
		if child.__parent is not None  and  child.parent is not self:
			child.__parent.__child_disconnected()

		# Append child to the list of children
		if self.__children_tail is not None:
			self.__children_tail.__next_sibling = child

		if self.__children_head is None:
			self.__children_head = child

		self.__children_tail = child

		child.__parent = self

		# Ref the subtree, so that it is kept around
		_FragmentView._ref_subtree(self.__inc_view, child)



	#
	#
	# Child notifications
	#
	#

	def __request_subtree_refresh(self):
		if not self.__test_flag(self._FLAG_SUBTREE_REFRESH_REQUIRED):
			self.__set_flag(self._FLAG_SUBTREE_REFRESH_REQUIRED)
			if self.__parent is not None:
				self.__parent.__request_subtree_refresh()

			self.__inc_view._on_fragment_view_request_refresh(self)



	#
	#
	# Refresh methods
	#
	#

	def __on_compute_node_result_begin(self):
		pass

	def __on_compute_node_result_end(self):
		pass





	#
	#
	# Inner fragment presentation
	#
	#

	def present_inner_fragment(self, model, perspective, inherited_state, subject=None):
		if subject is None:
			subject = self.__fragment_factory._subject

		if inherited_state is None:
			raise ValueError, 'inherited_state is None'

		child_fragment_view = self.__inc_view._build_fragment_view(model, self.__inc_view._get_unique_fragment_factory(perspective, subject, inherited_state))

		# Register the parent <-> child relationship before refreshing the node, so that the relationship is 'available' during (re-computation)
		self.__register_child(child_fragment_view)

		# We don't need to refresh the child node - this is done by incremental view after the fragments contents have been computed

		# If a refresh is in progress, we do not need to refresh the child node, as all child nodes will be refreshed by FragmentView.refreshSubtree()
		# Otherwise, we are constructing a presentation of a child node, outside the normal process, in which case, a refresh is required.
		if not self.__test_flag(self._FLAG_NODE_REFRESH_IN_PROGRESS):
			# Block access tracking to prevent the contents of this node being dependent upon the child node being refreshed,
			# and refresh the view node
			# Refreshing the child node will ensure that when its contents are inserted into outer elements, its full element tree
			# is up to date and available.
			# Blocking the access tracking prevents an inner node from causing all parent/grandparent/etc nodes from requiring a
			# refresh.
			current = IncrementalMonitor.block_access_tracking()
			child_fragment_view.refresh()
			IncrementalMonitor.unblock_access_tracking(current)

		return HtmlContent([child_fragment_view.__segment_reference])





	#
	#
	# Incremental monitor notifications
	#
	#

	def __on_incremental_monitor_changed(self, incr):
		if not self.__test_flag(self._FLAG_NODE_REFRESH_REQUIRED):
			self.__set_flag(self._FLAG_NODE_REFRESH_REQUIRED)
			self.__request_subtree_refresh()






	#
	#
	# Flags
	#
	#

	def __clear_flag(self, flag):
		self.__flags &= ~flag


	def __set_flag(self, flag):
		self.__flags |= flag


	def __set_flag_value(self, flag, value):
		if value:
			self.__flags |= flag
		else:
			self.__flags &= ~flag


	def __test_flag(self, flag):
		return (self.__flags & flag) != 0


	@property
	def __ref_state(self):
		return self.__flags & self._FLAG_REFSTATEMASK_

	@__ref_state.setter
	def __ref_state(self, state):
		self.__flags = (self.__flags & ~self._FLAG_REFSTATEMASK_) | state

	def _set_ref_state_refed(self):
		self.__ref_state = self._FLAG_REFSTATE_REFED

	def _set_ref_state_unrefed(self):
		self.__ref_state = self._FLAG_REFSTATE_UNREFED



class FragmentFactory (object):
	def __init__(self, inc_view, perspective, subject, inherited_state):
		self._perspective = perspective
		self._subject = subject
		self._inherited_state = inherited_state
		self.__hash = hash((id(perspective), hash(inherited_state), hash(id(subject))))


	def __hash__(self):
		return self.__hash

	def __eq__(self, other):
		if isinstance(other, FragmentFactory):
			return other._perspective is self._perspective  and  other._subject is self._subject  and  other._inherited_state is self._inherited_state
		else:
			return NotImplemented

	def __ne__(self, other):
		if isinstance(other, FragmentFactory):
			return other._perspective is not self._perspective  or  other._subject is not self._subject  or  other._inherited_state is not self._inherited_state
		else:
			return NotImplemented


	def build_html_content_for_fragment(self, inc_view, fragment_view, model):
		# Create the view fragment
		try:
			fragment_pres = self._perspective.present_object(model, fragment_view)
		except Exception, e:
			fragment_pres = _exception_during_presentation(present_exception_with_traceback(e, sys.exc_info()[1], sys.exc_info()[2]))

		try:
			if not isinstance(fragment_pres, Pres):
				raise TypeError, 'Presentation functions must return an object of type Pres, an object of type {0} was received'.format(type(fragment_pres).__name__)
		except Exception, e:
			fragment_pres = _exception_during_presentation(present_exception_with_traceback(e, sys.exc_info()[1], sys.exc_info()[2]))

		try:
			html_content = self.__pres_to_html_content(fragment_pres, fragment_view)
		except Exception, e:
			# The HTML content may have been partially built before the exception was raised, in which case fragment view nodes - and
			# their respective segments - may have been created. They are now orphaned and need to be disposed of
			fragment_view._clear_existing_content()
			fragment_pres = _exception_during_presentation_to_html(present_exception_with_traceback(e, sys.exc_info()[1], sys.exc_info()[2]))
			html_content = self.__pres_to_html_content(fragment_pres, fragment_view)

		return html_content


	def __pres_to_html_content(self, fragment_pres, fragment_view):
		return fragment_pres.build(PresentationContext(fragment_view, self._perspective, self._inherited_state))



class _TableForModel (object):
	def __init__(self, table, model):
		self.__table = table
		self.__model = model

		self.__refed_fragment_views = set()
		self.__unrefed_fragment_views = None


	def __add_unrefed_fragment_view(self, v):
		if self.__unrefed_fragment_views is None:
			self.__unrefed_fragment_views = set()
		self.__unrefed_fragment_views.add(v)

	def __remove_unrefed_fragment_view(self, v):
		if self.__unrefed_fragment_views is not None:
			self.__unrefed_fragment_views.remove(v)
			if len(self.__unrefed_fragment_views) == 0:
				self.__unrefed_fragment_views = None


	def _get_unrefed_fragment_view_for(self, fragment_factory):
		if self.__unrefed_fragment_views is not None:
			for v in self.__unrefed_fragment_views:
				if v.fragment_factory == fragment_factory:
					return v
		return None


	@property
	def refed_fragment_views(self):
		return self.__refed_fragment_views

	def __len__(self):
		return len(self.__refed_fragment_views)

	@property
	def num_unrefed_fragment_views(self):
		return len(self.__unrefed_fragment_views)   if self.__unrefed_fragment_views is not None   else 0


	def ref_fragment_view(self, v):
		self.__remove_unrefed_fragment_view(v)
		self.__refed_fragment_views.add(v)

	def unref_fragment_view(self, v):
		self.__refed_fragment_views.remove(v)
		self.__add_unrefed_fragment_view(v)


	def _clean(self):
		self.__unrefed_fragment_views = None
		if len(self.__refed_fragment_views) == 0:
			self.__table._remove_view_table_for_model(self.__model)



class IncrementalViewTable (object):
	def __init__(self):
		self.__table = {}
		self.__unrefed_fragment_views = set()


	def get_unrefed_fragment_for_model(self, model, fragment_factory):
		try:
			sub_table = self.__table[id(model)]
		except KeyError:
			return None
		return sub_table._get_unrefed_fragment_view_for(fragment_factory)


	def get(self, model):
		try:
			sub_table = self.__table[id(model)]
		except KeyError:
			return []
		return sub_table.refed_fragment_views


	def __contains__(self, model):
		return self.get_num_fragments_for_model(model) > 0


	def __len__(self):
		size = 0
		for v in self.__table.values():
			size += len(v)
		return size


	@property
	def num_models(self):
		return len(self.__table)


	def get_num_fragments_for_model(self, model):
		try:
			sub_table = self.__table[id(model)]
		except KeyError:
			return None
		return len(sub_table)


	def get_num_unrefed_fragments_for_model(self, model):
		try:
			sub_table = self.__table[id(model)]
		except KeyError:
			return None
		return sub_table.num_unrefed_fragment_views


	def clean(self):
		# We need to remove all nodes within the sub-trees rooted at the unrefed nodes
		unrefed_stack = []
		unrefed_stack.extend(self.__unrefed_fragment_views)

		while len(unrefed_stack) > 0:
			fragment_view = unrefed_stack.pop()

			# Don't need to visit children; entire sub-trees are 'unrefed' all at once

			try:
				sub_table = self.__table[id(fragment_view.model)]
			except KeyError:
				pass
			else:
				sub_table._clean()

			fragment_view._dispose()

		self.__unrefed_fragment_views.clear()


	def _ref_fragment_view(self, fragment_view):
		fragment_view._set_ref_state_refed()
		model = fragment_view.model
		try:
			sub_table = self.__table[id(model)]
		except KeyError:
			sub_table = _TableForModel(self, model)
			self.__table[id(model)] = sub_table
		sub_table.ref_fragment_view(fragment_view)
		try:
			self.__unrefed_fragment_views.remove(fragment_view)
		except KeyError:
			pass


	def _unref_fragment_view(self, fragment_view):
		fragment_view._set_ref_state_unrefed()
		model = fragment_view.model
		try:
			sub_table = self.__table[id(model)]
		except KeyError:
			sub_table = _TableForModel(self, model)
			self.__table[id(model)] = sub_table
		sub_table.unref_fragment_view(fragment_view)
		self.__unrefed_fragment_views.add(fragment_view)


	def _remove_view_table_for_model(self, model):
		del self.__table[id(model)]





#
#
# IncrementalView
#
#

class IncrementalView (object):
	class Subtree (object):
		def __init__(self, inc_view, model, perspective):
			self.__inc_view = inc_view
			self.__refresh_required = False
			self.model = model
			self.perspective = perspective
			self.fragment_view = None
			self.fragment_factory = None



		def initialise(self):
			# Create and set the root fragment fragment factory
			fragment_factory = self.__inc_view._get_unique_fragment_factory(self.perspective, self.__inc_view._subject, SimpleAttributeTable.instance)
			self._set_fragment_factory(fragment_factory)

			# Refresh
			self._refresh()

			# Get the root fragment
			return self._get_fragment_view()


		def dispose(self):
			_FragmentView._unref_subtree(self.__inc_view, self.fragment_view)
			self.__inc_view._node_table.clean()


		def _get_fragment_view(self):
			if self.fragment_factory is None:
				raise ValueError, 'No root fragment factory set'

			if self.fragment_view is not None:
				self.__inc_view._node_table._unref_fragment_view(self.fragment_view)
			if self.fragment_view is None:
				self.fragment_view = self.__inc_view._build_fragment_view(self.model, self.fragment_factory)
			if self.fragment_view is not None:
				self.__inc_view._node_table._ref_fragment_view(self.fragment_view)
			return self.fragment_view


		def _set_fragment_factory(self, fragment_factory):
			if fragment_factory is not self.fragment_factory:
				self.fragment_factory = fragment_factory
				self._queue_refresh()



		#
		# Refreshing
		#

		def _queue_refresh(self):
			if not self.__refresh_required:
				self.__refresh_required = True
				self.__inc_view.dynamic_page.queue_task(self._refresh, DynamicPage._REFRESH_PRIORITY)

		def _refresh(self):
			if self.__refresh_required:
				self.__refresh_required = False
				self._perform_refresh()


		def _perform_refresh(self):
			self.__on_subtree_refresh_begin()
			root_frag = self._get_fragment_view()
			if root_frag is not None:
				root_frag.refresh()
			self.__inc_view._node_table.clean()
			self.__on_subtree_refresh_end()



		def __on_subtree_refresh_begin(self):
			pass

		def __on_subtree_refresh_end(self):
			pass







	def __init__(self, subject, dynamic_page):
		self._subject = subject


		self.__root_subtree = self.Subtree(self, subject.focus, subject.perspective)
		self.__popup_subtrees = []


		self._node_table = IncrementalViewTable()

		self.__unique_fragment_factories = {}

		self.__dynamic_page = dynamic_page

		self.__lock = None

		# Initialise the root subtree
		root_frag_view = self.__root_subtree.initialise()
		# Set the content of the dynamic page to the content of the root fragment
		self.__dynamic_page.root_segment = root_frag_view._refreshed_segment_reference

		self.__dynamic_page.inc_view = self




	#
	#
	# View, model, subject
	#
	#

	@property
	def root_model(self):
		return self.__root_subtree.model

	@property
	def root_fragment_view(self):
		return self.__root_subtree.fragment_view

	@property
	def subject(self):
		return self._subject

	@property
	def dynamic_page(self):
		return self.__dynamic_page

	@property
	def service(self):
		return self.__dynamic_page.service



	def queue_task(self, task, priority=0):
		"""
		Queue a task

		:param task: callable
		:param priority: [optional] task priority
		"""
		self.__dynamic_page.queue_task(task, priority)




	#
	#
	# Popups
	#
	#

	def create_popup_segment(self, model, perspective, initialise_js_expr):
		def on_close():
			subtree.dispose()

		subtree = self.Subtree(self, model, perspective)
		self.__popup_subtrees.append(subtree)

		# Initialise the subtree
		root_frag_view = subtree.initialise()
		pres_ctx = PresentationContext(root_frag_view, perspective, SimpleAttributeTable.instance)
		subtree_seg_ref = root_frag_view._refreshed_segment_reference
		content = HtmlContent([subtree_seg_ref])
		init_js = initialise_js_expr.build_js(pres_ctx)
		popup_segment = self.__dynamic_page.new_popup_segment(init_js, on_close, content, 'popup')
		return popup_segment


	#
	#
	# Refreshing
	#
	#

	def _on_fragment_view_request_refresh(self, fragment_view):
		if fragment_view is self.__root_subtree.fragment_view:
			self.__root_subtree._queue_refresh()
		else:
			for sub in self.__popup_subtrees:
				if fragment_view is sub.fragment_view:
					sub._queue_refresh()
					break



	#
	#
	# Fragment building and acquisition
	#
	#

	def _build_fragment_view(self, model, fragment_factory):
		# Try asking the table for an unused fragment view for the model
		fragment_view = self._node_table.get_unrefed_fragment_for_model(model, fragment_factory)

		if fragment_view is None:
			# No existing incremental tree node could be acquired.
			# Create a new one and add it to the table
			fragment_view = _FragmentView(model, self)

		fragment_view.fragment_factory = fragment_factory

		return fragment_view


	#
	#
	# Fragment factories
	#
	#

	def _get_unique_fragment_factory(self, perspective, subject, inherited_state):
		factory = FragmentFactory(self, perspective, subject, inherited_state)
		try:
			return self.__unique_fragment_factories[factory]
		except KeyError:
			self.__unique_fragment_factories[factory] = factory
			return factory



	def on_fragment_content_change_from(self, fragment_view, content):
		pass


	def on_fragment_content_change_to(self, fragment_view, content):
		pass




	#
	#
	# Fragment inspector
	#
	#

	def _inspect_fragment(self, event, fragment):
		invoke_inspector = self.subject.optional_attr('invoke_inspector')
		if invoke_inspector is not None:
			invoke_inspector(event, fragment)
