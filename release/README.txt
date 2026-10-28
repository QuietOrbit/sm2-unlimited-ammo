UNLIMITED AMMO - Warhammer 40,000: Space Marine 2
Version {version} - works on game patch {game_version}
{author_line}
WHAT IT DOES
------------
Pick one ammo mode, plus optional unlimited grenades:

  Unlimited Reserve   Your reserve ammo never runs out. You still reload.
  No Reload           Bottomless magazines. You never reload.
  Unlimited Grenades  Frag, krak and shock grenades never run out.

Covers every player weapon in Campaign and Operations/Siege, including the
weapon perk variants (e.g. the underbarrel grenade launcher).
PvP (Eternal War) is NOT affected.


INSTALL - VORTEX / MOD ORGANIZER 2
----------------------------------
Install the main file normally. A menu will ask which options you want.
To change options later, reinstall the mod.


INSTALL - MANUAL
----------------
1. Open: <game folder>\client_pc\root\mods
   (create the "mods" folder if it doesn't exist)
2. Copy ONE ammo .pak into it:
     "1 - Unlimited Reserve\UnlimitedAmmo.pak"            or
     "2 - No Reload\UnlimitedAmmo_NoReload.pak"
3. Optionally also copy "3 - Unlimited Grenades\UnlimitedGrenades.pak"
4. Open pak_config.yaml in that folder (create it if missing) and add a pair
   of lines for each .pak you copied, for example:

     - pak: UnlimitedAmmo.pak
       disabled: false
     - pak: UnlimitedGrenades.pak
       disabled: false

Do not install both ammo .paks at once.


UNINSTALL
---------
Vortex/MO2: remove the mod.
Manual: delete the .pak files and their lines in pak_config.yaml.


AFTER A GAME UPDATE
-------------------
If the game crashes after a patch, remove this mod and wait for an update.
Or use the optional "Patcher" download: it rebuilds the mod from your own
installed game files in a few seconds (requires Python 3.10+).


CONFLICTS
---------
Space Marine 2 mods replace whole files. Any mod that changes these files
will conflict, and whichever loads last wins:

  ssl/weapons/creator/firearm_library_pve.sso                    (ammo)
  ssl/weapons/creator/customization/firearm_modificators_library.sso (ammo)
  ssl/abilities/ability_library.sso                               (grenades)

Known conflicts: Astartes Overhaul, Primarch - Power Fantasy, and older
infinite-ammo mods. Turn off any other infinite-ammo mod before using this one.


CO-OP
-----
Works best solo or when you are the host. Please don't use it in public
lobbies with strangers.
