import json
import gzip
import sys

artifacts_dir = sys.argv[1]
targets_file = sys.argv[2]
pin_name = sys.argv[3]
targets = [line.strip() for line in open(targets_file) if line.strip()]

layout = json.load(gzip.open(f"{artifacts_dir}/component_layout.json.gz"))
by_id = {c["id"]: c for c in layout}
for t in targets:
    c = by_id.get(t)
    if c is None:
        print(f"MISSING: {t}")
        continue
    matches = [p for p in c["pins"] if p["name"] == pin_name]
    if not matches:
        print(f"{t} type={c['type']} has no pin named {pin_name}; pins={[p['name'] for p in c['pins']]}")
        continue
    p = matches[0]
    origin = c["origin"]
    off = p["offset"]
    world = [origin[i] + off[i] for i in range(3)]
    print(f"{t} type={c['type']} origin={origin} {pin_name}_offset={off} world={world}")
