"""Build the Unlimited Ammo mod for Warhammer 40,000: Space Marine 2.

Reads game data straight from your installed game, so the mod always matches the
current patch. Rerun this after every game update.

    python build_mod.py                                # build all paks into dist/
    python build_mod.py --install reserve              # infinite reserve ammo (you still reload)
    python build_mod.py --install no-reload            # bottomless magazines (never reload)
    python build_mod.py --install reserve --grenades   # ...plus unlimited grenades
    python build_mod.py --install none --grenades      # unlimited grenades only
    python build_mod.py --uninstall                    # remove everything this mod installed

When installing, an enabled Astartes Overhaul in the game's mods folder is detected
and the mod is built on top of its files, keeping Overhaul's changes. Pass --vanilla
to build from the base game anyway. Earlier entries in pak_config.yaml take priority,
so the mod is listed just above Overhaul.

PvP data (firearm_library_pvp.sso, ability_library_pvp.sso) is never touched.
"""
import argparse
import re
from contextlib import nullcontext
import shutil
import sys
import zipfile
from pathlib import Path

STEAM_APP_ID = "2183900"
HERE = Path(__file__).parent
DIST = HERE / "dist"

PAK_RESERVE = "UnlimitedAmmo.pak"
PAK_NO_RELOAD = "UnlimitedAmmo_NoReload.pak"
PAK_GRENADES = "UnlimitedGrenades.pak"
# Every pak name this mod has ever installed, so --install/--uninstall can clean up.
MANAGED_PAKS = [PAK_RESERVE, PAK_NO_RELOAD, PAK_GRENADES, "unlimited_ammo.pak"]

# PvE weapons and the perk variants that replace their clip settings.
AMMO_FILES = [
    "ssl/weapons/creator/firearm_library_pve.sso",
    "ssl/weapons/creator/customization/firearm_modificators_library.sso",
]
ABILITY_FILE = "ssl/abilities/ability_library.sso"
GRENADES = ["equipment_frag_grenade", "equipment_krak_grenade", "equipment_shock_grenade"]

CLIP_TYPE = re.compile(r'^(?P<indent>[ \t]*)__type   =   "ClipSettings"\s*$')
FLAG = re.compile(r'^[ \t]*(isInfiniteAmmo|isInfiniteClip)   =   ')
HEAT_VALUE = re.compile(r"^([ \t]*value   =   )\S+$")
HEATING_SPEED = re.compile(r"^([ \t]*continuousHeatingSpeed   =   )\S+$")
LAUNCHER_POOL = re.compile(r"^(?P<indent>[ \t]*)ammo_grenade(?:_tac_reserve)?   =   \{$")
OVERHEAT_FLAG = re.compile(r"^([ \t]*(?:isOverheatAffectingShooting|isShootingForbiddenWhileOverheated)   =   )True$")


class FormatChanged(Exception):
    """The game's data no longer looks the way this script expects."""


def patch_clip_settings(text: str, no_reload: bool) -> tuple[str, int]:
    """Set infinite-ammo flags on every ClipSettings block. Returns (text, blocks patched)."""
    lines = text.split("\r\n")
    out: list[str] = []
    patched = 0
    for line in lines:
        m = CLIP_TYPE.match(line)
        if not m:
            out.append(line)
            continue
        indent = m.group("indent")
        # The block's body is every preceding line indented at least as deep as __type.
        block_start = len(out)
        while block_start > 0 and out[block_start - 1].startswith(indent):
            block_start -= 1
        # Drop any flags already set directly in this block, then re-add ours.
        existing = {}
        kept = []
        for prev in out[block_start:]:
            fm = FLAG.match(prev)
            if fm and not prev[len(indent)].isspace():
                existing[fm.group(1)] = prev.split("=")[-1].strip()
            else:
                kept.append(prev)
        out[block_start:] = kept
        out.append(f"{indent}isInfiniteAmmo   =   True")
        clip = "True" if no_reload else existing.get("isInfiniteClip", "False")
        out.append(f"{indent}isInfiniteClip   =   {clip}")
        out.append(line)
        patched += 1
    if patched == 0:
        raise FormatChanged("no ClipSettings blocks found")
    return "\r\n".join(out), patched


