# Unlimited Ammo — Warhammer 40,000: Space Marine 2

Unlimited reserve ammo, a no-reload mode, and unlimited grenades for Space Marine 2 (PvE only).

**Players:** download the mod from Nexus Mods. This repo is the source that builds it.

I hope it keeps working through future game updates. If an update breaks it, I will post a fixed version as soon as I can.

## What it changes

The paks are built from the installed game's files.

| Option | What it changes |
|---|---|
| Unlimited Reserve | Sets `isInfiniteAmmo = True` on every `ClipSettings` block in `firearm_library_pve.sso` and `firearm_modificators_library.sso` |
| No Reload | Same, plus `isInfiniteClip = True` |
| Unlimited Grenades | Adds an `EnergyTimerRegen` (recoverSpeed 200) to frag, krak, and shock grenades in `ability_library.sso` |

The grenade charges stay a small finite pool on purpose. Grenade pickups spawn one model per charge, so the game's infinite ability resource (2^31-1 charges) crashes on load.

PvP data (`*_pvp.sso`) is never touched.

## Requirements

- Python 3.10+
- Space Marine 2 installed through Steam (or pass `--game "<install folder>"`)

## Usage

```
python build_mod.py                              # build all paks into dist/
python build_mod.py --install reserve --grenades # build and install into the game
python build_mod.py --install no-reload          # bottomless magazines
python build_mod.py --uninstall                  # remove everything this mod installed
python test_build.py                             # check the grenade patch against your game data
python release.py                                # build the Nexus zips and page text into dist/
```

## Releasing after a game patch

1. `python test_build.py`
2. Bump `VERSION` in `release.py`
3. `python release.py`
4. Upload `dist/UnlimitedAmmo-<version>.zip` (main) and `dist/UnlimitedAmmo-Patcher-<version>.zip` (optional) to Nexus, and add a changelog entry.

## Layout

- `build_mod.py`: patches game data and builds or installs the paks. It also ships to players as the Patcher.
- `release.py`: packages the FOMOD installer zip, the Patcher zip, and the Nexus description.
- `release/`: templates for the README, the Nexus page, and `Run_Patcher.bat`.
- `test_build.py`: sanity checks for the grenade patch.
- `tools/`: helpers for listing, searching, and extracting files in game `.pak` archives.
