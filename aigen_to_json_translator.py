# aigen_to_json_translator.py
#
# Description: Advanced AIGEN v3.1 Translator.
# NOW OFFLINE: Reads 'effects_manifest.json' locally.
# FEATURES: Auto-fixes PNG images using Pillow.
#

import yaml
import json
import sys
import re
import os
from collections.abc import MutableMapping
from PIL import Image  # Added for image fixing

# નામ ફિક્સ કર્યું છે - આ ફાઈલ સ્ક્રિપ્ટની બાજુમાં જ હોવી જોઈએ
MANIFEST_FILENAME = "effects_manifest.json"

def deep_merge(d1, d2):
    """Recursively merges dictionary d2 into d1."""
    for k, v in d2.items():
        if k in d1 and isinstance(d1[k], dict) and isinstance(v, MutableMapping):
            deep_merge(d1[k], v)
        else:
            d1[k] = v
    return d1

def get_from_dict(data_dict, map_list):
    for k in map_list:
        data_dict = data_dict[k]
    return data_dict

def resolve_globals(data_node, globals_map):
    if isinstance(data_node, dict):
        return {k: resolve_globals(v, globals_map) for k, v in data_node.items()}
    elif isinstance(data_node, list):
        return [resolve_globals(item, globals_map) for item in data_node]
    elif isinstance(data_node, str):
        match = re.match(r'^\$globals\.([\w\.]+)', data_node)
        if match:
            try:
                keys = match.group(1).split('.')
                return get_from_dict(globals_map, keys)
            except (KeyError, TypeError):
                print(f"Warning: Global variable '{data_node}' not found.", file=sys.stderr)
                return data_node
    return data_node

def load_local_manifest(filename):
    """Loads the effects manifest from a local file."""
    if not os.path.exists(filename):
        print(f"CRITICAL ERROR: '{filename}' not found in the script directory.", file=sys.stderr)
        print("Please create this JSON file manually.", file=sys.stderr)
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            print(f"Loaded local effects manifest: {filename}")
            return json.load(f)
    except Exception as e:
        print(f"Error reading manifest file: {e}", file=sys.stderr)
        return None

def translate_effect(effect_data, manifest):
    user_effect_name = effect_data.get('type')
    # Fallback: If effect not in manifest, assume the user gave the exact MatchName
    if not user_effect_name: return None
    
    if user_effect_name not in manifest:
        # SMART LOGIC: If not found in manifest, use the name as is.
        # This allows advanced users to use MatchNames directly in YAML.
        return {
            "matchName": user_effect_name,
            "name": effect_data.get('name', user_effect_name),
            "properties": [] # Cannot map properties without manifest, assumes defaults or explicit matchnames
        }

    effect_info = manifest[user_effect_name]
    translated_effect = {
        "matchName": effect_info["matchName"],
        "name": effect_data.get('name', user_effect_name),
        "properties": []
    }
    if 'properties' in effect_data:
        for user_prop_name, prop_value in effect_data['properties'].items():
            prop_found = False
            for group in effect_info.get("groups", []):
                if user_prop_name in group.get("properties", {}):
                    prop_details = group["properties"][user_prop_name]
                    translated_effect["properties"].append({
                        "index": prop_details["index"],
                        "value_data": prop_value
                    })
                    prop_found = True
                    break
    return translated_effect

def fix_image(image_path):
    """
    Reads an image, converts it to RGBA, and saves it as a new PNG 
    in a 'changed' directory to ensure compatibility.
    """
    try:
        # Create 'changed' directory if it doesn't exist
        script_dir = os.path.dirname(os.path.abspath(__file__))
        changed_dir = os.path.join(script_dir, "changed")
        if not os.path.exists(changed_dir):
            os.makedirs(changed_dir)

        # Open and process image
        with Image.open(image_path) as img:
            # Convert to RGBA to ensure transparency is handled correctly and format is standard
            img = img.convert("RGBA")
            
            # Generate new filename
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_fixed.png"
            new_path = os.path.join(changed_dir, new_filename)
            
            # Save the fixed image
            img.save(new_path, "PNG")
            print(f"  [Auto-Fix] Image saved to: {new_path}")
            
            # Return the absolute path using backslashes for Windows/AE compatibility
            return os.path.abspath(new_path).replace(os.sep, '\\')
            
    except Exception as e:
        print(f"  [Auto-Fix Error] Could not process {image_path}: {e}")
        return image_path # Return original if failure

