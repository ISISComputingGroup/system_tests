setlocal
call C:\Instrument\Apps\EPICS\config_env.bat
%PYTHON% -c "exec(\"from psutil import virtual_memory\nprint(virtual_memory().used)\")">base_line_memory.txt
set /P BASE_MEMORY_USAGE=<base_line_memory.txt
start /wait cmd /c C:\Instrument\Apps\EPICS\start_ibex_server.bat
set "PYTHONUNBUFFERED=1"
%PYTHON% "%~dp0run_tests.py" %* || echo "running tests failed."
call C:\Instrument\Apps\EPICS\ISIS\JournalParser\master\test\run_tests.bat || echo "running tests failed."
start /wait cmd /c C:\Instrument\Apps\EPICS\stop_ibex_server.bat
