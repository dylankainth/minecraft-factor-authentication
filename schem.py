"""Minimal Sponge Schematic v2 writer, matching MCHPRS's loader
(mchprs/crates/schematic/src/lib.rs) exactly:
  - Width/Height/Length as shorts
  - Palette: compound of "block_name[props]" -> palette index (int)
  - BlockData: varint-encoded palette indices, iterated y-outer, z-mid, x-inner
  - Metadata.WEOffsetX/Y/Z ints (we always anchor at the schematic's own
    corner, so these are 0)
  - root tag named "Schematic", version=2, gzip-compressed NBT
"""
from nbtlib import File, Compound, Int, Short, ByteArray, List


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


class Schematic:
    """blocks: dict[(x,y,z)] -> block string, e.g. "minecraft:lever[face=floor]".
    Unlisted positions within the bounding box default to "minecraft:air"."""

    def __init__(self):
        self.blocks = {}

    def set(self, x, y, z, block_str):
        key = (x, y, z)
        existing = self.blocks.get(key)
        if existing is not None and existing != block_str:
            raise ValueError(
                f"collision at {key}: tried to place {block_str!r} but "
                f"{existing!r} is already there (two parts of the circuit "
                f"overlap -- check the layout)"
            )
        self.blocks[key] = block_str

    def save(self, path, data_version=3700, we_offset=(0, 0, 0)):
        """we_offset: WEOffsetX/Y/Z, the WorldEdit clipboard "handle" --
        the local point (relative to the structure's own min corner)
        that lands exactly on the player's position at paste time.
        Confirmed from mchprs/crates/schematic/src/lib.rs: the loader
        negates WEOffset into cb.offset_x, and execute_paste computes
        world_offset = player_pos + WEOffset, so passing (0,0,0) (the
        default) anchors on the structure's corner -- pass the
        structure's own center here instead to roughly halve the
        worst-case distance from the player's paste position to any
        block, which 2026-11-18's investigation suggests matters for
        live-read reliability on larger builds."""
        if not self.blocks:
            raise ValueError("no blocks set")
        xs = [p[0] for p in self.blocks]
        ys = [p[1] for p in self.blocks]
        zs = [p[2] for p in self.blocks]
        minx, miny, minz = min(xs), min(ys), min(zs)
        size_x = max(xs) - minx + 1
        size_y = max(ys) - miny + 1
        size_z = max(zs) - minz + 1

        palette = {"minecraft:air": 0}
        data = bytearray()
        for y in range(size_y):
            for z in range(size_z):
                for x in range(size_x):
                    name = self.blocks.get((x + minx, y + miny, z + minz), "minecraft:air")
                    if name not in palette:
                        palette[name] = len(palette)
                    data += _varint(palette[name])

        nbt_palette = Compound({name: Int(idx) for name, idx in palette.items()})

        root = Compound({
            "Width": Short(size_x),
            "Length": Short(size_z),
            "Height": Short(size_y),
            "Palette": nbt_palette,
            "BlockData": ByteArray(list((b if b < 128 else b - 256) for b in data)),
            "BlockEntities": List[Compound]([]),
            "Metadata": Compound({
                "WEOffsetX": Int(we_offset[0]),
                "WEOffsetY": Int(we_offset[1]),
                "WEOffsetZ": Int(we_offset[2]),
            }),
            "Version": Int(2),
            "DataVersion": Int(data_version),
        })

        nbt_file = File(root, gzipped=True, root_name="Schematic")
        nbt_file.save(path)
