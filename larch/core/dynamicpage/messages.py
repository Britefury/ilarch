##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************

from larch.msg import message


def dependency_message(deps):
	return message('add_dependencies', deps=deps)


def modify_page_message(changes):
	return message('modify_page', changes=changes)


def execute_js_message(js_code):
	return message('execute_js', js_code=js_code)


def resource_messages_message(resource_id_and_message_pairs):
	return message('resource_messages', messages= [{'resource_id': rsc_id, 'message': msg}   for rsc_id, msg in resource_id_and_message_pairs])


def resources_disposed_message(resource_ids):
	return message('resources_disposed', resource_ids=list(resource_ids))


def invalid_page_message():
	return message('invalid_page')


def reload_page_message(location, get_params):
	return message('reload_page', location=location, get_params=get_params)



def error_handling_event_message(err_html, event_name, event_seg_id, event_model_type_name, handler_seg_id, handler_model_type_name):
	return message('error_handling_event', err_html=err_html, event_name=event_name, event_seg_id=event_seg_id, event_model_type_name=event_model_type_name,
		       handler_seg_id=handler_seg_id, handler_model_type_name=handler_model_type_name)


def error_retrieving_resource(err_html, rsc_seg_id, rsc_model_type_name):
	return message('error_retrieving_resource', err_html=err_html, rsc_seg_id=rsc_seg_id, rsc_model_type_name=rsc_model_type_name)


def error_during_update_message(err_html):
	return message('error_during_update', err_html=err_html)


def html_structure_fixes_message(fixes_by_model):
	return message('html_structure_fixes', fixes_by_model=fixes_by_model)
