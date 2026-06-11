@echo off
title 9Router Qoder Fallback Patch
color 0A

echo ============================================
echo   9Router - Qoder Queue Error Fallback Patch
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found! Install Python 3.8+ first.
    echo         https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Find patch script (same folder as .bat)
set "SCRIPT=%~dp09router-qoder-patch.py"
if not exist "%SCRIPT%" (
    echo [ERROR] Patch script not found: %SCRIPT%
    echo         Make sure 9router-qoder-patch.py is in the same folder.
    echo.
    pause
    exit /b 1
)

:: Show menu
echo What do you want to do?
echo.
echo   [1] Apply patch   (fix Qoder queue errors)
echo   [2] Check status  (see if patch is active)
echo   [3] Revert patch  (restore original files)
echo   [4] Test API      (send test request)
echo   [Q] Quit
echo.
set /p choice="  Choose (1-4/Q): "

if /i "%choice%"=="1" goto apply
if /i "%choice%"=="2" goto check
if /i "%choice%"=="3" goto revert
if /i "%choice%"=="4" goto test
if /i "%choice%"=="Q" exit /b 0
if /i "%choice%"=="q" exit /b 0

echo Invalid choice.
pause
exit /b 0

:apply
echo.
echo Applying patches...
echo.
python "%SCRIPT%" --apply
echo.
echo.
echo Restarting 9router...
taskkill /f /im node.exe /fi "WINDOWTITLE eq 9router*" >nul 2>&1
timeout /t 2 /nobreak >nul
echo Done! Restart 9router manually if needed: 9router
echo.
pause
exit /b 0

:check
echo.
python "%SCRIPT%" --check
echo.
pause
exit /b 0

:revert
echo.
echo Reverting patches (restoring original files)...
echo.
python "%SCRIPT%" --revert
echo.
echo Restart 9router to apply: 9router stop ^&^& 9router
echo.
pause
exit /b 0

:test
echo.
echo Testing Qoder API (qd/qmodel_latest)...
echo.
python -c "import http.client,json,os;db=json.load(open(os.path.join(os.environ['APPDATA'],'9router','db.json')));k=db['apiKeys'][0]['key'];c=http.client.HTTPConnection('localhost',20128,timeout=30);c.request('POST','/v1/chat/completions',json.dumps({'model':'qd/qmodel_latest','messages':[{'role':'user','content':'say hi'}],'max_tokens':5,'stream':False}),{'Content-Type':'application/json','Authorization':'Bearer '+k,'Accept':'application/json'});r=c.getresponse();d=r.read().decode();c.close();print('HTTP',r.status);j=json.loads(d) if d else {};print(j.get('choices',[{}])[0].get('message',{}).get('content','') if 'choices' in j else 'Error: '+json.dumps(j.get('error',{})))" 2>&1
echo.
pause
exit /b 0
