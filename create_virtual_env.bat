if "%ICP_CONFIG_ENV_RUN%" == "" (
    call C:\Instrument\Apps\EPICS\config_env.bat
) else (
    @echo Using existing EPICS_ROOT %EPICS_ROOT%
)
del /q /s my_venv >NUL 2>&1
%PYTHON3% -m venv --system-site-packages my_venv
call "%~dp0my_venv\Scripts\activate.bat"
"%~dp0my_venv\Scripts\pip.exe" install -r requirements.txt
