import json

with open('effects_manifest.json', 'r', encoding='utf-8') as f:
    manifest = json.load(f)

if 'Transform' in manifest:
    for group in manifest['Transform']['groups']:
        print(f"Group: {group.get('name')}")
        for prop_name in group.get('properties', {}):
            print(f"  - {prop_name}")
else:
    print("Transform not found")
