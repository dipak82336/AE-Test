import json
import sys
import os

def format_value(val):
    """Formats a value for YAML output."""
    if isinstance(val, str):
        return f'"{val}"'
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, list):
        # Compact list format for vectors/colors: [0, 1, 2]
        return str(val).replace("'", '"')
    return str(val)

def indent(level):
    return "  " * level

def write_property(key, prop_data, level, lines):
    """Recursive function to write properties to YAML lines."""
    # Skip empty or whitespace-only keys
    if not key or not key.strip():
        return

    indent_str = indent(level)
    prefix = indent_str
    
    # If it's a simple value wrapper
    if isinstance(prop_data, dict) and "value" in prop_data and "animated" in prop_data and not prop_data["animated"]:
        val = prop_data["value"]
        # Special handling for Text Document object
        if isinstance(val, dict) and "text" in val:
             lines.append(f"{prefix}{key}:")
             lines.append(f"{prefix}  value:")
             for k, v in val.items():
                 lines.append(f"{prefix}    {k}: {format_value(v)}")
        else:
            lines.append(f"{prefix}{key}: {{ value: {format_value(val)} }}")
        return

    # If it's animated
    if isinstance(prop_data, dict) and "animated" in prop_data and prop_data["animated"]:
        lines.append(f"{prefix}{key}:")
        lines.append(f"{prefix}  animated: true")
        if "keyframes" in prop_data:
            lines.append(f"{prefix}  keyframes:")
            for kf in prop_data["keyframes"]:
                # Format keyframe compactly: - { time: 0, value: 10 }
                kf_str = ", ".join([f"{k}: {format_value(v)}" for k, v in kf.items()])
                lines.append(f"{prefix}    - {{ {kf_str} }}")
        return

    # If it's a group (has 'properties')
    if isinstance(prop_data, dict) and "properties" in prop_data:
        lines.append(f"{prefix}{key}:")
        if "matchName" in prop_data:
             pass # We can skip matchName in YAML if not strictly needed, or add it as comment
        
        # Recurse
        for sub_key, sub_prop in prop_data["properties"].items():
            write_property(sub_key, sub_prop, level + 1, lines)
        return

    # Fallback for direct values (if simplified)
    lines.append(f"{prefix}{key}: {format_value(prop_data)}")

