"""Checks the patched game data against the real files from your install.

    python test_build.py
"""
import re
import sys
import zipfile

import build_mod as b


def grenade_blocks(text: str) -> dict[str, str]:
    lines = text.split("\r\n")
    blocks = {}
    for name in b.GRENADES:
        start = lines.index(f"   {name}   =   {{")
        end = lines.index("   }", start)
        blocks[name] = "\r\n".join(lines[start:end + 1])
    return blocks


def main() -> int:
    game = b.find_game()
    source = game / "client_pc" / "root" / "paks" / "client" / "default" / "default_other.pak"
    with zipfile.ZipFile(source) as z:
        original = z.read(b.ABILITY_FILE).decode("utf-8")
    patched = b.patch_grenades(original)
    failures = []

    for name, block in grenade_blocks(patched).items():
        orig_block = grenade_blocks(original)[name]
        # Pickup visuals spawn one model per charge, so charges must stay a small finite pool.
        if "AbilityResourceInfiniteDesc" in block:
            failures.append(f"{name}: uses the infinite resource (crashes pickup visuals)")
        if '"CHARGES"' not in block:
            failures.append(f"{name}: no longer charge-based")
        for key in ("maxCharges", "startingCharges"):
            if re.findall(rf"{key}   =   \d+", block) != re.findall(rf"{key}   =   \d+", orig_block):
                failures.append(f"{name}: {key} changed")
        if '"EnergyTimerRegen"' not in block:
            failures.append(f"{name}: no timer refill")
        if '"EnergyCraftPointsSimpleRegen"' not in block:
            failures.append(f"{name}: lost ammo-crate refill")
        if block.count("{") != block.count("}"):
            failures.append(f"{name}: unbalanced braces")

    # Nothing outside the grenade blocks may change.
    strip = lambda t: [l for l in t.split("\r\n")]
    outside_orig = original
    outside_new = patched
    for name in b.GRENADES:
        outside_orig = outside_orig.replace(grenade_blocks(original)[name], "")
        outside_new = outside_new.replace(grenade_blocks(patched)[name], "")
    if strip(outside_orig) != strip(outside_new):
        failures.append("lines outside the grenade blocks changed")

    for f in failures:
        print("FAIL", f)
    print("all checks passed" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
