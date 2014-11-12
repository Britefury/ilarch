//-*************************
//-* This program is free software; you can use it, redistribute it and/or
//-* modify it under the terms of the GNU Affero General Public License
//-* version 3 as published by the Free Software Foundation. The full text of
//-* the GNU Affero General Public License version 3 can be found in the file
//-* named 'LICENSE.txt' that accompanies this program. This source code is
//-* (C)copyright Geoffrey French 2011-2014.
//-*************************

larch = {
    __view_id: undefined,
    __segment_table: {}
};


larch.__getElementsOfClass = function(className, tagName) {
    // Utility function to get elements of a named class
    // if running on IE, a slower method is used that first involves finding elements by tagName then filtering by class
    if (document.getElementsByClassName) {
        return document.getElementsByClassName(className);
    }
    else {
        // IE does not support getElementsByClassName
        var els = document.getElementsByTagName(tagName);
        var i = 0;
        var elem;
        var placeHolders = [];
        while (elem = els[i++]) {
            if (elem.className === className) {
                placeHolders.push(elem);
            }
        }
        return placeHolders;
    }
};



larch.__addDependency = function(dep) {
    // Adds a dependency to the <head> element
    // A dependency is an element reference some CSS or a JS script
    $(dep).appendTo("head");
};



//
//
// SEGMENT MANAGEMENT
//
//

larch.__getSegmentIDForEvent = function(src_element) {
    // Get the segment ID that should be used to identify the source of an event to
    // the backend.
    // `src_element` is a DOM element. Searches the ancestors of src_element until one with
    // a segment ID is found.
    var n = src_element;
    var segment_id = null;
    while (n !== null) {
        if ("__lch_seg_id" in n) {
            // We have a segment ID
            segment_id = n.__lch_seg_id;
            break;
        }
        n = n.parentNode;
    }

    return segment_id;
};

larch.__buildConnectivity = function(segment) {
    // `segment` consists of the start and end nodes of a segment.
    // We often remove elements from the DOM in order to alter its contents.
    // Sometimes we put these nodes back in again. In such cases, the nextSibling attribute will be null,
    // preventing us from using it for iterating across the sequence of nodes.
    // So, we create a __lch_next attribute that points to the next sibling, so we can iterate using this instead.

    var prev = null;        // Maintain previous node, so that we can link to the current node
    for (var node = segment.start; node !== segment.end; node = node.nextSibling) {
        if (prev !== null) {
            prev.__lch_next = node;
        }
        prev = node;
    }
    prev.__lch_next = segment.end;
};

larch.__clearConnectivity = function(nodes) {
    // Clear connectivity built with __buildConnectivity

    var prev = null;        // Maintain previous node, so we can clear its connectivity after we have moved on to the next
    for (var i = 0; i < nodes.length; i++)
    {
        var n = nodes[i];
        if (prev !== null) {
            prev.__lch_next = null;
        }
        prev = n;
    }
};


larch.__newSegmentState = function(start, end) {
    // This creates a new 'segment state' to go into the segment table.
    // Larch defines a segment as a set of nodes that reside between
    // a start and end node
    return {'start': start, 'end': end}
};

larch.__getNodesInActiveSegment = function(segment) {
    // Get the list of nodes in a segment
    // Does not traverse into children
    // It builds a list of siblings between - and including - the start that
    // mark the start and end of the segment
    var nodeList = [];
    for (var n = segment.start; n !== segment.end; n = n.nextSibling) {
        nodeList.push(n);
    }
    nodeList.push(segment.end);
    return nodeList;
};

larch.__getNodesInActiveSegmentById = function(segment_id) {
    // Get the nodes in an active segment identified by segment ID
    // The segment must be active in order for it to be found in the
    // segment table.
    var segment_table = larch.__segment_table;
    var state = segment_table[segment_id];
    if (state === undefined) {
        console.log("larch.__getNodesInActiveSegmentById: Cannot get segment " + segment_id);
        return;
    }
    return larch.__getNodesInActiveSegment(state);
}

larch.__getNodesInInactiveSegment = function(segment) {
    // Get the nodes in an *inactive* segment

    // Iterate using __lch_next attribute; see __newSegmentState function for explanation
    var nodeList = [];
    var start = segment.start;
    var n;
    if (start.hasOwnProperty('__lch_next')  &&  start.__lch_next !== null) {
        // This inactive segment was directly removed in a previous replacement operation.
        // We must use the __lch_next property to iterate.
        for (n = segment.start; n !== segment.end; n = n.__lch_next) {
            nodeList.push(n);
        }
    }
    else {
        // This segment was removed as a result of a parent being removed, hence __lch_next has
        // not been initialised. Iterate using nextSibling.
        for (n = segment.start; n !== segment.end; n = n.nextSibling) {
            nodeList.push(n);
        }
    }
    nodeList.push(segment.end);
    return nodeList;
};



larch.__replaceSegment = function(oldSegmentState, newSegmentState) {
    // Replace the nodes within `oldSegmentState` within those in `newSegmentState`.
    // The is the main DOM manipulation operation used by Larch to update the DOM.

    var first = oldSegmentState.start;
    var parent = first.parentNode;

    // The nodes that we are about to remove from the DOM may be reused later.
    // Build out own connectivity structure so that we can iterate through them
    larch.__buildConnectivity(oldSegmentState);

    var oldNodes = larch.__getNodesInActiveSegment(oldSegmentState);
    var newNodes = larch.__getNodesInActiveSegment(newSegmentState);

    newNodes.forEach(function(n) {parent.insertBefore(n, first);});
    oldNodes.forEach(function(n) {parent.removeChild(n);});
};


larch.__replacePlaceholder = function(placeHolder, existingInactiveSegmentState) {
    // This replaces a placeholder element with the nodes in an inactive segment.
    // This DOM manipulation operation allows existing parts of the DOM tree to be retained;
    // they are un-parented and re-parented to new nodes.
    var parent = placeHolder.parentNode;

    var newNodes = larch.__getNodesInInactiveSegment(existingInactiveSegmentState);

    newNodes.forEach(function(n) {parent.insertBefore(n, placeHolder);});

    // These nodes are active: clear connectivity
    larch.__clearConnectivity(newNodes);

    parent.removeChild(placeHolder);
};





larch.__createSegmentContentNodesFromSource = function(content) {
    // Create nodes to form the contents of a segment from HTML source
    // Creates a temporary <div> element containing the content and extracts its child nodes.
    var elem = document.createElement("div");
    elem.innerHTML = content;
    return larch.__newSegmentState(elem.firstChild, elem.lastChild);
};



