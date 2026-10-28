"""Package Unlimited Ammo for Nexus Mods.

    python release.py

Builds the paks from your installed game, then writes to dist/:
    UnlimitedAmmo-<version>.zip          main file (FOMOD installer + manual folders)
    UnlimitedAmmo-Patcher-<version>.zip  optional file (rebuild after a game patch)
    nexus_description.txt                page text to paste into Nexus (BBCode)

Bump VERSION for every upload.
"""
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import build_mod as b

VERSION = "1.1.0"
GAME_VERSION = "15.2"  # game patch this release was tested on
AUTHOR = "QuietOrbit"  # Nexus username
MOD_NAME = "Unlimited Ammo"
NEXUS_URL = "https://www.nexusmods.com/warhammer40000spacemarine2/mods/626"

TEMPLATES = b.HERE / "release"

# (folder in the zip, pak, option name, option description)
AMMO_OPTIONS = [
    ("1 - Unlimited Reserve", b.PAK_RESERVE, "Unlimited Reserve",
     "Your reserve ammo never runs out. You still reload."),
    ("2 - No Reload", b.PAK_NO_RELOAD, "No Reload",
     "Bottomless magazines. You never reload."),
]
GRENADE_OPTION = ("3 - Unlimited Grenades", b.PAK_GRENADES, "Unlimited Grenades",
                  "Frag, krak and shock grenades never run out.")


def plugin(name: str, desc: str, folder: str | None, pak: str | None, default: str) -> str:
    files = (f'<files><file source="{escape(folder)}\\{pak}" destination="{pak}" priority="0"/></files>'
             if pak else "")
    return f"""
          <plugin name="{escape(name)}">
            <description>{escape(desc)}</description>
            {files}
            <typeDescriptor><type name="{default}"/></typeDescriptor>
          </plugin>"""


def module_config() -> str:
    ammo = "".join(plugin(name, desc, folder, pak, "Recommended" if i == 0 else "Optional")
                   for i, (folder, pak, name, desc) in enumerate(AMMO_OPTIONS))
    ammo += plugin("Off", "No ammo changes. Use this if you only want unlimited grenades.", None, None, "Optional")
    folder, pak, name, desc = GRENADE_OPTION
    extras = plugin(name, desc, folder, pak, "Optional")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="http://qconsulting.ca/fo3/ModConfig5.0.xsd">
  <moduleName>{escape(MOD_NAME)}</moduleName>
  <installSteps order="Explicit">
    <installStep name="Options">
      <optionalFileGroups order="Explicit">
        <group name="Ammo mode" type="SelectExactlyOne">
          <plugins order="Explicit">{ammo}
          </plugins>
        </group>
        <group name="Extras" type="SelectAny">
          <plugins order="Explicit">{extras}
          </plugins>
        </group>
      </optionalFileGroups>
    </installStep>
  </installSteps>
</config>
"""


def info_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<fomod>
  <Name>{escape(MOD_NAME)}</Name>
  <Author>{escape(AUTHOR)}</Author>
  <Version>{VERSION}</Version>
  <Website>{escape(NEXUS_URL)}</Website>
  <Description>Unlimited ammo, no-reload, and unlimited grenade options. Works on game patch {GAME_VERSION}.</Description>
</fomod>
"""


def fill(template: str) -> str:
    author_line = f"by {AUTHOR}\n" if AUTHOR else ""
    return (template.replace("{version}", VERSION).replace("{game_version}", GAME_VERSION)
            .replace("{author_line}", author_line))


def main() -> int:
    game = b.find_game()
    if game is None:
        print("Couldn't find Space Marine 2 through Steam.")
        return 1
    b.build(game / "client_pc" / "root" / "paks" / "client" / "default" / "default_other.pak")

    readme = fill((TEMPLATES / "README.txt").read_text(encoding="utf-8")).replace("\n", "\r\n")

    main_zip = b.DIST / f"UnlimitedAmmo-{VERSION}.zip"
    with zipfile.ZipFile(main_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("fomod/info.xml", info_xml())
        z.writestr("fomod/ModuleConfig.xml", module_config())
        for folder, pak, _, _ in AMMO_OPTIONS + [GRENADE_OPTION]:
            z.write(b.DIST / pak, f"{folder}/{pak}")
        z.writestr("README.txt", readme)
    print(f"wrote {main_zip}")

    patcher_zip = b.DIST / f"UnlimitedAmmo-Patcher-{VERSION}.zip"
    with zipfile.ZipFile(patcher_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(b.HERE / "build_mod.py", "UnlimitedAmmo-Patcher/build_mod.py")
        bat = (TEMPLATES / "Run_Patcher.bat").read_text(encoding="utf-8").replace("\r\n", "\n").replace("\n", "\r\n")
        z.writestr("UnlimitedAmmo-Patcher/Run_Patcher.bat", bat)
        z.writestr("UnlimitedAmmo-Patcher/README.txt", readme)
    print(f"wrote {patcher_zip}")

    desc = b.DIST / "nexus_description.txt"
    desc.write_text(fill((TEMPLATES / "nexus_description.txt").read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {desc}")
    if not AUTHOR:
        print("note: AUTHOR is blank in release.py - set it to your Nexus username before uploading")
    return 0


if __name__ == "__main__":
    sys.exit(main())
