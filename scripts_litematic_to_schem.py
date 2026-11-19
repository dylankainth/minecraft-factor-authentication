"""Converts a MineRTL-produced .litematic (Litematica format) into the Sponge
Schematic v2 format this project's schem.py writes, which MCHPRS's //load
actually reads. MCHPRS has no native .litematic loader. Merges every region
in the source file into one combined schematic, placing each region at its
own (x,y,z) offset within the structure.

Run with the MineRTL venv's python (has litemapy + nbtlib):
    MineRTL/.venv/bin/python scripts_litematic_to_schem.py <in.litematic> <out.schem>
"""
import json
import sys

import litemapy
import schem


def convert(in_path, out_path, we_offset=None):
    """Litematica regions are independent boxes meant to be pasted in order,
    a later region overwriting an earlier one at any overlapping position --
    that's by design (e.g. a built-in clock laid over part of the main
    layout), not a circuit bug, so overlaps here are resolved last-wins
    rather than treated as the real collisions schem.Schematic.set() guards
    against."""
    src = litemapy.Schematic.load(in_path)
    merged = {}
    for name, region in src.regions.items():
        rx, ry, rz = region.x, region.y, region.z
        for (lx, ly, lz) in region.block_positions():
            b = region[lx, ly, lz]
            if b.id == "minecraft:air":
                continue
            props = dict(b.properties())
            if b.id == "minecraft:redstone_wire":
                # `power` is a derived/runtime value MCHPRS recomputes on the
                # next live transition anyway; dropping it collapses the
                # combinatorial explosion of (connections x power 0-15)
                # variants in the palette (643 -> 140 distinct block strings
                # for the TOTP core), staying under the 256-entry threshold
                # where MCHPRS's PalettedBitBuffer switches its clipboard
                # storage mode (crates/world/src/storage.rs resize_buffer) --
                # a transition that appears to silently corrupt very large
                # pastes in this MCHPRS build.
                props.pop("power", None)
            if props:
                prop_str = ",".join(f"{k}={v}" for k, v in props.items())
                block_str = f"{b.id}[{prop_str}]"
            else:
                block_str = b.id
            merged[(rx + lx, ry + ly, rz + lz)] = block_str

    out = schem.Schematic()
    out.blocks = merged

    xs = [p[0] for p in out.blocks]
    ys = [p[1] for p in out.blocks]
    zs = [p[2] for p in out.blocks]
    minx, miny, minz = min(xs), min(ys), min(zs)

    if we_offset is None:
        we_offset = ((max(xs) - minx) // 2, (max(ys) - miny) // 2, (max(zs) - minz) // 2)
    out.save(out_path, we_offset=we_offset)

    # schem.Schematic.save() normalizes to the tight bounding box of actual
    # non-air blocks, so a pin/port coordinate captured in the original
    # (region-relative) frame -- e.g. from MineRTL's build_with_pins.py --
    # is off by (minx, miny, minz) once pasted from this file. Record the
    # shift so callers can correct for it: world_pos = ANCHOR + local -
    # shift, i.e. use ANCHOR.offset(-shift...) as the effective anchor.
    shift = {"shift_x": minx, "shift_y": miny, "shift_z": minz}
    shift_path = out_path + ".shift.json"
    with open(shift_path, "w") as f:
        json.dump(shift, f)
    print(f"wrote {out_path}: {len(out.blocks)} non-air blocks, we_offset={we_offset}, "
          f"shift={shift} (written to {shift_path})")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
