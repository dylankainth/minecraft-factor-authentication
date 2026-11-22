import sys
import litemapy

path = sys.argv[1]
schem = litemapy.Schematic.load(path)
for name, region in schem.regions.items():
    rx, ry, rz = region.x, region.y, region.z
    for x in range(region.width if region.width > 0 else -region.width):
        for y in range(region.height if region.height > 0 else -region.height):
            for z in range(region.length if region.length > 0 else -region.length):
                b = region[x, y, z]
                bid = b.id
                if bid in ("minecraft:lever", "minecraft:redstone_lamp"):
                    wx = rx + (x if region.width > 0 else -x)
                    wy = ry + (y if region.height > 0 else -y)
                    wz = rz + (z if region.length > 0 else -z)
                    try:
                        props = b.properties()
                    except Exception:
                        props = {}
                    print(bid, wx, wy, wz, props)