larch.__getPlaceHolderNodes = function() {
    // Find the placeholder nodes within the document
    return larch.__getElementsOfClass("__lch_seg_placeholder", "span");
};

larch.__getSegmentBeginNodes = function(q) {
    // Find the segment start nodes within the document
    if (q === undefined) {
        return larch.__getElementsOfClass("__lch_seg_begin", "span");
    }
    else {
        // Return the elements referenced by q and their descendants, filtered for spans with the '__lch_seg_begin' class
        return q.find('span.__lch_seg_begin').andSelf().filter('span.__lch_seg_begin');
    }
};





// A list of segments that are broken due to bad HTML structure.
larch.__brokenSegmentIDs = null;

larch.__register_segments = function(q) {
    // Iterate over all the segment begin nodes within the jQuery q
    // For any node that has not yet been initialised - this will be the case
    // with nodes just introduced to the DOM via a DOM manipulation -
    // register and initialise it
    var segment_table = larch.__segment_table;

    var inlines = larch.__getSegmentBeginNodes(q);

    for (var i = 0; i < inlines.length; i++) {
        // Get the start node and extract the segment ID
        var start = inlines[i];

        // Check if it is uninitialised
        if (!start.hasOwnProperty('__lch_initialised')) {
            start.__lch_initialised = true;

            // Extract the segment ID
            var segment_id = start.getAttribute("data-larchsegid");
            //console.log("Initialised " + segment_id);

            // Iterate forwards until we find the matching end node.
            var n = start;
            var segmentIsValid = true;      // false if the structure is broken
            while (true) {
                // Set the node's segment ID
                n.__lch_seg_id = segment_id;

                if (n.getAttribute  &&  n.getAttribute("class") === '__lch_seg_end'  && n.getAttribute("data-larchsegid") === segment_id) {
                    break;
                }

                // Next
                var nextNode = n.nextSibling;
                if (nextNode === null) {
                    segmentIsValid = false;
                    if (larch.__brokenSegmentIDs === null) {
                        larch.__brokenSegmentIDs = [];
                    }
                    larch.__brokenSegmentIDs.push(segment_id);
                    break;
                }
                n = nextNode;
            }

            if (segmentIsValid) {
                // This segment is valid e.g. not broken

                // @n is now the end node
                var end = n;

                // Put an entry in our segment table
                segment_table[segment_id] = larch.__newSegmentState(start, end);
            }
            else {
                continue;
            }
        }
    }
};






//
//
// SCRIPT EXECUTION
//
//

larch.__executeJS = function(js_code, context) {
    // Execute some Javascript code supplied in `js_code`.
    // `context` provides contextual information for tracking errors.
    try {
        eval(js_code);
    }
    catch (e) {
        console.log("Caught during " + context + ":");
        console.log(e);
        if (e.stack) {
            console.log(e.stack);
        }
    }
};


larch.__executeNodeScripts = function(node_scripts) {
    // Execute scripts that are used to initialise DOM nodes that are being
    // inserted into the DOM or shutdown nodes that are being removed
    // Node scripts are passed as an array of pairs, each one of the form [segment_id, script_js]
    // where segment_id identifies the segment to which the script is to be applied
    // and script_js is the Javascript source to executed.
    // The script will be evaluated in an environment in which `node` is the element/node
    // that it is to initialise
    var segment_table = larch.__segment_table;
    for (var i = 0; i < node_scripts.length; i++) {
        var node_script = node_scripts[i];
        var segment_id = node_script[0];
        var script = node_script[1];
        //console.log("Executing initialisers for " + segment_id);
        var state = segment_table[segment_id];
        if (state === undefined) {
            console.log("larch.__executeNodeScripts: Cannot get segment " + segment_id);
            return;
        }
        var nodes = larch.__getNodesInActiveSegment(state);
        for (var j = 1; j < nodes.length - 1; j++) {
            // The 'unused' variable node is referenced by the source code contained in the initialiser; it is needed by eval()
            var node = nodes[j];        // <<-- DO NOT DELETE; needed by code executed by eval
            for (var k = 0; k < script.length; k++) {
                try {
                    eval(script[k]);
                }
                catch (e) {
                    console.log("Caught during execution of node script:");
                    console.log(e);
                    if (e.stack) {
                        console.log(e.stack);
                    }
                }
            }
        }
    }
};



larch.__executePopupScripts = function(popup_scripts) {
    // Execute scripts that are used to initialise DOM nodes that are being
    // displayed within a popup
    // Node scripts are passed as an array of [segment_id, script_js] pairs,
    // where segment_id identifies the segment to which the script is to be applied
    // and script_js is the Javascript source to executed.
    // The script will be evaluated in an environment in which `popup_id` is the identity
    // of the popup and `nodes` is a reference to the elements at the root of the popup content.
    var segment_table = larch.__segment_table;
    for (var i = 0; i < popup_scripts.length; i++) {
        var popup_script = popup_scripts[i];
        var segment_id = popup_script[0];
        var script = popup_script[1];
        //console.log("Executing initialisers for " + segment_id);
        var state = segment_table[segment_id];
        if (state === undefined) {
            console.log("larch.__executePopupScripts: Cannot get segment " + segment_id);
            return;
        }
        // The 'unused' variables popup_id nad nodes are referenced by the source code contained in the initialiser; it is needed by eval()
        var popup_id = segment_id;        // <<-- DO NOT DELETE; needed by code executed by eval
        var nodes = larch.__getNodesInActiveSegment(state);        // <<-- DO NOT DELETE; needed by code executed by eval
        try {
            eval(script);
        }
        catch (e) {
            console.log("Caught during execution of popup script:");
            console.log(e);
            if (e.stack) {
                console.log(e.stack);
            }
        }
    }
};



//
//
// PAGE UPDATES
//
//


