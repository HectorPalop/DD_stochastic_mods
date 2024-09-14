@echo off

REM Change to the base directory
cd /d "C:\Users\hecto\Documents\DD_MOD\DD_stochastic_mods"

REM Copy files from the vanilla backup folder to the game directory
xcopy "vanilla_backup" "DarkestDungeon" /E /I /Y

REM Change to the Stochastic_Trinkets directory
cd Stochastic_Trinkets

REM Erase contents of modded_trinkets.string_table.xml
echo.> "mod\localization\modded_trinkets.string_table.xml"

REM Erase contents of base.entries.trinkets.json
echo.> "mod\trinkets\base.entries.trinkets.json"

REM Delete modded.rarities.trinkets.json
if exist "mod\trinkets\modded.rarities.trinkets.json" del "mod\trinkets\modded.rarities.trinkets.json"

REM Copy contents of vanilla_all_buffs.json to base.buffs.json
copy /Y "vanilla_all_buffs.json" "mod\shared\buffs\base.buffs.json"

REM Delete all files in the icons_equip folder
del /Q "mod\panels\icons_equip\trinket\*.*"

echo Vanilla files have been restored, mod files have been prepared, modded rarities file has been deleted, and icons_equip folder has been cleared.