require(["widgets/js/widget",
    //"/files/static/larch/larch.js",
    "components/jquery-ui/ui/minified/jquery-ui.min"], function(WidgetManager){


    var ILarchView = IPython.DOMWidgetView.extend({
        render: function(){
            var self = this;

            this.model.on('msg:custom', this._on_custom_msg, this);

            var view_id = self.model.get('view_id_');
            var max_inflight = self.model.get('max_inflight_messages_');

            var send = function(msg) {
                self._send_larch_msg(msg)
            };

            self.__larch_msg_handler = null;
            var register_recv_handler = function(handler) {
                self.__larch_msg_handler = handler;
            };

            self.__larch = Larch(view_id, send, register_recv_handler, max_inflight);

            this.$content = $('<div>Hello world</div>');
            this.$content.appendTo(this.$el);

            this.$content.on("click", function() {
                self._send_larch_msg('click_event');
            });
        },


        _send_larch_msg: function(data) {
            this.send({msg_type: 'larch', data: data});
        },

        _on_larch_msg: function(msg_data) {
            //this.$content.text(msg_data);
            if (this.__larch_msg_handler !== null) {
                this.__larch_msg_handler(msg_data);
            }
        },


        _on_custom_msg: function(msg) {
            if (msg.msg_type === "larch") {
                this._on_larch_msg(msg.data);
            }
        }
    });

    // Register the DatePickerView with the widget manager.
    WidgetManager.register_widget_view('ILarchView', ILarchView);
});
