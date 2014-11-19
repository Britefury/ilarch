from IPython.core.getipython import get_ipython
from IPython.html import widgets
from IPython.display import display, Javascript
from IPython.utils.traitlets import Unicode, Integer, List, Dict

import sys

from larch.core.dynamicpage.page import EventHandleError
from larch.core.dynamicpage import messages
from larch.inspector import present_exception



def install_ilarch():
	with open('static/larch/ilarch.js', 'r') as f:
		ilarch_js = f.read()
	display(Javascript(ilarch_js))


class ILarch(widgets.DOMWidget):
	_view_name = Unicode('ILarchView', sync=True)

	view_id_ = Unicode(sync=True)
	initial_content_ = Unicode(sync=True)
	doc_init_scripts_ = List(sync=True)
	initialisers_ = List(sync=True)

	max_inflight_messages_ = Integer(default_value=3)

	def __init__(self, page, **kwargs):
		self.__page = page
		page.register_queue_synchronize_callback(self.__on_queue_synchronize)
		view_id, initial_content, doc_init_scripts, initialisers, deps = page.initial_content()
		self.__synchronize_op_in_progress = False

		for dep in deps:
			dep.ipython_setup()

		print 'ILarch.__init__: view_id={0}, initial_content={1}, doc_init_scripts={2}, initialisers={3}'.format(view_id, initial_content, doc_init_scripts, initialisers)

		super(ILarch, self).__init__(view_id_=view_id, initial_content_=initial_content, doc_init_scripts_=doc_init_scripts, initialisers_=initialisers, **kwargs)

		self.on_msg(self._on_msg_revc)

		self._synchronize()



	def send_larch_msg_packet(self, messages):
		self.send({
            		'msg_type'   : 'larch_msg_packet',
			'messages': messages
		})



	def __on_queue_synchronize(self, page):
		if not self.__synchronize_op_in_progress:
			self.send({
				'msg_type'   : 'larch_sync_request'
			})

	def _synchronize(self):
		self.__synchronize_op_in_progress = True
		error_messages = []

		# Synchronise the view
		deps = []
		try:
			client_messages, deps = self.__page.synchronize()
		except Exception, e:
			# Catch internal server error
			err_html = present_exception.exception_to_html_src(e, sys.exc_info()[1], sys.exc_info()[2])
			msg = messages.error_during_update_message(err_html)
			error_messages.append(msg)
			client_messages = []

		self.__synchronize_op_in_progress = False

		for dep in deps:
			dep.ipython_setup()

		# Send messages to the client
		msgs_out = client_messages + error_messages
		if len(msgs_out) > 0:
			self.send_larch_msg_packet(msgs_out)


	def _on_events(self, block_id, ev_msgs):
		self.__synchronize_op_in_progress = True

		error_messages = []

		# Handle the events
		for ev_json in ev_msgs:
			event_handle_result = self.__page.handle_event(ev_json['segment_id'], ev_json['event_name'], ev_json['ev_data'])
			if isinstance(event_handle_result, EventHandleError):
				msg = event_handle_result.to_message()
				error_messages.append(msg)


		# Synchronise the view
		deps = []
		try:
			client_messages, deps = self.__page.synchronize()
		except Exception, e:
			# Catch internal server error
			err_html = present_exception.exception_to_html_src(e, sys.exc_info()[1], sys.exc_info()[2])
			msg = messages.error_during_update_message(err_html)
			error_messages.append(msg)
			client_messages = []

		for dep in deps:
			dep.ipython_setup()

		self.__synchronize_op_in_progress = False

		# Send messages to the client
		return client_messages + error_messages


	def _on_msg_revc(self, _, msg):
		msg_type = msg.get('msg_type', '')
		if msg_type == 'larch_events':
			message_block = msg['data']
			replies = self._on_events(message_block['id'], message_block['messages'])
			if len(replies) > 0  or  message_block['ack_immediately']:
				self.send_larch_msg_packet(replies)
		elif msg_type == 'larch_sync':
			self._synchronize()