def convert_json_to_aigen(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    lines = []
    
    # Project Settings
    if "projectSettings" in data:
        lines.append("projectSettings:")
        for k, v in data["projectSettings"].items():
            lines.append(f"  {k}: {v}")
        lines.append("")

    # Assets
    if "assets" in data:
        lines.append("assets:")
        for asset in data["assets"]:
            lines.append(f"  - id: \"{asset.get('id')}\"")
            # Use the path as is (relative) or convert if needed. 
            # AIGEN usually expects absolute or relative to project. 
            # Since the JSON has relative paths to the sidecar folder, we can keep them.
            # But we might want to ensure backslashes for Windows if that's the convention, 
            # though forward slashes work in most modern contexts.
            lines.append(f"    path: \"{asset.get('path')}\"")
            if "width" in asset:
                lines.append(f"    width: {asset['width']}")
            if "height" in asset:
                lines.append(f"    height: {asset['height']}")
        lines.append("")

    # Compositions
    if "compositions" in data:
        lines.append("compositions:")
        for comp in data["compositions"]:
            lines.append(f"  - name: \"{comp.get('name', 'Comp')}\"")
            lines.append(f"    width: {comp.get('width', 1920)}")
            lines.append(f"    height: {comp.get('height', 1080)}")
            lines.append(f"    frameRate: {comp.get('frameRate', 24)}")
            lines.append(f"    duration: {comp.get('duration', 10)}")
            
            if "markers" in comp:
                lines.append("    markers:")
                for m in comp["markers"]:
                    lines.append(f"      - {{ name: \"{m['name']}\", time: {m['time']} }}")

            if "layers" in comp:
                lines.append("    layers:")
                for layer in comp["layers"]:
                    lines.append(f"      - name: \"{layer.get('name', 'Layer')}\"")
                    lines.append(f"        type: \"{layer.get('type', 'Null')}\"")
                    
                    # Asset ID / Ref ID
                    if "assetId" in layer:
                        lines.append(f"        assetId: \"{layer['assetId']}\"")
                    if "refId" in layer:
                        lines.append(f"        refId: \"{layer['refId']}\"")

                    if "sourceText" in layer:
                        lines.append(f"        sourceText: \"{layer['sourceText']}\"")
                    
                    lines.append(f"        inPoint: {layer.get('inPoint', 0)}")
                    lines.append(f"        outPoint: {layer.get('outPoint', 1)}")
                    lines.append(f"        startTime: {layer.get('startTime', 0)}")
                    
                    # Attributes
                    if "attributes" in layer and layer["attributes"]:
                        attrs = []
                        for k, v in layer["attributes"].items():
                            attrs.append(f"{k}: {format_value(v)}")
                        lines.append(f"        attributes: {{ {', '.join(attrs)} }}")

                    # Properties (Transform, etc.)
                    if "properties" in layer:
                        lines.append("        properties:")
                        for prop_group_name, prop_group_data in layer["properties"].items():
                            # Flatten Transform group
                            if prop_group_name == "Transform" and isinstance(prop_group_data, dict):
                                for p_key, p_val in prop_group_data.items():
                                    # Use dot notation: "Transform.Opacity"
                                    # We need to pass the full key to write_property, but write_property handles indentation.
                                    # We can manually construct the line here for the top-level flattened keys.
                                    flat_key = f"\"{prop_group_name}.{p_key}\""
                                    write_property(flat_key, p_val, 5, lines) # Level 5 indentation (10 spaces)
                            else:
                                # Normal handling for other groups or direct properties
                                if isinstance(prop_group_data, dict):
                                    lines.append(f"          {prop_group_name}:")
                                    for p_key, p_val in prop_group_data.items():
                                        write_property(p_key, p_val, 6, lines)

                    # Effects
                    if "effects" in layer:
                        lines.append("        effects:")
                        # Handle effects list (if it's a list in JSON) or dict (if exporter output)
                        # The exporter outputs a dict: { "Effect Name": { ... } }
                        # We convert this to a list for AIGEN.
                        if isinstance(layer["effects"], dict):
                            for eff_name, eff_data in layer["effects"].items():
                                 lines.append(f"          - type: \"{eff_name}\"")
                                 if "matchName" in eff_data:
                                     lines.append(f"            matchName: \"{eff_data['matchName']}\"")
                                 if "properties" in eff_data:
                                     lines.append("            properties:")
                                     for p_key, p_val in eff_data["properties"].items():
                                         write_property(p_key, p_val, 7, lines)
                        elif isinstance(layer["effects"], list):
                            # If it's already a list (rare with current exporter but possible)
                            for eff in layer["effects"]:
                                lines.append(f"          - type: \"{eff.get('type', 'Effect')}\"")
                                if "matchName" in eff:
                                    lines.append(f"            matchName: \"{eff['matchName']}\"")
                                if "properties" in eff:
                                    lines.append("            properties:")
                                    # Check if properties is dict or list
                                    if isinstance(eff["properties"], dict):
                                        for p_key, p_val in eff["properties"].items():
                                            write_property(p_key, p_val, 7, lines)
                                    elif isinstance(eff["properties"], list):
                                         for p in eff["properties"]:
                                             # Complex handling if properties are list of dicts with index/value_data
                                             pass 

                    # Text Animators
                    if "textAnimators" in layer:
                        lines.append("        textAnimators:")
                        for anim in layer["textAnimators"]:
                            lines.append(f"          - name: \"{anim.get('name', 'Animator')}\"")
                            
                            # Animator Properties
                            if "animatorProperties" in anim:
                                lines.append("            animatorProperties:")
                                for ap in anim["animatorProperties"]:
                                    lines.append(f"              - property: \"{ap['property']}\"")
                                    lines.append("                value_data:")
                                    vd = ap['value_data']
                                    if "animated" in vd and vd["animated"]:
                                        lines.append("                  animated: true")
                                        if "keyframes" in vd:
                                            lines.append("                  keyframes:")
                                            for kf in vd["keyframes"]:
                                                kf_str = ", ".join([f"{k}: {format_value(v)}" for k, v in kf.items()])
                                                lines.append(f"                    - {{ {kf_str} }}")
                                    else:
                                        lines.append(f"                  value: {format_value(vd.get('value'))}")

                            # Selectors
                            if "selectors" in anim:
                                lines.append("            selectors:")
                                for sel in anim["selectors"]:
                                    lines.append(f"              - name: \"{sel.get('name', 'Selector')}\"")
                                    if "properties" in sel:
                                        lines.append("                properties:")
                                        for p_key, p_val in sel["properties"].items():
                                            write_property(p_key, p_val, 9, lines)

            lines.append("") # Spacer between comps

    # Write output
    output_path = json_path.replace(".json", ".aigen")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        print(f"Successfully converted to: {output_path}")
    except Exception as e:
        print(f"Error writing AIGEN file: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_to_aigen.py <input_json_file>")
        # Default for testing if no arg provided
        default_file = r"e:\Python\json-exported-from-AfterEffects.json"
        if os.path.exists(default_file):
            print(f"No argument provided. Using default: {default_file}")
            convert_json_to_aigen(default_file)
        else:
            print("Default file not found.")
    else:
        convert_json_to_aigen(sys.argv[1])
