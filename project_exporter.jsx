/*************************************************************************
 * project_exporter.jsx
 *
 * Description: Exports After Effects Compositions to AIGEN JSON Format.
 * Use this to "Reverse Engineer" your AE designs back into templates.
 *************************************************************************/

{
    // --- Polyfills ---
    if (!Object.keys) {
        Object.keys = (function () {
            var hasOwnProperty = Object.prototype.hasOwnProperty,
                hasDontEnumBug = !({ toString: null }).propertyIsEnumerable('toString'),
                dontEnums = [
                    'toString',
                    'toLocaleString',
                    'valueOf',
                    'hasOwnProperty',
                    'isPrototypeOf',
                    'propertyIsEnumerable',
                    'constructor'
                ],
                dontEnumsLength = dontEnums.length;

            return function (obj) {
                if (typeof obj !== 'function' && (typeof obj !== 'object' || obj === null)) {
                    throw new TypeError('Object.keys called on non-object');
                }

                var result = [], prop, i;

                for (prop in obj) {
                    if (hasOwnProperty.call(obj, prop)) {
                        result.push(prop);
                    }
                }

                if (hasDontEnumBug) {
                    for (i = 0; i < dontEnumsLength; i++) {
                        if (hasOwnProperty.call(obj, dontEnums[i])) {
                            result.push(dontEnums[i]);
                        }
                    }
                }
                return result;
            };
        }());
    }

    function buildUI(thisObj) {
        var win = (thisObj instanceof Panel) ? thisObj : new Window("palette", "AIGEN Exporter", undefined, { resizeable: true });
        win.orientation = "column";
        win.alignChildren = ["fill", "top"];

        var groupList = win.add("panel", undefined, "Select Compositions to Export");
        groupList.orientation = "column";
        groupList.alignChildren = ["fill", "fill"];
        groupList.preferredSize = [300, 400];

        var listbox = groupList.add("listbox", undefined, [], { multiselect: true });

        // Populate Listbox
        var comps = [];
        for (var i = 1; i <= app.project.numItems; i++) {
            if (app.project.item(i) instanceof CompItem) {
                comps.push(app.project.item(i));
                listbox.add("item", app.project.item(i).name);
            }
        }

        var btnGroup = win.add("group");
        btnGroup.orientation = "row";
        var refreshBtn = btnGroup.add("button", undefined, "Refresh List");
        var selectAllBtn = btnGroup.add("button", undefined, "Select All");
        var exportBtn = btnGroup.add("button", undefined, "Export to JSON");

        refreshBtn.onClick = function () {
            listbox.removeAll();
            comps = [];
            for (var i = 1; i <= app.project.numItems; i++) {
                if (app.project.item(i) instanceof CompItem) {
                    comps.push(app.project.item(i));
                    listbox.add("item", app.project.item(i).name);
                }
            }
        }

        selectAllBtn.onClick = function () {
            for (var i = 0; i < listbox.items.length; i++) {
                listbox.items[i].selected = true;
            }
        }

        exportBtn.onClick = function () {
            var selectedComps = [];
            for (var i = 0; i < listbox.items.length; i++) {
                if (listbox.items[i].selected) {
                    selectedComps.push(comps[i]);
                }
            }

            if (selectedComps.length === 0) {
                alert("Please select at least one composition.");
                return;
            }

            var outputFile = File.saveDialog("Save AIGEN JSON", "*.json");
            if (!outputFile) return;

            try {
                // 1. Collect all dependencies (recursive)
                var allComps = [];
                var allAssets = [];
                var processedCompIds = {}; // To avoid duplicates
                var processedAssetIds = {};

                for (var i = 0; i < selectedComps.length; i++) {
                    collectDependencies(selectedComps[i], allComps, allAssets, processedCompIds, processedAssetIds);
                }

                // 2. Prepare Output Directory
                var jsonFolder = outputFile.parent;
                var baseName = outputFile.name.replace(".json", "");
                var assetsFolder = new Folder(jsonFolder.fsName + "/" + baseName);

                if (!assetsFolder.exists) {
                    assetsFolder.create();
                }

                // 3. Copy Assets and Update Paths
                var exportedAssets = [];
                for (var j = 0; j < allAssets.length; j++) {
                    var assetItem = allAssets[j];
                    var originalFile = assetItem.file;

                    if (originalFile && originalFile.exists) {
                        var targetPath = assetsFolder.fsName + "/" + originalFile.name;
                        var targetFile = new File(targetPath);
                        originalFile.copy(targetFile);

                        exportedAssets.push({
                            id: "asset_" + assetItem.id,
                            name: assetItem.name,
                            path: baseName + "/" + originalFile.name, // Relative path for JSON
                            width: assetItem.width,
                            height: assetItem.height
                        });
                    } else {
                        // Handle missing files or solids/placeholders if necessary
                        // For now, skip or log
                    }
                }

                // 4. Generate JSON Data
                var projectData = {
                    projectSettings: {
                        width: allComps[0].width, // Assuming first selected is main
                        height: allComps[0].height,
                        frameRate: allComps[0].frameRate,
                        duration: allComps[0].duration,
                        bitsPerChannel: app.project.bitsPerChannel
                    },
                    assets: exportedAssets,
                    compositions: []
                };

                for (var k = 0; k < allComps.length; k++) {
                    projectData.compositions.push(processComp(allComps[k]));
                }

                if (outputFile.open("w")) {
                    outputFile.write(JSON.stringify(projectData, null, 2));
                    outputFile.close();
                    alert("Export Successful!\nSaved to: " + outputFile.fsName + "\nAssets saved to: " + assetsFolder.fsName);
                } else {
                    alert("Could not write to file.");
                }
            } catch (e) {
                alert("Export Failed: " + e.toString() + "\nLine: " + e.line);
            }
        }

        win.layout.layout(true);
        return win;
    }

    // --- DEPENDENCY COLLECTION ---
    function collectDependencies(comp, allComps, allAssets, processedCompIds, processedAssetIds) {
        if (processedCompIds[comp.id]) return; // Already processed

        processedCompIds[comp.id] = true;
        allComps.push(comp);

        for (var i = 1; i <= comp.numLayers; i++) {
            var layer = comp.layer(i);
            if (layer instanceof AVLayer) {
                var source = layer.source;
                if (source) {
                    if (source instanceof CompItem) {
                        collectDependencies(source, allComps, allAssets, processedCompIds, processedAssetIds);
                    } else if (source instanceof FootageItem) {
                        // Check if it has a file (ignore solids for asset list, usually)
                        // Solids usually have mainSource instanceof SolidSource
                        if (source.mainSource && source.mainSource instanceof FileSource) {
                            if (!processedAssetIds[source.id]) {
                                processedAssetIds[source.id] = true;
                                allAssets.push(source);
                            }
                        }
                    }
                }
            }
        }
    }

    // --- EXPORT LOGIC ---

    function processComp(comp) {
        var compData = {
            name: comp.name,
            width: comp.width,
            height: comp.height,
            frameRate: comp.frameRate,
            duration: comp.duration,
            layers: []
        };

        // Markers
        if (comp.markerProperty && comp.markerProperty.numKeys > 0) {
            compData.markers = [];
            for (var m = 1; m <= comp.markerProperty.numKeys; m++) {
                compData.markers.push({
                    name: comp.markerProperty.keyValue(m).comment,
                    time: comp.markerProperty.keyTime(m)
                });
            }
        }

        for (var i = comp.numLayers; i >= 1; i--) {
            var layer = comp.layer(i);
            try {
                var layerData = processLayer(layer);
                if (layerData) compData.layers.push(layerData);
            } catch (e) {
                alert("Error processing layer '" + layer.name + "': " + e.toString());
            }
        }

        return compData;
    }

    function getLayerType(layer) {
        if (layer instanceof CameraLayer) return "Camera";
        if (layer instanceof LightLayer) return "Light";
        if (layer.sourceText !== undefined) return "Text";
        if (layer.matchName === "ADBE Vector Layer") return "Shape";
        if (layer.isNull) return "Null";
        // if (layer.adjustmentLayer) return "Adjustment Layer"; // REMOVED: Let source determine type (e.g. Solid)
        if (layer instanceof AVLayer && layer.source) {
            if (layer.source instanceof CompItem) return "Pre-comp";
            if (layer.source.mainSource instanceof SolidSource) return "Solid";
            if (layer.hasAudio && !layer.hasVideo) return "Audio";
            if (layer.source instanceof FootageItem) return "Footage";
        }
        return "Unknown";
    }

    function processLayer(layer) {
        var data = {
            name: layer.name,
            index: layer.index,
            type: getLayerType(layer),
            inPoint: layer.inPoint,
            outPoint: layer.outPoint,
            startTime: layer.startTime,
            attributes: {}
        };

        // Attributes
        if (layer.threeDLayer) data.attributes.threeD = true;
        if (layer.adjustmentLayer) data.attributes.adjustmentLayer = true;
        if (layer.locked) data.attributes.locked = true;
        if (layer.shy) data.attributes.shy = true;
        if (layer.solo) data.attributes.solo = true;
        if (layer.blendingMode !== BlendingMode.NORMAL) data.attributes.blendingMode = getBlendingModeName(layer.blendingMode);

        // Parent
        if (layer.parent) data.parent = layer.parent.name;

        // Track Matte
        if (layer.hasTrackMatte) {
            data.attributes.trackMatte = { mode: getTrackMatteName(layer.trackMatteType) };
        }

        // Specific Layer Data
        if (data.type === "Text") {
            data.sourceText = layer.property("Text").property("Source Text").value.text;
            data.properties = {};
            data.properties.Text = parsePropertyGroup(layer.property("Text"), layer.inPoint);
            var animators = extractAnimatorsFromRobustData(data.properties.Text);
            if (animators.length > 0) {
                data.textAnimators = animators;
            }

        } else if (data.type === "Shape") {
            data.properties = {};
            data.properties.Contents = parsePropertyGroup(layer.property("Contents"), layer.inPoint);
        } else if (data.type === "Solid") {
            data.properties = { sourceParameters: { color: layer.source.mainSource.color } };
        } else if (data.type === "Footage" || data.type === "Audio") {
            // Link to Asset ID
            if (layer.source) {
                data.assetId = "asset_" + layer.source.id;
            }
        } else if (data.type === "Pre-comp") {
            // Link to Comp Name (which is unique enough for now, or use ID if we want to be strict)
            // Using name to match AIGEN structure which usually references comps by name or ID.
            // Let's use name for readability as per AIGEN spec usually.
            data.refId = layer.source.name;
        }

        // Transform
        if (!data.properties) data.properties = {};
        data.properties.Transform = parsePropertyGroup(layer.property("Transform"), layer.inPoint);

        // Effects
        if (layer.property("Effects") && layer.property("Effects").numProperties > 0) {
            data.effects = parsePropertyGroup(layer.property("Effects"), layer.inPoint);
        }

        // Masks
        if (layer.mask && layer.mask.numProperties > 0) {
            data.masks = parsePropertyGroup(layer.mask, layer.inPoint);
        }

        return data;
    }

    // --- ROBUST RECURSIVE PROPERTY PARSER (Adapted from User's Script) ---
    function getKeyframeData(prop, layerInPoint) {
        var keyframes = [];
        for (var i = 1; i <= prop.numKeys; i++) {
            var keyData = { time: prop.keyTime(i) - layerInPoint }; // Make relative
            var keyValue = prop.keyValue(i);
            if (keyValue instanceof TextDocument) {
                keyData.value = {
                    text: keyValue.text,
                    font: keyValue.font,
                    fontSize: keyValue.fontSize,
                    fillColor: keyValue.fillColor,
                    justification: getJustificationName(keyValue.justification)
                };
            } else {
                keyData.value = convertValue(keyValue);
            }
            // Add easing if possible (simplified)
            // keyData.easeIn = prop.keyInTemporalEase(i);
            // keyData.easeOut = prop.keyOutTemporalEase(i);
            keyframes.push(keyData);
        }
        return keyframes;
    }

    function parsePropertyGroup(propGroup, layerInPoint) {
        var data = {};
        if (!propGroup || propGroup.numProperties === 0) { return null; }

        for (var i = 1; i <= propGroup.numProperties; i++) {
            var currentProp = propGroup.property(i);

            // Basic check: must be enabled
            if (!currentProp.enabled) continue;

            // --- FILTERING LOGIC ---
            // We only want properties that are actually used (modified, animated, or have expressions).
            // Exceptions: 
            // 1. Groups (we need to traverse them to find modified children).
            // 2. "Source Text" (always export content).
            // 3. "Transform" properties (often useful to have defaults, but strict filtering is cleaner).

            var isGroup = (currentProp.propertyType === PropertyType.NAMED_GROUP || currentProp.propertyType === PropertyType.INDEXED_GROUP);
            var keep = false;

            if (isGroup) {
                // For groups, we assume we keep them if they have valid children (checked later)
                keep = true;
            } else {
                // For properties, check if relevant
                var isModified = false;
                try { isModified = currentProp.isModified; } catch (e) { } // isModified might fail on some props

                var isAnimated = (currentProp.numKeys > 0);
                var hasExpression = (currentProp.expressionEnabled);
                var isCritical = (currentProp.matchName === "ADBE Text Document"); // Always keep Source Text

                if (isModified || isAnimated || hasExpression || isCritical) {
                    keep = true;
                }
            }

            if (!keep) continue;
            // -----------------------

            var propInfo = {
                matchName: currentProp.matchName,
                name: currentProp.name
            };

            if (!isGroup) {
                // It is a Property
                if (currentProp.matchName === "ADBE Text Document") {
                    try {
                        var textDocument = currentProp.value;
                        propInfo.value = {
                            text: textDocument.text,
                            font: textDocument.font,
                            fontSize: textDocument.fontSize,
                            fillColor: textDocument.fillColor,
                            justification: getJustificationName(textDocument.justification)
                        };
                    } catch (e) {
                        propInfo.value = "Could not read TextDocument properties.";
                    }
                } else {
                    try {
                        propInfo.value = convertValue(currentProp.value);
                    } catch (e) {
                        propInfo.value = "Error reading value";
                    }
                }

                if (currentProp.numKeys > 0) {
                    propInfo.animated = true;
                    propInfo.keyframes = getKeyframeData(currentProp, layerInPoint);
                } else {
                    propInfo.animated = false;
                }

                if (currentProp.expressionEnabled) {
                    propInfo.expression = currentProp.expression;
                }

            }

            if (currentProp.numProperties > 0) {
                var nestedProps = parsePropertyGroup(currentProp, layerInPoint);
                // Only add the group if it actually has relevant children
                if (nestedProps && Object.keys(nestedProps).length > 0) {
                    propInfo.properties = nestedProps;
                } else {
                    // If group ended up empty after filtering children, skip this group entirely
                    continue;
                }
            }

            // Use name as key for readability, but matchName is available in propInfo
            var key = currentProp.name;
            // Handle duplicates by appending index if needed (rare in AE unless effects)
            if (data[key]) key = key + "_" + i;

            data[key] = propInfo;
        }
        return data;
    }

    function convertValue(val) {
        if (val instanceof Shape) {
            return {
                vertices: val.vertices,
                inTangents: val.inTangents,
                outTangents: val.outTangents,
                isClosed: val.closed
            };
        }
        return val;
    }

    function getBlendingModeName(mode) {
        for (var key in BlendingMode) {
            if (BlendingMode[key] === mode) return key;
        }
        return "Normal";
    }

    function getTrackMatteName(mode) {
        if (mode === TrackMatteType.ALPHA) return "Alpha";
        if (mode === TrackMatteType.ALPHA_INVERTED) return "Alpha Inverted";
        if (mode === TrackMatteType.LUMA) return "Luma";
        if (mode === TrackMatteType.LUMA_INVERTED) return "Luma Inverted";
        return "None";
    }

    function extractAnimatorsFromRobustData(textProps) {
        var animatorsList = [];
        if (!textProps || !textProps["Animators"] || !textProps["Animators"].properties) return animatorsList;

        var animatorsGroup = textProps["Animators"].properties;

        for (var key in animatorsGroup) {
            if (!animatorsGroup.hasOwnProperty(key)) continue;
            var animator = animatorsGroup[key];

            // We assume anything in "Animators" group is an Animator if it has properties
            if (animator.matchName === "ADBE Text Animator") {
                var animData = {
                    name: animator.name,
                    animatorProperties: [],
                    selectors: []
                };

                if (animator.properties) {
                    // 1. Selectors
                    if (animator.properties["Selectors"] && animator.properties["Selectors"].properties) {
                        var selectorsGroup = animator.properties["Selectors"].properties;
                        for (var selKey in selectorsGroup) {
                            if (selectorsGroup.hasOwnProperty(selKey)) {
                                var sel = selectorsGroup[selKey];
                                animData.selectors.push({
                                    name: sel.name,
                                    properties: sel.properties // Keep the robust structure for selector properties
                                });
                            }
                        }
                    }

                    // 2. Animator Properties (Fill, Stroke, Position, etc.)
                    if (animator.properties["Properties"] && animator.properties["Properties"].properties) {
                        var propsGroup = animator.properties["Properties"].properties;
                        for (var propKey in propsGroup) {
                            if (propsGroup.hasOwnProperty(propKey)) {
                                var prop = propsGroup[propKey];
                                animData.animatorProperties.push({
                                    property: prop.name, // e.g. "Position", "Opacity"
                                    value_data: prop     // Pass the full robust property object
                                });
                            }
                        }
                    }
                }
                animatorsList.push(animData);
            }
        }
        return animatorsList;
    }

    function getJustificationName(j) {
        if (j === ParagraphJustification.CENTER_JUSTIFY) return "CENTER";
        if (j === ParagraphJustification.RIGHT_JUSTIFY) return "RIGHT";
        return "LEFT";
    }

    // Run UI
    var win = buildUI(this);
    if (win instanceof Window) {
        win.center();
        win.show();
    }
}
