call C:\Instrument\Apps\EPICS\config_env.bat
del /q /s my_venv >NUL 2>&1
%PYTHON3% -m venv --system-site-packages my_venv
call "%~dp0my_venv\Scripts\activate.bat"
call "%~dp0my_venv\Scripts\pip.exe" install -r requirements.txt