def main(input_path, output_path):
    print("--- Starting AIGEN v3.1 Translation (Offline Mode) ---")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            aigen_data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading AIGEN file: {e}", file=sys.stderr)
        sys.exit(1)

    # Resolve Globals
    globals_map = aigen_data.get("globals", {})
    if globals_map:
        aigen_data = resolve_globals(aigen_data, globals_map)

    # Merge Components
    components_map = {comp['id']: comp for comp in aigen_data.get("components", [])}
    if components_map:
        for comp_data in aigen_data.get("compositions", []):
            for layer_data in comp_data.get("layers", []):
                if "useComponents" in layer_data:
                    merged_properties = {}
                    for comp_id in layer_data["useComponents"]:
                        if comp_id in components_map:
                            comp_props = json.loads(json.dumps(components_map[comp_id].get("properties", {})))
                            deep_merge(merged_properties, comp_props)
                    layer_props = layer_data.get("properties", {})
                    deep_merge(merged_properties, layer_props)
                    layer_data["properties"] = merged_properties
                    del layer_data["useComponents"]

    # Load Manifest Locally
    effects_manifest = load_local_manifest(MANIFEST_FILENAME)
    if not effects_manifest:
        # If manifest fails, we create an empty one so script doesn't crash,
        # but effects translation relies on direct matchnames.
        effects_manifest = {}

    # Build Blueprint
# aigen_to_json_translator.py
#
# Description: Advanced AIGEN v3.1 Translator.
# NOW OFFLINE: Reads 'effects_manifest.json' locally.
# FEATURES: Auto-fixes PNG images using Pillow.
#

import yaml
import json
import sys
import re
import os
from collections.abc import MutableMapping
from PIL import Image  # Added for image fixing

# નામ ફિક્સ કર્યું છે - આ ફાઈલ સ્ક્રિપ્ટની બાજુમાં જ હોવી જોઈએ
MANIFEST_FILENAME = "effects_manifest.json"

def deep_merge(d1, d2):
    """Recursively merges dictionary d2 into d1."""
    for k, v in d2.items():
        if k in d1 and isinstance(d1[k], dict) and isinstance(v, MutableMapping):
            deep_merge(d1[k], v)
        else:
            d1[k] = v
    return d1

def get_from_dict(data_dict, map_list):
    for k in map_list:
        data_dict = data_dict[k]
    return data_dict

def resolve_globals(data_node, globals_map):
    if isinstance(data_node, dict):
        return {k: resolve_globals(v, globals_map) for k, v in data_node.items()}
    elif isinstance(data_node, list):
        return [resolve_globals(item, globals_map) for item in data_node]
    elif isinstance(data_node, str):
        match = re.match(r'^\$globals\.([\w\.]+)', data_node)
        if match:
            try:
                keys = match.group(1).split('.')
                return get_from_dict(globals_map, keys)
            except (KeyError, TypeError):
                print(f"Warning: Global variable '{data_node}' not found.", file=sys.stderr)
                return data_node
    return data_node

def load_local_manifest(filename):
    """Loads the effects manifest from a local file."""
    if not os.path.exists(filename):
        print(f"CRITICAL ERROR: '{filename}' not found in the script directory.", file=sys.stderr)
        print("Please create this JSON file manually.", file=sys.stderr)
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            print(f"Loaded local effects manifest: {filename}")
            return json.load(f)
    except Exception as e:
        print(f"Error reading manifest file: {e}", file=sys.stderr)
        return None

def translate_effect(effect_data, manifest):
    user_effect_name = effect_data.get('type')
    # Fallback: If effect not in manifest, assume the user gave the exact MatchName
    if not user_effect_name: return None
    
    if user_effect_name not in manifest:
        # SMART LOGIC: If not found in manifest, use the name as is.
        # This allows advanced users to use MatchNames directly in YAML.
        return {
            "matchName": user_effect_name,
            "name": effect_data.get('name', user_effect_name),
            "properties": [] # Cannot map properties without manifest, assumes defaults or explicit matchnames
        }

    effect_info = manifest[user_effect_name]
    translated_effect = {
        "matchName": effect_info["matchName"],
        "name": effect_data.get('name', user_effect_name),
        "properties": []
    }
    if 'properties' in effect_data:
        for user_prop_name, prop_value in effect_data['properties'].items():
            prop_found = False
            for group in effect_info.get("groups", []):
                if user_prop_name in group.get("properties", {}):
                    prop_details = group["properties"][user_prop_name]
                    translated_effect["properties"].append({
                        "index": prop_details["index"],
                        "value_data": prop_value
                    })
                    prop_found = True
                    break
    return translated_effect

