require(["widgets/js/widget",
    "/files/static/larch/larch.js",
    "/files/static/larch/larch_ui.js",
    "/files/static/noty/jquery.noty.js",
    "/files/static/noty/layouts/bottom.js",
    "/files/static/noty/layouts/bottomLeft.js",
    "/files/static/noty/layouts/bottomCenter.js",
    "/files/static/noty/layouts/bottomRight.js",
    "/files/static/noty/layouts/center.js",
    "/files/static/noty/layouts/centerLeft.js",
    "/files/static/noty/layouts/centerRight.js",
    "/files/static/noty/layouts/inline.js",
    "/files/static/noty/layouts/top.js",
    "/files/static/noty/layouts/topLeft.js",
    "/files/static/noty/layouts/topCenter.js",
    "/files/static/noty/layouts/topRight.js",
    "/files/static/noty/themes/default.js",
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

            self.__larch = Larch(this.$el, initial_content, view_id, send_events, max_inflight);
            self.__larch = LarchControls(self.__larch);

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
