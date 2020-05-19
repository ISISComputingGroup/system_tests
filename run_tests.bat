setlocal
call create_virtual_env.bat
python -c "exec(\"from psutil import virtual_memory\nprint(virtual_memory().used)\")">base_line_memory.txt
set /P BASE_MEMORY_USAGE=<base_line_memory.txt
start /wait cmd /c %EPICS_ROOT%\start_ibex_server.bat
set "PYTHONUNBUFFERED=1"
python "%~dp0run_tests.py" %* || echo "running base tests failed."
call %EPICS_ROOT%\ISIS\JournalParser\master\test\run_tests.bat || echo "running journal tests failed."
start /wait cmd /c %EPICS_ROOT%\stop_ibex_server.bat