def patch_overheat(text: str) -> tuple[str, int]:
    """Stop weapons building heat. Returns (text, settings changed).

    Heat per shot and continuous heating go to zero, and the flags that block
    shooting while overheated are cleared as a backstop. Perk modificators only
    add to or scale those numbers, so zero stays zero.
    """
    lines = text.split("\r\n")
    changed = 0
    for i, line in enumerate(lines):
        new = None
        if HEAT_VALUE.match(line) and i + 1 < len(lines) and '"HeatPercentPerShot"' in lines[i + 1]:
            new = HEAT_VALUE.sub(r"\g<1>0", line)
        elif HEATING_SPEED.match(line):
            new = HEATING_SPEED.sub(r"\g<1>0", line)
        elif OVERHEAT_FLAG.match(line):
            new = OVERHEAT_FLAG.sub(r"\g<1>False", line)
        if new is not None and new != line:
            lines[i] = new
            changed += 1
    if changed == 0:
        raise FormatChanged("no overheat settings found")
    return "\r\n".join(lines), changed


def patch_launcher_ammo(text: str) -> tuple[str, int]:
    """Give the underbarrel grenade launcher a real reserve. Returns (text, pools patched).

    The launcher's reserve pools are capped at 0 (or left unset) because the stock
    weapon only ever fires its clip, so the infinite-ammo flag has nothing to refill
    the clip from and a reload comes up empty.
    """
    lines = text.split("\r\n")
    out: list[str] = []
    patched = 0
    for i, line in enumerate(lines):
        out.append(line)
        m = LAUNCHER_POOL.match(line)
        if not m:
            continue
        indent = m.group("indent") + "   "
        if lines[i + 1].startswith(f"{indent}maxAmount   =   "):
            lines[i + 1] = f"{indent}maxAmount   =   999"
        else:
            out.append(f"{indent}maxAmount   =   999")
        patched += 1
    return "\r\n".join(out), patched


def patch_grenades(text: str) -> str:
    """Give each grenade a fast timer refill on top of its normal charges.

    Charges must stay a small finite pool: grenade pickups spawn one visual per
    charge, so the game's infinite ability resource (2^31-1 charges) crashes on load.
    recoverSpeed is energy per second and one charge costs 100, so 200 refills a
    grenade about every half second - the same mechanism the jetpack uses.
    """
    lines = text.split("\r\n")
    for name in GRENADES:
        try:
            start = lines.index(f"   {name}   =   {{")
            end = lines.index("   }", start)
            regen = lines.index("            regenerationRules   =   {", start, end)
            close = lines.index("            }", regen, end)
        except ValueError:
            raise FormatChanged(f"couldn't find the charge refill rules for {name}")
        lines[close:close] = [
            "               TimerRegen   =   {",
            "                  recoverSpeed   =   200",
            "                  ticksPerSec   =   20",
            "                  regenStartingDelay   =   0",
            '                  __type   =   "EnergyTimerRegen"',
            "               }",
        ]
    return "\r\n".join(lines)


def find_game() -> Path | None:
    """Locate the Steam install of Space Marine 2 via the registry and Steam library folders."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            steam = Path(winreg.QueryValueEx(key, "SteamPath")[0])
    except OSError:
        return None
    vdf = steam / "steamapps" / "libraryfolders.vdf"
    libraries = [steam]
    if vdf.exists():
        libraries += [Path(p.replace("\\\\", "\\"))
                      for p in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="replace"))]
    for lib in libraries:
        manifest = lib / "steamapps" / f"appmanifest_{STEAM_APP_ID}.acf"
        if manifest.exists():
            m = re.search(r'"installdir"\s+"([^"]+)"', manifest.read_text(encoding="utf-8", errors="replace"))
            if m and (lib / "steamapps" / "common" / m.group(1)).exists():
                return lib / "steamapps" / "common" / m.group(1)
    return None


def write_pak(path: Path, files: dict[str, bytes]) -> None:
    """Write an uncompressed zip with explicit directory entries, like other SM2 mods."""
    dirs = sorted({"/".join(name.split("/")[:i]) + "/"
                   for name in files for i in range(1, name.count("/") + 1)})
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        for d in dirs:
            z.writestr(zipfile.ZipInfo(d), b"")
        for name, data in files.items():
            z.writestr(zipfile.ZipInfo(name), data)


def build(source_pak: Path, base_pak: Path | None = None) -> None:
    """Build all paks. Files present in base_pak (another mod) are patched instead of the game's."""
    with zipfile.ZipFile(source_pak) as game, \
            (zipfile.ZipFile(base_pak) if base_pak else nullcontext()) as base:
        def read(name: str) -> str:
            z = base if base and name in base.NameToInfo else game
            return z.read(name).decode("utf-8")
        ammo_src = {name: read(name) for name in AMMO_FILES}
        ability_src = read(ABILITY_FILE)

    DIST.mkdir(exist_ok=True)
    for pak, no_reload in ((PAK_RESERVE, False), (PAK_NO_RELOAD, True)):
        files = {}
        for name, text in ammo_src.items():
            patched, count = patch_clip_settings(text, no_reload)
            patched, count = patch_overheat(patched)
            patched, count = patch_launcher_ammo(patched)
            patched, count = patch_launcher_ammo(patched)
            files[name] = patched.encode("utf-8")
        write_pak(DIST / pak, files)
        print(f"built dist/{pak}")
    write_pak(DIST / PAK_GRENADES, {ABILITY_FILE: patch_grenades(ability_src).encode("utf-8")})
    print(f"built dist/{PAK_GRENADES}")