larch.__applyChanges = function(changes) {
    // Apply changes
    // This takes a change set sent by the backend that describes
    // the updates that must be made to the DOM.
    // It takes the form of an object with the following properties:
    // - shutdown_scripts: an array of [segment_id, script_js] pairs that identify segments that need to have shutdown scripts
    // executed before they are removed from the DOM (see remove attribute below)
    // - removed: an array of segment IDs that are being removed from the DOM
    // - modified: an array of [segment_id, new_content] pairs that identify segments that are to be replaced
    // along with the replacement HTML content
    // - popups: an array of [segment_id, popup_content] pairs that provide content that is to be loaded into popups.
    // Since they are within popups, they are not parented to another node within the document, so they have to be
    // maintained separately.
    // - popup_scripts: an array of [segment_id, script_js] pairs that are used to initialise the contents of popups
    // - initialise_scripts :  an array of [segment_id, script_js] pairs that are used to initialise DOM nodes that were
    // just inserted into the DOM. Nodes are inserted when processing the contents of the modified attribute, above.
    //
    // The changes are performed in the order of the attributes above.
    //

    //console.log("STARTING UPDATE");
    var removed = changes.removed;
    var modified = changes.modified;
    var popups = changes.popups;
    var popup_scripts = changes.popup_scripts;
    var initialise_scripts = changes.initialise_scripts;
    var shutdown_scripts = changes.shutdown_scripts;

    var segment_table = larch.__segment_table;

    // Execute shutdown scripts
    try {
        larch.__executeNodeScripts(shutdown_scripts);
    }
    finally {
        // Handle removals
        for (var i = 0; i < removed.length; i++) {
            // Just remove them from the table
            // The DOM modifications will remove the nodes
            //console.log("Removed " + removed[i]);
            delete segment_table[removed[i]];
        }

        // Handle modifications
        for (var i = 0; i < modified.length; i++) {
            // Get the segment ID and content
            var segment_id = modified[i][0];
            var content = modified[i][1];

            if (segment_id in segment_table) {
                var state = segment_table[segment_id];

                //console.log("Replaced " + segment_id);

                var newState = larch.__createSegmentContentNodesFromSource(content);
                newState.start.__lch_initialised = true;

                // Unregister segment IDs
                var oldNodes = larch.__getNodesInActiveSegment(state);
                oldNodes.forEach(function(n) {n.__lch_seg_id = null;});

                larch.__replaceSegment(state, newState);

                // Register segment IDs
                var newNodes = larch.__getNodesInActiveSegment(newState);
                newNodes.forEach(function(n) {n.__lch_seg_id = segment_id;});

                // Put in segment table
                segment_table[segment_id] = newState;
            }
        }

        // Handle popups
        var popupNodes = [];
        for (var i = 0; i < popups.length; i++) {
            // Get the segment ID and content
            var segment_id = popups[i][0];
            var content = popups[i][1];


            var newState = larch.__createSegmentContentNodesFromSource(content);
            newState.start.__lch_initialised = true;

            // Register segment IDs
            var newNodes = larch.__getNodesInActiveSegment(newState);
            newNodes.forEach(function(n) {n.__lch_seg_id = segment_id;});
            popupNodes = popupNodes.concat(newNodes);

            // Put in segment table
            segment_table[segment_id] = newState;
        }

        // Replace the placeholders with the segments that they reference
        var placeHolders = larch.__getPlaceHolderNodes();
        // Replacing a placeholder may introduce content that contains yet more placeholders....
        while (placeHolders.length > 0) {
            for (var i = 0; i < placeHolders.length; i++) {
                // Get the placeholder node
                var p = placeHolders[i];
                // Extract the segment ID that if references
                var segment_id = p.getAttribute("data-larchsegid");

                // Get the segment that is to take its place
                var segment = segment_table[segment_id];

                // Replace it
                larch.__replacePlaceholder(p, segment);
            }

            placeHolders = larch.__getPlaceHolderNodes();
        }

        // Register any unregistered segments that have been introduced by modifications
        larch.__register_segments();
        if (popupNodes.length > 0) {
            larch.__register_segments($(popupNodes));
        }


        // Execute popup scripts
        try {
            larch.__executePopupScripts(popup_scripts);
        }
        finally {
            //console.log("FINISHED UPDATE");
        }


        // Execute initialise scripts
        try {
            larch.__executeNodeScripts(initialise_scripts);
        }
        finally {
            //console.log("FINISHED UPDATE");
        }
    }
};





//
//
// HIGHLIGHT SEGMENTS
//
//


larch.__highlightSegment = function(segment_id) {
    var segment_table = larch.__segment_table;
    var state = segment_table[segment_id];
    if (state === undefined) {
        console.log("larch.__highlightSegment: Cannot get segment " + segment_id);
        return;
    }
    var nodes = larch.__getNodesInActiveSegment(state);
    for (var j = 1; j < nodes.length - 1; j++) {
        $(nodes[j]).addClass("segment_highlight");
    }
};

larch.__unhighlightSegment = function(segment_id) {
    var segment_table = larch.__segment_table;
    var state = segment_table[segment_id];
    if (state === undefined) {
        console.log("larch.__unhighlightSegment: Cannot get segment " + segment_id);
        return;
    }
    var nodes = larch.__getNodesInActiveSegment(state);
    for (var j = 1; j < nodes.length - 1; j++) {
        $(nodes[j]).removeClass("segment_highlight");
    }
};


larch.__highlightElement = function(element) {
    $(element).addClass("segment_highlight");
};

larch.__unhighlightElement = function(element) {
    $(element).removeClass("segment_highlight");
};





//
//
// KEY EVENT PROCESSING
//
//


larch.__createKey = function(keyCode, altKey, ctrlKey, shiftKey, metaKey) {
    return {
        keyCode: keyCode,
        altKey: altKey,
        ctrlKey: ctrlKey,
        shiftKey: shiftKey,
        metaKey: metaKey
    };
};

larch.__matchKeyEvent = function(event, key) {
    if (key.keyCode === undefined  ||  event.keyCode == key.keyCode) {
        if (key.altKey !== undefined  &&  event.altKey != key.altKey) {
            return false;
        }
        if (key.ctrlKey !== undefined  &&  event.ctrlKey != key.ctrlKey) {
            return false;
        }
        if (key.shiftKey !== undefined  &&  event.shiftKey != key.shiftKey) {
            return false;
        }
        if (key.metaKey !== undefined  &&  event.metaKey != key.metaKey) {
            return false;
        }
        return true;
    }
    return false;
};

larch.__eventToKey = function(event) {
    return {
        keyCode: event.keyCode,
        altKey: event.altKey,
        ctrlKey: event.ctrlKey,
        shiftKey: event.shiftKey,
        metaKey: event.metaKey
    };
};

