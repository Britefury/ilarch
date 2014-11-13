from IPython.core.getipython import get_ipython
from IPython.html import widgets
from IPython.display import display, Javascript
from IPython.utils.traitlets import Unicode, Integer, List, Dict


def install_ilarch():
	with open('static/larch/ilarch.js', 'r') as f:
		ilarch_js = f.read()
	display(Javascript(ilarch_js))


class ILarch(widgets.DOMWidget):
	_view_name = Unicode('ILarchView', sync=True)

	def __init__(self, **kwargs):
		super(ILarch, self).__init__(**kwargs)
		self.on_msg(self._on_msg_revc)
		self.on_larch_msg = None
		self.count = 0

	def send_larch_msg(self, msg):
		self.send({
            		'msg_type'   : 'larch',
			'data': msg
		})


	def _on_msg_revc(self, _, msg):
		self.count += 1
		if self.on_larch_msg is not None:
			self.on_larch_msg(msg)

