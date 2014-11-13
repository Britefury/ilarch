##-*************************
##-* This program is free software; you can use it, redistribute it and/or
##-* modify it under the terms of the GNU Affero General Public License
##-* version 3 as published by the Free Software Foundation. The full text of
##-* the GNU Affero General Public License version 3 can be found in the file
##-* named 'LICENSE.txt' that accompanies this program. This source code is
##-* (C)copyright Geoffrey French 2011-2014.
##-*************************
from larch.core.dynamicpage.service import DynamicPageService
from larch.core.incremental_view import IncrementalView
from larch.core.subject import Subject
from larch import command


class CouldNotResolveLocationError (Exception):
	pass



class ProjectionService (DynamicPageService):
	"""
	Projection service

	A dynamic page service that uses the core system to display objects and resolves locations to
	subjects.

	Commands:
	For each focus object on the subject path from the root to the final subject:
		each focus that defines a __command__ should have it return a list of commands.
		These lists are concatenated and are made available

	Augmenting the page
	It can be desirable to have a containing object be able to place a frame around pages of child objects.
	To do so, add an augment_page attribute to the subject with add_step. This function will be called,
	with the subject as a parameter. It should return a new object that will present as the augmented
	page. A new step will be added to the subject with the focus attribute set to the newly augmented page.

	The locations 'pages' and 'pages/' resolve to the front page
	"""


	def __init__(self, front_page_model):
		"""
		Constructor

		:param front_page_model - the front page
		:return: ProjectionService instance
		"""
		super(ProjectionService, self).__init__()
		self.__front_page_model = front_page_model


	def page(self, subject):
		"""
		Render a page

		:param subject: the subject identifying what to display
		"""
		view = self.new_view(subject)

		# Augment page
		self.__augment_page(subject)

		# Attach commands
		self.__attach_commands(view, subject)

		# Create the incremental view and attach as view data
		view.view_data = IncrementalView(subject, view.dynamic_page)

		return view.dynamic_page.page_html()



	def page_for_subject(self, subject):
		view = self.new_view(subject)

		# Augment page
		self.__augment_page(subject)

		# Attach commands
		self.__attach_commands(view, subject)

		# Create the incremental view and attach as view data
		view.view_data = IncrementalView(subject, view.dynamic_page)

		return view.dynamic_page.page_html()



	def kernel_message(self, message, *args, **kwargs):
		return self.__front_page_model.kernel_message(message, *args, **kwargs)






	def __augment_page(self, subject):
		# Augment page
		try:
			augment_page_fn = subject.augment_page
		except AttributeError:
			pass
		else:
			augmented_page = augment_page_fn(subject)
			subject.add_step(focus=augmented_page)


	def __attach_commands(self, view, subject):
		cmds = []
		for f in subject.focii:
			try:
				method = f.__commands__
			except AttributeError:
				pass
			else:
				cmds.extend(method(view.dynamic_page.public_api))

		command_set = command.CommandSet(cmds)
		command_set.attach_to_page(view.dynamic_page)