larch.__handleKeyEvent = function(event, keys) {
    for (var i = 0; i < keys.length; i++) {
        var key = keys[i];
        if (larch.__matchKeyEvent(event, key)) {
            // We have a match
            var k = larch.__eventToKey(event);
            return [k, key.preventDefault];
        }
    }
    return undefined;
};

larch.__onkeydown = function(event, keys) {
    var k = larch.__handleKeyEvent(event, keys);
    if (k !== undefined) {
        larch.postEvent(event.target, 'keydown', k[0]);
        if (k[1] === 1) {
            event.preventDefault();
            return false;
        }
    }
    return true;
};

larch.__onkeyup = function(event, keys) {
    var k = larch.__handleKeyEvent(event, keys);
    if (k !== undefined) {
        larch.postEvent(event.target, 'keyup', k[0]);
        if (k[1] === 1) {
            event.preventDefault();
            return false;
        }
    }
    return true;
};

larch.__onkeypress = function(event, keys) {
    var k = larch.__handleKeyEvent(event, keys);
    if (k !== undefined) {
        larch.postEvent(event.target, 'keypress', k[0]);
        if (k[1] === 1) {
            event.preventDefault();
            return false;
        }
    }
    return true;
};




//
//
// CLIENT-SERVER MESSAGING
//
//

larch.__connectionToPageLost = false;

larch.__serverMessageHandlers = {
    modify_page: function(message) {
        larch.__applyChanges(message.changes);
    },

    execute_js: function(message) {
        larch.__executeJS(message.js_code, "execution of JS from server");
    },

    add_dependencies: function(message) {
        var deps = message.deps;
        for (var i = 0; i < deps.length; i++) {
            larch.__addDependency(deps[i]);
        }
    },

    resource_messages: function(message) {
        var messages = message.messages;
        for (var i = 0; i < messages.length; i++) {
            var msg = messages[i];
            larch.__resourceMessage(msg.resource_id, msg.message);
        }
    },

    resources_disposed: function(message) {
        var resource_ids = message.resource_ids;
        for (var i = 0; i < resource_ids.length; i++) {
            larch.__destroyResource(resource_ids[i]);
        }
    },

    invalid_page: function(message) {
        if (!larch.__connectionToPageLost) {
            larch.__connectionToPageLost = true;
            noty({
                text: '<p class="invalid_page_style">Connection to page lost. Click to reload.<br><br><em>(the server may have been restarted)</em></p>',
                layout: "center",
                type: "error",
                modal: true,
                closeWith: ["click"],
                callback: {
                    onClose: function() {
                        location.reload();
                    }
                }
            });
        }
    },

    reload_page: function(message) {
        var loc = message.location;
        var get_params = message.get_params;

        if (loc === null  &&  get_params === null) {
            location.reload();
        }
        else {
            // Default to the current location
            if (loc === null) {
                loc = window.location.origin + window.location.pathname;
            }

            // Default to existing parameters
            var paramsString = '';
            if (get_params === null) {
                paramsString = window.location.search;
            }
            else {
                paramsString = '?' + $.param(get_params);
            }

            // Go
            window.location.replace(loc + paramsString);
        }
    },

    error_handling_event: function(message) {
        larch.showAlert(function() {
            var eventName = '<span class="event_error_event_name">' + message.event_name + '</span>';
            var header;
            if (message.event_seg_id !== null) {
                var eventSegID = message.event_seg_id, handlerSegID = message.handler_seg_id;
                var srcSegment = $('<span class="event_error_segment">segment</span>');
                srcSegment.mouseover(function() {larch.__highlightSegment(eventSegID)}).mouseout(function() {larch.__unhighlightSegment(eventSegID)});

                var hdlSegment = $('<span class="event_error_segment">segment</span>');
                hdlSegment.mouseover(function() {larch.__highlightSegment(handlerSegID)}).mouseout(function() {larch.__unhighlightSegment(handlerSegID)});

                var sentFrom = $('<span>sent from a </span>');
                sentFrom.append(srcSegment);
                sentFrom.append(' belonging to an instance of <span class="event_error_model_type">' + message.event_model_type_name + '</span>, ');

                var handledAt = $('<span>handled at a </span>');
                handledAt.append(hdlSegment);
                handledAt.append(' belonging to an instance of <span class="event_error_model_type">' + message.handler_model_type_name + '</span>');

                header = $('<div class="event_error_header">Error handling event ' + eventName + ', </div>');
                header.append(sentFrom);
                header.append(handledAt);
            }
            else {
                header = $('<div class="event_error_header">Error handling page event ' + eventName + '</div>');
            }

            var text = $('<div class="exception_in_alert"></div>');
            text.append(header);
            text.append(message.err_html);
            return text;
        });
    },

    error_retrieving_resource: function(message) {
         larch.showAlert(function() {
           var header;
            var rscSegID = message.rsc_seg_id;
            var rscSegment = $('<span class="event_error_segment">segment</span>');
            rscSegment.mouseover(function() {larch.__highlightSegment(rscSegID)}).mouseout(function() {larch.__unhighlightSegment(rscSegID)});

            var sentFrom = $('<span>associated with a </span>');
            sentFrom.append(rscSegment);
            sentFrom.append(' belonging to an instance of <span class="event_error_model_type">' + message.rsc_model_type_name + '</span>, ');

            header = $('<div class="event_error_header">Error retrieving resource </div>');
            header.append(sentFrom);

            var text = $('<div class="exception_in_alert"></div>');
            text.append(header);
            text.append(message.err_html);
            return text;
        });
    },

    error_during_update: function(message) {
        larch.showAlert(function() {
            var headerHtml = '<div class="event_error_header">Error while updating after handling events</div>';
            var text = '<div class="exception_in_alert">' + headerHtml + message.err_html + '</div>';
            return text;
        });
    },

    html_structure_fixes: function(message) {
        var fixes_by_model = message.fixes_by_model;

        var makeAlertFactory = function(fix_set) {
            return function() {
                var model_type_name = fix_set.model_type_name;
                var fixes = fix_set.fixes;

                var heading = $('<div>The following HTML structure problems were detected in a presentation of a <span class="event_error_model_type">' + model_type_name  + '</span></div>');
                var fixHTML = $('<div></div>');

                for (var j = 0; j < fixes.length; j++) {
                    var fix = fixes[j];
                    if (fix.fix_type === 'close_unclosed_tag') {
                        fixHTML.append($('<div>Added missing end tag<span class="event_error_model_type">&lt;/' + fix.tag  + '&gt;</span></div>'))
                    }
                    else if (fix.fix_type === 'drop_close_tag_with_no_matching_open_tag') {
                        fixHTML.append($('<div>Dropped orphan end tag<span class="event_error_model_type">&lt;/' + fix.tag  + '&gt;</span></div>'))
                    }
                }

                var text = $('<div></div>');
                text.append(heading);
                text.append(fixHTML);
                return text;
            };
        };

        for (var i = 0; i < fixes_by_model.length; i++) {
            larch.showAlert(makeAlertFactory(fixes_by_model[i]));
        }
    }
};

