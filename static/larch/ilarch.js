require(["widgets/js/widget",
    "components/jquery-ui/ui/minified/jquery-ui.min"], function(WidgetManager){



    var ILarchView = IPython.DOMWidgetView.extend({
        initialize: function(parameters) {
            this.model.on('msg:custom', this.on_custom_msg, this);
        },

        render: function(){
            var self = this;


            this.$content = $('<div>Hello world</div>');
            this.$content.appendTo(this.$el);

            this.$content.on("click", function() {
                console.log("clicked");
                //self.on_content_click();
            });
        },

        on_custom_msg: function(msg) {
            if (msg.msg_type === "larch") {
                this.$content.text(msg.data);
            }
        },

        on_content_click: function() {
            this.send({event: 'click'});
        }
    });

    // Register the DatePickerView with the widget manager.
    WidgetManager.register_widget_view('ILarchView', ILarchView);
});
