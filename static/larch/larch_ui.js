//-*************************
//-* This program is free software; you can use it, redistribute it and/or
//-* modify it under the terms of the GNU Affero General Public License
//-* version 3 as published by the Free Software Foundation. The full text of
//-* the GNU Affero General Public License version 3 can be found in the file
//-* named 'LICENSE.txt' that accompanies this program. This source code is
//-* (C)copyright Geoffrey French 2011-2014.
//-*************************

var LarchControls = function(larch) {
    var link = document.createElement("link");
    link.type = "text/css";
    link.rel = "stylesheet";
    link.href = "/files/static/larch/larch_ui.css";
    document.getElementsByTagName("head")[0].appendChild(link);

    larch.controls = {};

    // editor must have the following:
    //      ignoreChanges: boolean flag
    //      outer: outer DOM element
    //      getContent: function() that gets the content
    //      setContent: function(content) that sets the editor content
    larch.controls.__ckEditorSetupEditor = function(textArea, editor, ck, immediate_events) {
        if (immediate_events) {
            textArea.addEventListener('input', function () {
                if (!editor.ignoreChanges) {
                    larch.postEvent(editor.outer, "ckeditor_edit", editor.getContent());
                }
            }, false);
        }
        else {
            textArea.addEventListener('input', function () {
                if (!editor.ignoreChanges) {
                    var fac = function () {
                        return editor.getContent();
                    };
                    larch.queueEventFactory(editor.outer, "ckeditor_edit", fac);
                }
            }, false);
        }

        ck.on("focus", function () {
            larch.controls.grabFocus(editor.outer);
            larch.postEvent(editor.outer, "ckeditor_focus", null);
        });
    };



    // editor must have the following:
    //      ignoreChanges: boolean flag
    //      outer: outer DOM element
    //      getContent: function() that gets the content
    //      setContent: function(content) that sets the editor content
    larch.controls.__ckEditorListenToChannel = function(editor, channel) {
        if (channel !== undefined) {
            channel.addListener(function (message) {
                editor.ignoreChanges = true;
                editor.setContent(message);
                editor.ignoreChanges = false;
            });
        }
    };



    larch.controls.initCKEditor = function (textArea, config, immediate_events, channel) {
        var editor = {
            ignoreChanges: false,
            outer: textArea,
            getContent: function() {
                return editor.outer.innerHTML;
            }
        };
        var ck = CKEDITOR.inline(textArea, config);
        textArea.setAttribute('data-__larch.controls.ckeditor-name', ck.name);

        editor.setContent = function(content) {
            ck.setData(content);
        };

        larch.controls.__ckEditorSetupEditor(textArea, editor, ck, immediate_events);
        larch.controls.__ckEditorListenToChannel(editor, channel);

        ck.on("blur", function () {
            // The input event from the text area is ony emitted when the user types
            // Style changes trigger no such event
            // Just in case, emit an edit event on blur to make sure any changes get sent over.
            larch.postEvent(textArea, "ckeditor_edit", textArea.innerHTML);
            larch.postEvent(textArea, "ckeditor_blur", null);
        });

        CKEDITOR.disableAutoInline = true;
    };

    larch.controls.shutdownCKEditor = function(textArea) {
        var name = textArea.getAttribute('data-__larch.controls.ckeditor-name');
        CKEDITOR.instances[name].destroy();
    };


    larch.controls.initCKEditorWithEditButton = function(node, config, immediate_events, channel) {
        var outerQ = $(node);

        // Rich text editor object
        var editor = {
            outer: node,
            outerQ: outerQ,
            textContainer: outerQ.children().first(),
            editing: false,
            ck: null,
            ignoreChanges: false,
            eventSource: node,
            getContent: function() {
                return editor.textContainer[0].innerHTML;
            },
            setContent: function(content) {
                if (editor.editing) {
                    editor.ck.setData(content);
                }
                else {
                    editor.textContainer[0].innerHTML = content;
                }
            }
        };

        // The edit button pop over
        var editButton = $('<button>Edit</button>');
        editButton.button({icons: {primary: 'ui-icon-pencil'}});
        var editPopOver = $('<div class="__larch_ui_ckeditor_edit_popover_container"></div>');
        var editPopOverInner = $('<div class="__larch_ui_ckeditor_edit_popover"></div>');
        editPopOverInner.append(editButton);
        editPopOverInner.append(' (or Alt-click)');
        editPopOver.append(editPopOverInner);

        editButton.click(function (ui, event) {
            editor.startEditing();
        });



        // Start editing function
        editor.startEditing = function () {
            if (!editor.editing) {
                editor.editing = true;
                var textArea = editor.textContainer[0];
                textArea.setAttribute('contenteditable', true);
                editor.ck = CKEDITOR.inline(textArea);
                editor.ck.on('instanceReady', function () {
                    editor.ck.focus();
                });

                larch.controls.__ckEditorSetupEditor(textArea, editor, editor.ck, immediate_events);


                editor.ck.on('blur', function () {
                    // The input event from the text area is ony emitted when the user types
                    // Style changes trigger no such event
                    // Just in case, emit an edit event on blur to make sure any changes get sent over.
                    larch.postEvent(editor.outer, "ckeditor_edit", editor.getContent());
                    larch.postEvent(editor.outer, "ckeditor_blur", null);
                    editor.stopEditing();
                });
            }
        };

        // Stop editing function
        editor.stopEditing = function () {
            if (editor.editing) {
                editor.editing = false;
                editor.ck.destroy();
                editor.ck = null;

                var contents = editor.textContainer.children();
                contents.detach();
                editor.textContainer.remove();
                var newContainer = $('<div></div>');
                newContainer.append(contents);
                editor.textContainer = newContainer;
                editor.outerQ.append(newContainer);
            }
        };


        editor.outerQ.prepend(editPopOver);

        // Edit on alt-click
        editor.outerQ.click(function (event) {
            if (event.altKey) {
                editor.startEditing();
            }
        });

        larch.controls.__ckEditorListenToChannel(editor, channel);
    };


    larch.controls.initCodeMirror = function (textArea, config, immediate_events, channel) {
        var ignoreChanges = [false];

        var c = CodeMirror.fromTextArea(textArea, config);
        if (immediate_events) {
            c.on("change", function (editor, edit) {
                if (!ignoreChanges[0]) {
                    var elem = editor.getWrapperElement();
                    larch.postEvent(elem, "code_mirror_edit", editor.getValue());
                }
            });
        }
        else {
            c.on("change", function (editor, edit) {
                if (!ignoreChanges[0]) {
                    var elem = editor.getWrapperElement();
                    var fac = function () {
                        return editor.getValue();
                    };
                    larch.queueEventFactory(elem, "code_mirror_edit", fac);
                }
            });
        }
        c.on("focus", function (editor) {
            var elem = editor.getWrapperElement();
            larch.controls.grabFocus(elem);
            larch.postEvent(elem, "code_mirror_focus", null);
        });
        c.on("blur", function (editor) {
            var elem = editor.getWrapperElement();
            larch.postEvent(elem, "code_mirror_blur", null);
        });

        if (channel !== undefined) {
            channel.addListener(function (message) {
                ignoreChanges[0] = true;
                c.getDoc().setValue(message);
                ignoreChanges[0] = false;
            });
        }
    };


    //
    //
    // jQuery UI controls
    //
    //

    larch.controls.initButton = function (node, options) {
        $(node).button(options);
    };

    larch.controls.initSlider = function (node, respondToSlide, options, channel) {
        var ignoreChanges = [false];
        options.change = function (event, ui) {
            if (!ignoreChanges[0]) {
                larch.postEvent(node, "slider_change", ui.value)
            }
        };
        if (respondToSlide) {
            options.slide = function (event, ui) {
                if (!ignoreChanges[0]) {
                    larch.postEvent(node, "slider_slide", ui.value)
                }
            };
        }
        var control = $(node).slider(options);
        if (channel !== undefined) {
            channel.addListener(function (message) {
                ignoreChanges[0] = true;
                control.slider('value', message);
                ignoreChanges[0] = false;
            });
        }
    };

    larch.controls.initRangeSlider = function (node, respondToSlide, options, channel) {
        var ignoreChanges = [false];
        options.change = function (event, ui) {
            if (!ignoreChanges[0]) {
                larch.postEvent(node, "slider_change", ui.values)
            }
        };
        if (respondToSlide) {
            options.slide = function (event, ui) {
                if (!ignoreChanges[0]) {
                    larch.postEvent(node, "slider_slide", ui.values)
                }
            };
        }
        var control = $(node).slider(options);
        if (channel !== undefined) {
            channel.addListener(function (message) {
                ignoreChanges[0] = true;
                control.slider('values', message);
                ignoreChanges[0] = false;
            });
        }
    };

    larch.controls.initSpinner = function (node, channel) {
        var ignoreChanges = [false];
        var control = $(node).spinner({
            spin: function (event, ui) {
                if (!ignoreChanges[0]) {
                    larch.postEvent(control.get(0), "spinner_change", ui.value);
                }
            },
            change: function (event, ui) {
                if (!ignoreChanges[0]) {
                    larch.postEvent(control.get(0), "spinner_change", control.spinner("value"));
                }
            }
        });

        if (channel !== undefined) {
            channel.addListener(function (message) {
                ignoreChanges[0] = true;
                control.spinner('value', message);
                ignoreChanges[0] = false;
            });
        }
    };

    larch.controls.initTextEntry = function (node, immediateEvents, channel) {
        var ignoreChanges = [false];

        if (immediateEvents) {
            node.oninput = function () {
                if (!ignoreChanges[0]) {
                    larch.postEvent(node, "text_entry_edit", node.value);
                }
            };
        }
        else {
            node.oninput = function () {
                if (!ignoreChanges[0]) {
                    larch.queueEventFactory(node, "text_entry_edit", function () {
                        return node.value;
                    });
                }
            };
        }

        if (channel !== undefined) {
            channel.addListener(function (message) {
                ignoreChanges[0] = true;
                node.value = message;
                ignoreChanges[0] = false;
            });
        }
    };

    larch.controls.initSelect = function (node) {
        node.onchange = function () {
            larch.postEvent(node, "select_choose", node.value);
        };
    };


    larch.controls.initMenu = function (node, options) {
        options.select = function (event, ui) {
            var node = ui.item.get(0);
            larch.postEvent(node, "menu_select", null);
        };
        $(node).menu(options);
    };


    //
    // FOCUS
    //

    larch.controls.__focus = null;

    larch.controls.initFocusable = function (node) {
        var q = $(node);
        q.addClass("larch_ui_focusable");
        q.click(function (e) {
            // Use the property '__larch_focus_handled' on the original event structure to ensure that
            // the event does not cause the focus to shift to an outer element
            if (!e.originalEvent.hasOwnProperty('__larch_focus_handled')) {
                larch.controls.grabFocus(node);
                e.originalEvent.__larch_focus_handled = true;
            }
        });
    };

    larch.controls.shutdownFocusable = function (node) {
        var q = $(node);
        q.addClass("larch_ui_focusable");
        q.click(function () {
            larch.controls.ungrabFocus(node);
        });
    };

    larch.controls.grabFocus = function (node) {
        var focusable = $(node).closest(".larch_ui_focusable");

        if (focusable.length === 1) {
            if (larch.controls.__focus !== null) {
                $(larch.controls.__focus).removeClass("larch_ui_focused");
                larch.postEvent(larch.controls.__focus, "lose_focus", null);
            }

            larch.controls.__focus = focusable.get(0);
            focusable.addClass("larch_ui_focused");
            larch.postEvent(larch.controls.__focus, "gain_focus", null);
        }
    };

    larch.controls.ungrabFocus = function (node) {
        var focusable = $(node).closest(".larch_ui_focusable");

        if (focusable.length === 1) {
            if (focusable.hasClass("larch_ui_focused")) {
                focusable.removeClass("larch_ui_focused");
                larch.postEvent(focusable.get(0), "lose_focus", null);
            }
        }
    };


    larch.controls.initToggleCommandBarButton = function (node) {
        return $(node).click(function () {
            if (larch.__commandBar === null) {
                larch.__showCommandBar();
            }
            else {
                larch.__commandBar.close();
            }
        }).button({icons: {primary: 'ui-icon-bullet'}});
    };


    larch.controls.initForm = function (node) {
        var form = $(node);
        form.submit(function () {
            var segment_id = larch.__getSegmentIDForEvent(node);
            form.ajaxSubmit({
                data: {__larch_segment_id: segment_id},
                url: '/form/' + larch.__doc_url + '/' + larch.__view_id,
                dataType: 'json',
                type: 'POST',
                success: function (msg) {
                    larch.__handleMessagesFromServer(msg);
                }
            });
            return false;
        });
        form.ajaxForm();
    };


    larch.controls.createNotyPopup = function (popup_id, nodes, options) {
        options.text = $(nodes);
        options.callback = {};
        options.callback.afterClose = function () {
            larch.__notifyPopupClosed(popup_id);
        };
        noty(options);
    };


    larch.controls.createDialog = function (popup_id, nodes, options) {
        options.close = function (event, ui) {
            larch.__notifyPopupClosed(popup_id);
        };
        var contents = null;
        if (nodes.length != 1) {
            contents = $('<div></div>');
            contents.append(nodes);
        }
        else {
            contents = nodes[0];
        }
        $(contents).dialog(options);
    };

    larch.controls.closeContainingDialog = function(node) {
        $(node).closest('.ui-dialog-content').dialog('close');
    };




    larch.controls.initObjectInspector = function(node) {
        // Pick up the click event
        $(node).mousedown(function(event) {
            if (!event.isImmediatePropagationStopped()  &&  event.which == 3  &&  (event.altKey && event.shiftKey  ||  event.altKey && event.ctrlKey)) {
                // Alt-shift-right-click
                event.preventDefault();
                event.stopImmediatePropagation();

                console.log("sending inspector message");

                larch.postEvent(node, '__larch_invoke_inspector', null);
            }
        });

        // Prevent the context menu from appearing
        $(node).contextmenu(function(event) {
            if (event.altKey && event.shiftKey  ||  event.altKey && event.ctrlKey) {
                event.preventDefault();
            }
        });
    };

    larch.controls.initInspectorEntry = function(node, segment_id) {
        var anchor = $(node);

        anchor.hover(function (event) {
            larch.__highlightSegment(segment_id);
        },
        function (event) {
            larch.__unhighlightSegment(segment_id);
        });

        anchor.click(function(event) {
            larch.__unhighlightSegment(segment_id);
        });
    };

    return larch;
};