larch.__handleMessage = function(handlerMap, msg, targetDescription, sourceDescription) {
    var handler = handlerMap[msg.msgtype];
    if (handler !== undefined) {
        handler(msg);
    }
    else {
        noty({
            text: '<p class="invalid_page_style">' + targetDescription + ' received an unrecognised message from ' + sourceDescription + ' (message type <em>' + msg.msgtype + '</em>)</p>',
            layout: "center",
            type: "error",
            modal: true,
            closeWith: ["click"]
        });
        throw ('Larch: unrecognised message: ' + msg.msgtype);
    }
};

larch.__handleMessagesFromServer = function(messages) {
    for (var i = 0; i < messages.length; i++) {
        var msg = messages[i];
        larch.__handleMessage(larch.__serverMessageHandlers, msg, 'Ubiquitous Larch', 'server');
    }

    larch.__postModificationCleanup();
};


larch.__postModificationCleanup = function() {
    if (larch.__brokenSegmentIDs !== null) {
        larch.postDocumentEvent('broken_html_structure', larch.__brokenSegmentIDs);
        larch.__brokenSegmentIDs = null;
    }
};



larch.__buildElementEventMessage = function(segment_id, event_name, event_data) {
    return {
        msgtype: 'event',
        segment_id: segment_id,
        event_name: event_name,
        ev_data: event_data
    };
};



larch.__messageBlockCount = 0;
larch.__messageBuffer = [];
larch.__waitingForResponse = 0;

// Messages are handled in a synchronous manner....
// This does violate the normal way of interacting with web servers but....
// The normal async approach is to fire off a request and handle it when the response comes.
// We do much the same thing here, except that while we are awaiting a response, new requests will be buffered until the response arrives.
// Once the response has been received, a request can pass through.
//
// When handling messages asynchronously, it is quite trivial to create a situation where responding to an event could would involve a few
// seconds of server-side computation.
// If the client posts these requests fast enough (e.g. 10 per second, by dragging a slider control) you can build up a few minutes worth of
// server-side work. The server will process each message block in turn, taking a few seconds each time. It will respond to each one with some
// changes, which will gradually arrive at the client over the next few minutes, making the application unresponsive during this time.
// Building up a back-log of server-side work is VERY easy to do, and makes the application feel more laggy in these instances
// than if we buffer messages until we KNOW that the server is ready to work on them.
larch.__sendEventMessagesToServer = function(ev_messages) {
    if (larch.__waitingForResponse > 0) {
        // The last event has not yet received a response, buffer the messages
        larch.__messageBuffer = larch.__messageBuffer.concat(ev_messages);
    }
    else {
        // Generate a message block index
        var block_id = larch.__messageBlockCount;
        larch.__messageBlockCount++;

        // Join the message buffer with the messages that are to be sent
        var messages = larch.__messageBuffer.concat(ev_messages);
        larch.__messageBuffer = [];

        // Create the message block and serialise
        var block = {id: block_id, messages: messages};
        var block_json = JSON.stringify(block);

        // Create the POST data
        var post_data = {
            event_data: block_json
        };

        //console.log('EVENT ' + block_id + ': sent ' + ev_messages.length);
        // Increment waiting for response
        larch.__waitingForResponse++;
        $.ajax({
            type: 'POST',
            url: '/event/' + larch.__doc_url + '/' + larch.__view_id,
            data: post_data,
            success: function(msg) {
                //console.log('EVENT ' + block_id + ': received ' + msg.length);
                // We have a response; we are not waiting any more
                larch.__waitingForResponse--;
                larch.__handleMessagesFromServer(msg);

                if (larch.__waitingForResponse == 0  &&  larch.__messageBuffer.length > 0) {
                    // More messages have been buffered up: send them
                    larch.__sendEventMessagesToServer([]);
                }
            },
            dataType: 'json'
        });
    }
};

larch.__postEventMessage = function(ev_msg) {
    var messages = [];

    if (larch.__eventFactoryQueue !== null) {
        messages = larch.__eventFactoryQueue.buildMessageList();
        larch.__eventFactoryQueue.clear();
    }

    // Add the message that we are posting
    if (ev_msg !== null) {
        messages.push(ev_msg);
    }

    // Send
    larch.__sendEventMessagesToServer(messages);
};


larch.postEvent = function(src_element, event_name, event_data) {
    var segment_id = larch.__getSegmentIDForEvent(src_element);

    if (segment_id !== null) {
        var ev_msg = larch.__buildElementEventMessage(segment_id, event_name, event_data);
        larch.__postEventMessage(ev_msg);
    }
    else {
        larch.__warnUserUnableToGetSegmentIDForElement(src_element);
    }
};


larch.postDocumentEvent = function(event_name, event_data) {
    var ev_msg = {
        msgtype: 'event',
        segment_id: null,
        event_name: event_name,
        ev_data: event_data
    };

    larch.__postEventMessage(ev_msg);
};


larch.__eventFactoryQueue = null;


