"""Checks the patched game data against the real files from your install.

    python test_build.py
"""
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import build_mod as b


def grenade_blocks(text: str) -> dict[str, str]:
    lines = text.split("\r\n")
    blocks = {}
    for name in b.GRENADES:
        start = lines.index(f"   {name}   =   {{")
        end = lines.index("   }", start)
        blocks[name] = "\r\n".join(lines[start:end + 1])
    return blocks


def check_load_order() -> list[str]:
    """Earlier pak_config.yaml entries win, so a build on top of Overhaul must be listed above it."""
    config = ("- pak: other.pak\n  disabled: false\n"
              "- pak: wa_astartes_15_2.pak\n  disabled: false\n"
              "- pak: later.pak\n  disabled: false\n")
    order = lambda mods: re.findall(r"- pak: (\S+)", (mods / "pak_config.yaml").read_text())
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        mods = Path(tmp)
        (mods / "pak_config.yaml").write_text(config)
        b.set_installed(mods, [b.PAK_RESERVE, b.PAK_GRENADES], above="wa_astartes_15_2.pak")
        got = order(mods)
        if got != ["other.pak", b.PAK_RESERVE, b.PAK_GRENADES, "wa_astartes_15_2.pak", "later.pak"]:
            failures.append(f"build on Overhaul not listed above it: {got}")
        # Reinstalling must move existing entries, not duplicate them.
        b.set_installed(mods, [b.PAK_RESERVE], above="wa_astartes_15_2.pak")
        if order(mods).count(b.PAK_RESERVE) != 1 or b.PAK_GRENADES in order(mods):
            failures.append(f"reinstall left stale entries: {order(mods)}")
        (mods / "pak_config.yaml").write_text(config)
        b.set_installed(mods, [b.PAK_RESERVE])
        if order(mods)[-1] != b.PAK_RESERVE:
            failures.append(f"vanilla build not listed last: {order(mods)}")
    return failures


def check_weapon_patches(game: Path) -> list[str]:
    """Heat is gone and the launcher has a reserve, in the game's own data."""
    failures = []
    source = game / "client_pc" / "root" / "paks" / "client" / "default" / "default_other.pak"
    with zipfile.ZipFile(source) as z:
        for name in b.AMMO_FILES:
            text = z.read(name).decode("utf-8")
            patched, _ = b.patch_launcher_ammo(b.patch_overheat(text)[0])
            lines = patched.split("\r\n")
            if len(lines) < len(text.split("\r\n")):
                failures.append(f"{name}: lines were lost")
            for i, line in enumerate(lines):
                if re.match(r"\s*value   =   [^0\s]", line) and '"HeatPercentPerShot"' in lines[i + 1]:
                    failures.append(f"{name}:{i + 1}: still builds heat per shot")
                if re.search(r"continuousHeatingSpeed   =   [1-9]|(OverheatAffectingShooting|ForbiddenWhileOverheated)   =   True", line):
                    failures.append(f"{name}:{i + 1}: heat still matters: {line.strip()}")
                if b.LAUNCHER_POOL.match(line) and lines[i + 1].strip() != "maxAmount   =   999":
                    failures.append(f"{name}:{i + 1}: launcher reserve not set")
    return failures


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

    failures += check_load_order()
    failures += check_weapon_patches(game)

    for f in failures:
        print("FAIL", f)
    print("all checks passed" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
