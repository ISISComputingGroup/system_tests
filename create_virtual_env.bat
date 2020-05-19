setlocal
call C:\Instrument\Apps\EPICS\config_env.bat
%PYTHON3DIR%\Scripts\virtualenv.exe venv --system-site-packages
call "%~dp0venv\Scripts\activate.bat"
call "%~dp0venv\Scripts\pip.exe" install -r requirements.txt