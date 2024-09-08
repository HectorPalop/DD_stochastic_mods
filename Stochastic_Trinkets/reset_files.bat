@echo off

REM Change to the base directory
cd /d "C:\Users\hecto\Documents\DD_MOD\DD_stochastic_mods"

REM Copy files from the vanilla backup folder to the game directory
xcopy "vanilla_backup" "DarkestDungeon" /E /I /Y

REM Change to the Stochastic_Trinkets directory
cd Stochastic_Trinkets

REM Erase contents of trinket_strings_table.xml
echo.> "mod\localization\trinket_strings_table.xml"

REM Erase contents of base.entries.trinkets.json
echo.> "mod\trinkets\base.entries.trinkets.json"

REM Copy contents of vanilla_all_buffs.json to base.buffs.json
copy /Y "vanilla_all_buffs.json" "mod\shared\buffs\base.buffs.json"

REM Delete all files in the icons_equip folder
del /Q "mod\panels\icons_equip\trinket\*.*"

echo Vanilla files have been restored, mod files have been prepared, and icons_equip folder has been cleared.