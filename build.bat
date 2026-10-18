@echo off
rem Converts the art in art\ and installs the mod into the game's mod folder.
rem Usage: build.bat                          (game in the default Steam folder)
rem        build.bat "D:\Steam\steamapps\common\Songs of Syx"
setlocal
cd /d "%~dp0"

set "GAME=%~1"
if "%GAME%"=="" if exist "C:\Program Files (x86)\Steam\steamapps\common\Songs of Syx\SongsOfSyx.jar" set "GAME=C:\Program Files (x86)\Steam\steamapps\common\Songs of Syx"
if "%GAME%"=="" if exist "M:\SteamLibrary\steamapps\common\Songs of Syx\SongsOfSyx.jar" set "GAME=M:\SteamLibrary\steamapps\common\Songs of Syx"
if not exist "%GAME%\SongsOfSyx.jar" (
    echo Could not find Songs of Syx. Run it again with your game folder, e.g.
    echo   build.bat "D:\Steam\steamapps\common\Songs of Syx"
    echo In Steam: right-click the game, Manage, Browse local files - that folder.
    exit /b 1
)
echo Using game folder: %GAME%

python "%~dp0tools\import_sprites.py" "%~dp0art" "%GAME%" || (echo Sprite import failed. & exit /b 1)
call .\mvnw.cmd -q install "-Dgame.install.directory=%GAME%" || (echo Build failed. & exit /b 1)

echo.
echo Done. Start Songs of Syx, enable "Yinglet Race" in the launcher's mod list, and start a new game.
