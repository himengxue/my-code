@echo off
setlocal DisableDelayedExpansion
set "PYTHONUTF8=1"
set "DOUYIN_AGENT_HOME=%~dp0data"
set "HOME=%~dp0data\home"
if not exist "%HOME%" mkdir "%HOME%"
"%~dp0.venv\Scripts\python.exe" "%~dp0agent.py" %*
exit /b %errorlevel%
