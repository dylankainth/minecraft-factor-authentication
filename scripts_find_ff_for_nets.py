import json
import gzip
import sys

artifacts_dir = sys.argv[1]
target_nets = {int(x) for x in sys.argv[2:]}

nl = json.load(gzip.open(f"{artifacts_dir}/netlist.json.gz"))
mod = list(nl["modules"].values())[0]
cells = mod["cells"]

for name, cell in cells.items():
    if cell.get("type") != "$_DFFE_PP_":
        continue
    conns = cell.get("connections", {})
    q = conns.get("Q", [])
    for net in q:
        if isinstance(net, int) and net in target_nets:
            print(net, name)