larch.__createEventFactoryQueue = function(onClear) {
    var q = {
        eventFactories: [],
        factoriesBySrcAndName: {},
        timeoutID: null,

        hasQueuedEventFactory: function(src_element, event_name) {
            var segment_id = larch.__getSegmentIDForEvent(src_element);

            if (segment_id !== null) {
                var key = segment_id + '__' + event_name;

                return q.factoriesBySrcAndName.hasOwnProperty(key);
            }
            else {
                larch.__warnUserUnableToGetSegmentIDForElement(src_element);
                return false;
            }
        },

        queueEventFactory: function(src_element, event_name, event_factory) {
            var segment_id = larch.__getSegmentIDForEvent(src_element);

            if (segment_id !== null) {
                var key = segment_id + '__' + event_name;

                var fac = {segment_id: segment_id, event_name: event_name, event_factory: event_factory};
                if (!q.hasQueuedEventFactory(src_element, event_name)) {
                    q.eventFactories.push(key);
                }
                q.factoriesBySrcAndName[key] = fac;
            }
            else {
                larch.__warnUserUnableToGetSegmentIDForElement(src_element);
            }
        },

        buildMessageList: function() {
            var messages = [];

            if (q.eventFactories.length > 0) {
                // Create events from factory queue
                for (var i = 0; i < q.eventFactories.length; i++) {
                    var key = q.eventFactories[i];
                    var fac = q.factoriesBySrcAndName[key];
                    var ev_data = fac.event_factory();
                    var msg = larch.__buildElementEventMessage(fac.segment_id, fac.event_name, ev_data);
                    messages.push(msg);
                }
            }

            return messages;
        },


        clear: function() {
            // Clear factory queue
            q.eventFactories = [];
            q.factoriesBySrcAndName = {};
            if (q.timeoutID !== null) {
                clearTimeout(q.timeoutID);
                q.timeoutID = null;
            }
            onClear();
        },


        setupTimeout: function() {
            if (q.timeoutID !== null) {
                clearTimeout(q.timeoutID);
            }

            q.timeoutID = setTimeout(function() {
                q.timeoutID = null;
                q.__sendAndClear();
            }, 1000);
        },


        __sendAndClear: function() {
            var messages = q.buildMessageList();
            q.clear();
            larch.__sendEventMessagesToServer(messages);
        }
    };

    return q;
};




larch.queueEventFactory = function(src_element, event_name, event_factory) {
    if (larch.__eventFactoryQueue === null) {
        larch.__eventFactoryQueue = larch.__createEventFactoryQueue(function() {
            larch.__eventFactoryQueue = null;
        });
    }
    larch.__eventFactoryQueue.queueEventFactory(src_element, event_name, event_factory);
    larch.__eventFactoryQueue.setupTimeout();
};



//
//
// WARNING AND ERROR NOTIFICATIONS FOR THE USER
//
//

larch.__enableAdditionalClientSideDebugging = false;

larch.__warnUserUnableToGetSegmentIDForElement = function(element) {
    if (larch.__enableAdditionalClientSideDebugging) {
        larch.showAlert(function() {
            var elem = $('<span class="event_error_segment">element</span>');
            elem.mouseover(function() {larch.__highlightElement(element);}).mouseout(function() {larch.__unhighlightElement(element);});

            var text = $('<span>Unable to get find the segment containing </span>');
            text.append(elem);
            text.append('<br>This is likely due to DOM manipulation operations moving the element outside the Larch document flow');
            return text;
        });
    }
};





//
//
// ALERTS BOX
//
//

larch.__alertBox = {
    visible: false,
    showQueued: false,
    alerts: [],
    body: null,
    selectorSpinner: null,

    changePage: function(pageIndex) {
        larch.__alertBox.body.children().remove();
        var pageFn = larch.__alertBox.alerts[pageIndex];
        larch.__alertBox.body.append(pageFn());
    },

    notifyClosed: function() {
        larch.__alertBox.visible = false;
        larch.__alertBox.showQueued = false;
        larch.__alertBox.alerts = [];
        larch.__alertBox.body = null;
        larch.__alertBox.selectorSpinner = null;
    }
};

larch.showAlert = function(contents) {
    larch.__alertBox.alerts.push(contents);

    if (!larch.__alertBox.showQueued) {
        larch.__alertBox.showQueued = true;

        var openAlert = function() {
            larch.__alertBox.visible = true;
            larch.__alertBox.selectorSpinner = $('<input name="value" value="0">');
            var header = $('<div class="alert_selector_header">Show alert </div>');
            header.append(larch.__alertBox.selectorSpinner);

            var lastPageIndex = larch.__alertBox.alerts.length - 1;

            larch.__alertBox.body = $('<div class="alert_body"></div>');
            var pageFn = larch.__alertBox.alerts[lastPageIndex];
            larch.__alertBox.body.append(pageFn());

            var text = $('<div class="alert_box"></div>')
            text.append(header);
            text.append(larch.__alertBox.body);

            noty({
                text: text,
                layout: "bottom",
                type: "alert",
                closeWith: [],
                callback: {
                    onClose: function() {
                        larch.__alertBox.notifyClosed();
                    }
                },
                buttons: [
                    {
                        addClass: 'btn btn-primary',
                        text: 'Ok',
                        onClick: function(notification) {
                             notification.close();
                        }
                    }
                ]
            });

            larch.__alertBox.selectorSpinner.spinner({
                spin: function(event, ui) {
                    larch.__alertBox.changePage(ui.value);
                },
                value: lastPageIndex,
                min: 0,
                max: lastPageIndex
            });
        };

        setTimeout(openAlert, 0);
    }
    else {
        if (larch.__alertBox.visible) {
            var lastPageIndex = larch.__alertBox.alerts.length - 1;
            larch.__alertBox.selectorSpinner.spinner("option", "max", lastPageIndex);
            larch.__alertBox.selectorSpinner.spinner("value", lastPageIndex);
            larch.__alertBox.changePage(lastPageIndex);
        }
    }
};

//
//
// RESOURCES
//
//

larch.__resourceIdToResource = {};
larch.__rscFetchCount = 0;

larch.__createResource = function(rscId) {
    var rsc = {
        __rscId: rscId,
        __messageHandlers: {},

        __handleMessage: function(message) {
            larch.__handleMessage(rsc.__messageHandlers, message, 'URL resource', 'server');
        },

        sendMessage: function(message) {
            larch.postDocumentEvent('resource_message', {
                resource_id: rsc.__rscId,
                message: message
            });
        }
    };

    larch.__resourceIdToResource[rscId] = rsc;
    return rsc;
};

larch.__destroyResource = function(rscId) {
   delete larch.__resourceIdToResource[rscId];
};

larch.__resourceMessage = function(resourceId, message) {
    larch.__resourceIdToResource[resourceId].__handleMessage(message);
};



