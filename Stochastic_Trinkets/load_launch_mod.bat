@echo off

REM Copy files from the mod folder to the game directory
xcopy "C:\Users\hecto\Documents\DD_MOD\DD_stochastic_mods\Stochastic_Trinkets\mod" "C:\Users\hecto\Documents\DD_MOD\DD_stochastic_mods\DarkestDungeon" /E /I /Y
echo Game files moved to the game directory.

REM Force CMD to run localization.bat
cd /d "C:\Users\hecto\Documents\DD_MOD\DD_stochastic_mods\DarkestDungeon\localization"
call localization.bat
echo executed localization.bat

REM Change to the game's executable directory
cd /d "C:\Users\hecto\Documents\DD_MOD\DD_stochastic_mods\DarkestDungeon\_windows"

REM Start the game with specified launch options
start "" "Darkest.exe" -skiptutorial -alltrinkets -norestore -skipfeflow -noguisfx -nomusic
echo game launched
