call C:\Instrument\Apps\EPICS\config_env.bat
%PYTHON3% -m venv --system-site-packages my_venv
call "%~dp0my_venv\Scripts\activate.bat"
call "%~dp0my_venv\Scripts\pip.exe" install -r requirements.txt