larch.__createURLResource = function(rscId, rscUrl) {
    var rsc = larch.__createResource(rscId);
    rsc.url = rscUrl;
    rsc.__listeners = [];

    rsc.fetchString = function(handlerFn) {
        var x = larch.__rscFetchCount;
        larch.__rscFetchCount++;
        //console.log('Getting resource ');
        $.ajax({
            type: 'GET',
            url: rsc.url + '?_idx=' + x,        // Append an index to the URL; this seems to prevent the server from ignoring (!) the request. Why? don't know yet.... The server ignores _idx, so its not like it does anything...
            success: handlerFn
        });
    };

    rsc.fetchJSON = function(handlerFn) {
        var x = larch.__rscFetchCount;
        larch.__rscFetchCount++;
        //console.log('Getting JSON resource ' + x);
        $.ajax({
            type: 'GET',
            url: rsc.url + '?_idx=' + x,        // Append an index to the URL; this seems to prevent the server from ignoring (!) the request. Why? don't know yet.... The server ignores _idx, so its not like it does anything...
            success: handlerFn,
            dataType: 'json'
        });
    };

    rsc.addListener = function(listener) {
        for (var i = 0; i < rsc.__listeners.length; i++) {
            if (rsc.__listeners[i] === listener) {
                return;
            }
        }

        rsc.__listeners.push(listener);
    };

    rsc.removeListener = function(listener) {
        for (var i = 0; i < rsc.__listeners.length; i++) {
            if (rsc.__listeners[i] === listener) {
                delete rsc.__listeners[i];
                return;
            }
        }
    };

    rsc.__messageHandlers.modified = function(message) {
        for (var i = 0; i < rsc.__listeners.length; i++) {
            rsc.__listeners[i]();
        }
    };

    return rsc;
};



larch.__createChannelResource = function(rscId) {
    var rsc = larch.__createResource(rscId);
    rsc.__listeners = [];

    rsc.addListener = function(listener) {
        for (var i = 0; i < rsc.__listeners.length; i++) {
            if (rsc.__listeners[i] === listener) {
                return;
            }
        }

        rsc.__listeners.push(listener);
    };

    rsc.removeListener = function(listener) {
        for (var i = 0; i < rsc.__listeners.length; i++) {
            if (rsc.__listeners[i] === listener) {
                delete rsc.__listeners[i];
                return;
            }
        }
    };

    rsc.__messageHandlers.message = function(message) {
        for (var i = 0; i < rsc.__listeners.length; i++) {
            rsc.__listeners[i](message.message);
        }
    };

    return rsc;
};




//
//
// COMMANDS
//
//




larch.__commands = []


larch.registerCommand = function(keySequence, commandId, description) {
    var cmd = {
        keySequence: keySequence,
        commandId: commandId,
        description: description,
        invoke: function() {
            larch.postDocumentEvent('command', cmd.commandId);
        }
    };
    larch.__commands.push(cmd);
};

larch.registerClientSideCommand = function(keySequence, invokeFn, description) {
    var cmd = {
        keySequence: keySequence,
        invokeFn: invokeFn,
        description: description,
        invoke: function() {
            cmd.invokeFn();
        }
    };
    larch.__commands.push(cmd);
};

larch.unregisterCommand = function(commandId) {
    for (var i = 0; i < larch.__commands.length; i++) {
        if (larch.__commands[i].commandId === commandId) {
            delete larch.__commands[i];
            return;
        }
    }
};

larch.__compareKeySequences = function(commandSequence, enteredSequence) {
    if (enteredSequence.length === commandSequence.length) {
        for (var j = 0; j < enteredSequence.length; j++) {
            if (!larch.__matchKeyEvent(enteredSequence[j], commandSequence[j])) {
                return false;
            }
        }
        return true;
    }
    return false;
};

larch.__keySequenceStartsWith = function(commandSequence, enteredSequence) {
    if (enteredSequence.length <= commandSequence.length) {
        for (var j = 0; j < enteredSequence.length; j++) {
            if (!larch.__matchKeyEvent(enteredSequence[j], commandSequence[j])) {
                return false;
            }
        }
        return true;
    }
    return false;
};

larch.__presentKeySequence = function(keySequence) {
    var htmlSrc = '';
    for (var j = 0; j < keySequence.length; j++) {
        var key = keySequence[j];
        var ch = String.fromCharCode(key.keyCode);
        htmlSrc += '<span class="command_key">' + ch + '</span>';
    }
    return htmlSrc;
};



//
//
// POPUPS
//
//

larch.__notifyPopupClosed = function(popupID) {
    larch.postDocumentEvent('notify_popup_closed', popupID);
};




//
//
// COMMAND BAR HELP DIALOG
//
//

larch.__createCommandHelpDialog = function(commands, onClose) {
    // The help dialog structure
    var helpDialog = {
        dialog: null,

        close: function() {
            helpDialog.dialog.dialog("close");
        }
    };


    // Build the help dialog contents
    var table = $('<table class="command_table"></table>');

    var heading = $('<tr class="command_table_heading_row"><th><span class="command_table_heading">Key sequence</span></th><th><span class="command_table_heading">Description</span></th></tr>');
    table.append(heading);

    var makeLinkListener = function(cmd) {
        return function() {
            cmd.invoke();
            larch.__commandBar.close()
            return true;
        };
    };

    for (var i = 0; i < commands.length; i++) {
        var cmd = commands[i];
        var keys = larch.__presentKeySequence(cmd.keySequence);
        var cmdSeqQ = $('<td class="command_table command_table_key_seq">' + keys + '</td>');
        var descriptionLink = $('<span class="command_table_desc">' + cmd.description + '</a>');
        descriptionLink.on("click", makeLinkListener(cmd));
        var descriptionQ = $('<td></td>');
        descriptionQ.append(descriptionLink);
        var rowQ = $('<tr></tr>').append(cmdSeqQ).append(descriptionQ);
        table.append(rowQ);
    }
    var div = $('<div class="command_table_container"></div>');
    div.append('<p>The following commands are available:</p>');
    div.append(table);


    // Set the dialog attribute of the structure
    helpDialog.dialog = $(div).dialog({
        close: function(event, ui) {
            onClose();
        }
    });

    return helpDialog;
};



//
//
// COMMAND BAR
//
//

