$ErrorActionPreference = "Stop"

$pyiArgs = @(
    "--onefile"
    "--windowed"
    "--noconfirm"
    "--name=Solaris"
    "--icon=asset\img\logo.ico"

    "--add-data=asset;asset"
    "--add-data=map;map"
    "--add-data=gameplay;gameplay"
    "--add-data=saves;saves"

    "--hidden-import=enemies.enemy"
    "--hidden-import=enemies.enemy_element"
    "--hidden-import=enemies.wizard"
    "--hidden-import=enemies.slime"
    "--hidden-import=enemies.tiny_orc"
    "--hidden-import=enemies.tiny_devil"
    "--hidden-import=enemies.kitsune"
    "--hidden-import=enemies.gorgona"

    "--hidden-import=battle.battle"
    "--hidden-import=battle.battle_func"
    "--hidden-import=battle.multi_battle"
    "--hidden-import=battle.boss_battle"
    "--hidden-import=battle.final_battle"

    "--hidden-import=classes.armory_item"
    "--hidden-import=classes.status_effects"

    "--hidden-import=floor.castle"
    "--hidden-import=floor.mystic"
    "--hidden-import=floor.catacombs"

    "--hidden-import=Modules.char"
    "--hidden-import=Modules.objects"
    "--hidden-import=Modules.mystic_effects"
    "--hidden-import=Modules.cinematics"
    "--hidden-import=Modules.dialogue_box"
    "--hidden-import=Modules.game_frame"
    "--hidden-import=Modules.inv"
    "--hidden-import=Modules.particles"
    "--hidden-import=Modules.pause_menu"
    "--hidden-import=Modules.quest"
    "--hidden-import=Modules.save_manager"
    "--hidden-import=Modules.stats_menu"
    "--hidden-import=Modules.transition"
    "--hidden-import=Modules.chest"
    "--hidden-import=Modules.button"
    "--hidden-import=Modules.sound_manager"

    "--hidden-import=player.player"

    "--hidden-import=Fmain_menu.main_menu"
    "--hidden-import=Fmain_menu.play_continue"
    "--hidden-import=Fmain_menu.prologue"
    "--hidden-import=Fmain_menu.tutorial"
    "--hidden-import=Fmain_menu.setting"
    "--hidden-import=Fmain_menu.ingame_setting"
    "--hidden-import=Fmain_menu.about"

    "--hidden-import=map.map"

    "main.py"
)

Write-Host "Building Solaris.exe ..." -ForegroundColor Cyan
pyinstaller @pyiArgs

Write-Host ""
Write-Host "Done.  Output: dist\Solaris.exe" -ForegroundColor Green
Write-Host "Saves will be created next to the exe on first launch." -ForegroundColor Green