def fix_image(image_path):
    """
    Reads an image, converts it to RGBA, and saves it as a new PNG 
    in a 'changed' directory to ensure compatibility.
    """
    try:
        # Create 'changed' directory if it doesn't exist
        script_dir = os.path.dirname(os.path.abspath(__file__))
        changed_dir = os.path.join(script_dir, "changed")
        if not os.path.exists(changed_dir):
            os.makedirs(changed_dir)

        # Open and process image
        with Image.open(image_path) as img:
            # Convert to RGBA to ensure transparency is handled correctly and format is standard
            img = img.convert("RGBA")
            
            # Generate new filename
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_fixed.png"
            new_path = os.path.join(changed_dir, new_filename)
            
            # Save the fixed image
            img.save(new_path, "PNG")
            print(f"  [Auto-Fix] Image saved to: {new_path}")
            
            # Return the absolute path using backslashes for Windows/AE compatibility
            return os.path.abspath(new_path).replace(os.sep, '\\')
            
    except Exception as e:
        print(f"  [Auto-Fix Error] Could not process {image_path}: {e}")
        return image_path # Return original if failure

def main(input_path, output_path):
    print("--- Starting AIGEN v3.1 Translation (Offline Mode) ---")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            aigen_data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading AIGEN file: {e}", file=sys.stderr)
        sys.exit(1)

    # Resolve Globals
    globals_map = aigen_data.get("globals", {})
    if globals_map:
        aigen_data = resolve_globals(aigen_data, globals_map)

    # Merge Components
    components_map = {comp['id']: comp for comp in aigen_data.get("components", [])}
    if components_map:
        for comp_data in aigen_data.get("compositions", []):
            for layer_data in comp_data.get("layers", []):
                if "useComponents" in layer_data:
                    merged_properties = {}
                    for comp_id in layer_data["useComponents"]:
                        if comp_id in components_map:
                            comp_props = json.loads(json.dumps(components_map[comp_id].get("properties", {})))
                            deep_merge(merged_properties, comp_props)
                    layer_props = layer_data.get("properties", {})
                    deep_merge(merged_properties, layer_props)
                    layer_data["properties"] = merged_properties
                    del layer_data["useComponents"]

    # Load Manifest Locally
    effects_manifest = load_local_manifest(MANIFEST_FILENAME)
    if not effects_manifest:
        # If manifest fails, we create an empty one so script doesn't crash,
        # but effects translation relies on direct matchnames.
        effects_manifest = {}

    # Build Blueprint
    blueprint = {
        "projectSettings": aigen_data.get("projectSettings", {}),
        "assets": [], # Will fill this loop below
        "compositions": []
    }

    # Process Assets with Auto-Fix
    if "assets" in aigen_data:
        print("Processing Assets...")
        # Get base directory of the input AIGEN file
        base_dir = os.path.dirname(os.path.abspath(input_path))
        
        for asset in aigen_data["assets"]:
            original_path = asset.get("path", "")
            
            # Resolve relative path
            if not os.path.isabs(original_path):
                full_path = os.path.join(base_dir, original_path)
            else:
                full_path = original_path

            # Check if it's an image that might need fixing
            if original_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                print(f"  Checking image: {full_path}")
                # Attempt to fix/re-save using the full path
                fixed_path = fix_image(full_path)
                asset["path"] = fixed_path
            
            blueprint["assets"].append(asset)

    if "compositions" in aigen_data:
        for comp_data in aigen_data.get("compositions", []):
            translated_comp = comp_data.copy()
            if 'layers' in comp_data:
                layers = [l for l in comp_data['layers'] if isinstance(l, dict)]
                for layer in layers:
                    if 'effects' in layer:
                        translated_effects = [translate_effect(e, effects_manifest) for e in layer['effects']]
                        layer['effects'] = [te for te in translated_effects if te is not None]
                translated_comp['layers'] = layers
            blueprint["compositions"].append(translated_comp)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(blueprint, f, indent=2)
        print(f"Success! Blueprint created: {output_path}")
    except IOError as e:
        print(f"Error writing JSON: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python aigen_to_json_translator.py <input.aigen> <output.json>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])