larch.__createCommandBar = function(onClose) {
    var cmdBar = {
        partialCommandKeySequence: [],
        barNoty: null,
        barNotyAppearing: true,
        closeQueued: false,
        helpDialog: null,


        //
        // SHOW HELP DIALOG
        //
        showHelpDialog: function() {
            if (cmdBar.helpDialog === null) {
                // Find all matching commands
                var matchingCommands = [];

                for (var i = 0; i < larch.__commands.length; i++) {
                    var match = larch.__commands[i];
                    if (larch.__keySequenceStartsWith(match.keySequence, cmdBar.partialCommandKeySequence)) {
                        matchingCommands.push(match);
                    }
                }

                cmdBar.helpDialog = larch.__createCommandHelpDialog(matchingCommands, function() {
                    cmdBar.helpDialog = null;
                });
            }
        },

        //
        // CLOSE HELP DIALOG
        //
        closeHelpDialog: function() {
            if (cmdBar.helpDialog !== null) {
                cmdBar.helpDialog.close();
            }
        },

        //
        // TOGGLE HELP DIALOG
        //
        toggleHelpDialog: function() {
            if (cmdBar.helpDialog !== null) {
                cmdBar.closeHelpDialog();
            }
            else {
                cmdBar.showHelpDialog();
            }
        },

        //
        // CLOSE COMMAND BAR
        //
        close: function() {
            cmdBar.closeHelpDialog();

            if (cmdBar.barNotyAppearing) {
                // Noty is in the process of appearing; it cannot be closed yet; queue the close
                cmdBar.closeQueued = true;
            }
            else {
                cmdBar.barNoty.close();
            }
        },


        //
        // KEY SEQUENCE MODIFIED
        //
        __keySequenceModified: function() {
            var matchingCommand = null;
            for (var i = 0; i < larch.__commands.length; i++) {
                var cmd = larch.__commands[i];
                if (larch.__compareKeySequences(cmd.keySequence, cmdBar.partialCommandKeySequence)) {
                    matchingCommand = cmd;
                    break;
                }
            }

            if (matchingCommand !== null) {
                // Found a command

                // Invoke it
                matchingCommand.invoke();

                // We are done
                cmdBar.close();
            }

            // Partial command; update the noty:
            var notyText = 'Command: ';
            notyText += larch.__presentKeySequence(cmdBar.partialCommandKeySequence);
            notyText += ' - or <span class="command_special_key">ESC</span> to cancel or <span class="command_special_key">H</span> for help';

            cmdBar.barNoty.setText(notyText);
        },


        //
        // ADD KEY
        //
        addKey: function(key) {
            cmdBar.partialCommandKeySequence.push(key);
            cmdBar.__keySequenceModified();
        },


        //
        // REMOVE KEY
        //
        removeKey: function() {
            cmdBar.partialCommandKeySequence.pop();
            cmdBar.__keySequenceModified();
        },

        //
        // KEY RESPONSE FUNCTION
        //
        onKeyDown: function(event) {
            if (event.keyCode === 27) {
                // ESC - Close the command bar
                cmdBar.close();
            }
            else if (event.keyCode === 72) {
                // H - Toggle help dialog

                cmdBar.toggleHelpDialog();
            }
            else if (event.keyCode === 8) {
                // Backspace - delete a key

                cmdBar.removeKey();
            }
            else {
                // Another key in the sequence
                var k = larch.__eventToKey(event);
                cmdBar.addKey(k);
            }
        }
    };


    // We have started a command
    cmdBar.barNoty = noty({
        text: 'Command started  --  enter key sequence or <span class="command_special_key">ESC</span> to cancel or <span class="command_special_key">H</span> for help',
        type: 'information',
        layout: 'bottom',
        closeWith: ['click'],
        callback: {
            onClose: function() {
                onClose();
            },
            afterShow: function() {
                // Finished appearing
                cmdBar.barNotyAppearing = false;

                if (cmdBar.closeQueued) {
                    // A close request has been queued; queue a close
                    setTimeout(function() {
                        cmdBar.close();
                    }, 0);
                }
            }
        }
    });

    return cmdBar;
};


larch.__commandBar = null;

larch.__showCommandBar = function() {
    larch.__commandBar = larch.__createCommandBar(function() {
            larch.__commandBar = null;
        }
    );
};




larch.__setupCommandListeners = function() {
    document.body.onkeydown = function(event) {
        if (larch.__commandBar !== null) {
            // The command bar is active: send the event there
            event.preventDefault();
            larch.__commandBar.onKeyDown(event);
            return false;
        }
        else {
            // Check for ESC
            if (event.keyCode === 27) {
                event.preventDefault();
                // Show the command bar
                larch.__showCommandBar();

                return false;
            }
        }

        return true;
    };
};



//
//
// PAGE LIVELINESS
//
//

larch.__liveIntervalID = null;

larch.__enableLiveliness = function() {
    if (larch.__liveIntervalID === null) {
        larch.__liveIntervalID = setInterval(function() {
            larch.__postEventMessage(null);
        }, 1000);
    }
};

larch.__disableLiveliness = function() {
    if (larch.__liveIntervalID !== null) {
        clearInterval(larch.__liveIntervalID);
        larch.__liveIntervalID = null;
    }
};

larch.initLivelinessToggle = function(node) {
    var toggle = $(node);
    if (toggle.hasClass('larch_liveliness_on')) {
        larch.__enableLiveliness();
    }

    toggle.click(function() {
        // Toggle
        var enabled = toggle.hasClass('larch_liveliness_on');
        if (enabled) {
            // Disable
            toggle.removeClass('larch_liveliness_on');
            larch.__disableLiveliness();
        }
        else {
            // Enable
            toggle.addClass('larch_liveliness_on');
            larch.__enableLiveliness();
        }
    });
};




//
//
// ON DOCUMENT READY
//
//

larch.__onDocumentReady = function(initialisers) {
    larch.__register_segments();
    try {
        larch.__executeNodeScripts(initialisers);
    }
    finally {
        larch.__setupCommandListeners();
    }
    larch.__postModificationCleanup();

    // Activate additional client side debugging toggle command: C-D
    larch.registerClientSideCommand([larch.__createKey(67), larch.__createKey(68)],
        function() {
            larch.__enableAdditionalClientSideDebugging = true;
        },
         'Enable additional client side debugging'
    );

    // Deactivate additional client side debugging toggle command: C-X
    larch.registerClientSideCommand([larch.__createKey(67), larch.__createKey(88)],
        function() {
            larch.__enableAdditionalClientSideDebugging = false;
        },
         'Disable additional client side debugging'
    );

    // Before unload
    window.onbeforeunload = function() {
        larch.postDocumentEvent('close_page', null);
    };

    // CSRF Token setup
    var csrf = $.cookie('csrftoken');
    if (csrf != null) {
        // Adapted from Django DOCS
        var csrfSafeMethod = function(method) {
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        };

        $.ajaxSetup({
            crossDomain: false,
            beforeSend: function(xhr, settings) {
                if (!csrfSafeMethod(settings.type)) {
                    xhr.setRequestHeader('X-CSRFToken', csrf);
                }
            }
        });
    }
};

