/*************************************************************************
 * json_engine.jsx
 * AIGEN v3.1 - Universal Execution Entry Point
 *************************************************************************/

#include "engine_library.jsxinc"
#include "engine_builder.jsxinc"

    (function runEngine() {
        var jsonFile = File.openDialog("Select JSON Blueprint File", "*.json");
        if (!jsonFile || !jsonFile.exists) return;

        var blueprint;
        try {
            jsonFile.open('r');
            var jsonContent = jsonFile.read();
            jsonFile.close();
            blueprint = JSON.parse(jsonContent);
        } catch (e) {
            alert("JSON Parse Error:\n" + e.toString());
            return;
        }

        if (!blueprint.compositions || blueprint.compositions.length === 0) {
            alert("No compositions found in blueprint.");
            return;
        }

        app.beginUndoGroup("AIGEN Build v3.1");
        try {
            if (blueprint.projectSettings) {
                if (blueprint.projectSettings.bitsPerChannel) app.project.bitsPerChannel = blueprint.projectSettings.bitsPerChannel;
                if (blueprint.projectSettings.expressionEngine) app.project.expressionEngine = blueprint.projectSettings.expressionEngine;
            }

            var importedAssets = {};
            if (blueprint.assets && blueprint.assets.length > 0) {
                for (var i = 0; i < blueprint.assets.length; i++) {
                    var assetData = blueprint.assets[i];
                    var assetPath = assetData.path;
                    var assetFile;

                    // Handle Absolute vs Relative Paths
                    if (assetPath.indexOf(":") > -1 || assetPath.charAt(0) == "/") {
                        assetFile = new File(assetPath);
                    } else {
                        assetFile = new File(jsonFile.parent.fsName + "/" + assetPath);
                    }

                    if (assetFile.exists) {
                        var io = new ImportOptions(assetFile);
                        var item = app.project.importFile(io);
                        importedAssets[assetData.id] = item;
                    } else {
                        alert("Asset Missing: " + assetFile.fsName);
                    }
                }
            }

            var createdComps = {};
            for (var j = 0; j < blueprint.compositions.length; j++) {
                var compData = blueprint.compositions[j];
                var newComp = AEGP.buildComposition(compData, createdComps, importedAssets);
                if (newComp) createdComps[compData.name] = newComp;
            }
        } catch (e) {
            alert("CRITICAL BUILD ERROR:\n" + e.toString() + "\nLine: " + e.line);
        } finally {
            app.endUndoGroup();
            alert("AIGEN Build Complete!");
        }
    })();