def find_overhaul(mods_dir: Path) -> Path | None:
    """Return the enabled Astartes Overhaul pak in the game's mods folder, if any."""
    cfg = mods_dir / "pak_config.yaml"
    text = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
    enabled = {m.group(1) for m in re.finditer(r"- pak: (\S+)\n  disabled: false", text)}
    for pak in sorted(mods_dir.glob("wa_astartes*.pak")):
        if pak.name in enabled:
            return pak
    return None


def set_installed(mods_dir: Path, paks: list[str], above: str | None = None) -> None:
    """Make exactly `paks` the installed set of this mod's paks, in files and pak_config.yaml.

    Earlier entries in pak_config.yaml take priority, so pass `above` (a pak name) to list
    ours just before the mod they were built on top of. Otherwise they go at the end.
    """
    for name in MANAGED_PAKS:
        if name not in paks:
            (mods_dir / name).unlink(missing_ok=True)
    for name in paks:
        shutil.copy2(DIST / name, mods_dir / name)

    cfg = mods_dir / "pak_config.yaml"
    original = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
    text = original
    for name in MANAGED_PAKS:
        text = re.sub(rf"- pak: {re.escape(name)}\n(  [^\n]*\n)*", "", text)
    if text and not text.endswith("\n"):
        text += "\n"
    entries = "".join(f"- pak: {name}\n  disabled: false\n" for name in paks)
    anchor = re.search(rf"^- pak: {re.escape(above)}\n", text, re.M) if above else None
    if anchor:
        text = text[:anchor.start()] + entries + text[anchor.start():]
    else:
        text += entries
    if text != original:
        if cfg.exists():
            shutil.copy2(cfg, cfg.with_suffix(".yaml.bak"))
        cfg.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", type=Path, help="Space Marine 2 install folder (found via Steam if omitted)")
    ap.add_argument("--install", choices=["reserve", "no-reload", "none"],
                    help="install into the game: ammo mode to use")
    ap.add_argument("--grenades", action="store_true", help="with --install, also install unlimited grenades")
    ap.add_argument("--uninstall", action="store_true", help="remove everything this mod installed")
    ap.add_argument("--vanilla", action="store_true",
                    help="build from the base game even if Astartes Overhaul is installed")
    args = ap.parse_args()

    game = args.game or find_game()
    if game is None:
        print("Couldn't find Space Marine 2 through Steam. Pass --game \"<install folder>\".")
        return 1
    root = game / "client_pc" / "root"
    mods_dir = root / "mods"
    source_pak = root / "paks" / "client" / "default" / "default_other.pak"
    if not source_pak.exists():
        print(f"Can't find game data at {source_pak}. Pass --game <install folder>.")
        return 1

    if args.uninstall:
        if mods_dir.exists():
            set_installed(mods_dir, [])
        print("Unlimited Ammo removed.")
        return 0

    overhaul = None if args.vanilla or not args.install else find_overhaul(mods_dir)
    if overhaul:
        print(f"Astartes Overhaul detected ({overhaul.name}) - building on top of it.")
    try:
        build(source_pak, overhaul)
    except (FormatChanged, KeyError) as e:
        print(f"Build failed - the game's data format may have changed: {e}")
        return 1

    if args.install:
        paks = {"reserve": [PAK_RESERVE], "no-reload": [PAK_NO_RELOAD], "none": []}[args.install]
        if args.grenades:
            paks.append(PAK_GRENADES)
        mods_dir.mkdir(exist_ok=True)
        set_installed(mods_dir, paks, above=overhaul.name if overhaul else None)
        print(f"Installed to {mods_dir}: {', '.join(paks) or 'nothing'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
