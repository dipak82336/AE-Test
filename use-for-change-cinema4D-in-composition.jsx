(function () {
    // 1. PATH SETUP
    var templatePath = Folder.myDocuments.fsName + "/AE_C4D_Template_Fixed.aep"; // New Name just in case
    var templateFile = new File(templatePath);
    var undoStarted = false; // ટ્રેકર

    // ==================================================
    // 🛑 PHASE 1: SETUP (If file is missing)
    // ==================================================
    if (!templateFile.exists) {
        var setupComp = app.project.items.addComp("MASTER_C4D_TEMPLATE", 1920, 1080, 1, 10, 30);
        setupComp.openInViewer();

        alert("⚙️ SETUP MODE\n\n1. Select 'Cinema 4D' & OK.\n2. I will save the Master File.");

        app.executeCommand(app.findMenuCommandId("Composition Settings..."));
        app.project.save(templateFile);

        alert("✅ SETUP DONE!\nSaved to Documents.\n\n👉 NOW RUN THIS SCRIPT AGAIN!");
        app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        return;
    }

    // ==================================================
    // 🚀 PHASE 2: AUTOMATIC RUN (The Fix)
    // ==================================================

    // 🔥 STEP 1: IMPORT OUTSIDE THE UNDO GROUP (This fixes the Mismatch Error)
    // આનાથી AE કન્ફ્યુઝ નહીં થાય.
    var importOptions = new ImportOptions(templateFile);
    var importedFolder;

    try {
        importedFolder = app.project.importFile(importOptions);
    } catch (e) {
        alert("Import Failed: " + e.toString());
        return;
    }

    // 🔥 STEP 2: NOW START UNDO GROUP
    app.beginUndoGroup("Auto 3D Text");
    undoStarted = true;

    try {
        // --- Find Master Comp ---
        var masterComp = null;
        for (var i = 1; i <= importedFolder.numItems; i++) {
            if (importedFolder.item(i) instanceof CompItem) {
                masterComp = importedFolder.item(i);
                break;
            }
        }

        if (!masterComp) {
            alert("Error: Template is empty. Please re-run setup.");
            return;
        }

        // --- DUPLICATE & MOVE OUT ---
        var finalComp = masterComp.duplicate();
        finalComp.name = "3D_Text_Auto_" + parseInt(Math.random() * 1000);
        finalComp.parentFolder = app.project.rootFolder; // Move to root

        // --- CLEANUP ---
        importedFolder.remove(); // Delete original folder

        // --- EDIT ---
        finalComp.openInViewer();
        var textLayer = finalComp.layers.addText("AUTO 3D");
        textLayer.threeDLayer = true;
        textLayer.position.setValue([960, 540, 0]);

        // --- EXTRUSION ---
        var geoGroup = textLayer.property("ADBE Extrsn Options Group");
        if (geoGroup) {
            geoGroup.expanded = true;
            var depthProp = geoGroup.property("ADBE Extrsn Depth");

            if (depthProp.canSetExpression) {
                depthProp.expression = "150";
            } else {
                depthProp.setValue(150);
            }
            try { geoGroup.property("ADBE Bevel Styles").setValue(2); } catch (e) { }
        }

    } catch (err) {
        alert("Script Error: " + err.toString());
    } finally {
        // 🔥 STEP 3: CLOSE UNDO GROUP SAFELY
        if (undoStarted) {
            app.endUndoGroup();
        }
    }

})();