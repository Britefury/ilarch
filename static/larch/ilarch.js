require(["widgets/js/widget",
    "/files/static/larch/larch.js",
    "components/jquery-ui/ui/minified/jquery-ui.min"], function(WidgetManager){


    var ILarchView = IPython.DOMWidgetView.extend({
        render: function(){
            var self = this;

            this.model.on('msg:custom', this._on_custom_msg, this);

            var view_id = self.model.get('view_id_');
            var initial_content = self.model.get('initial_content_');
            var doc_init_js = self.model.get('doc_init_scripts_');
            var initialisers = self.model.get('initialisers_');
            var max_inflight = self.model.get('max_inflight_messages_');

            var send_events = function(msg) {
                self._send_larch_events(msg)
            };

            self.__larch = Larch(view_id, send_events, max_inflight);

            this.$content = $(initial_content);
            this.$content.appendTo(this.$el);

             setTimeout(function() {
                    self.__larch.initialise(initialisers, doc_init_js);
                }, 0);
        },


        _send_larch_events: function(data) {
            this.send({msg_type: 'larch_events', data: data});
        },

        _send_larch_sync: function() {
            this.send({msg_type: 'larch_sync'});
        },

        _on_larch_msg: function(msg_data) {
            //this.$content.text(msg_data);
            this.__larch.receiveMessagesFromServer(msg_data);
        },


        _on_custom_msg: function(msg) {
            if (msg.msg_type === "larch_msg_packet") {
                this._on_larch_msg(msg.messages);
            }
            else if (msg.msg_type === "larch_sync_request") {
                this._send_larch_sync();
            }
        }
    });

    // Register the DatePickerView with the widget manager.
    WidgetManager.register_widget_view('ILarchView', ILarchView);
});
