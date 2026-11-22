import json
import gzip
import sys

artifacts_dir = sys.argv[1]
targets_file = sys.argv[2]
targets = [line.strip() for line in open(targets_file) if line.strip()]

layout = json.load(gzip.open(f"{artifacts_dir}/component_layout.json.gz"))
by_id = {c["id"]: c for c in layout}
for t in targets:
    c = by_id.get(t)
    if c is None:
        print(f"MISSING: {t}")
        continue
    q = [p for p in c["pins"] if p["name"] == "Q"][0]
    origin = c["origin"]
    off = q["offset"]
    world = [origin[i] + off[i] for i in range(3)]
    print(f"{t} type={c['type']} origin={origin} Q_offset={off} world={world}")
