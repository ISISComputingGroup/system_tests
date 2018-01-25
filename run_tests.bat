setlocal
call C:\Instrument\Apps\EPICS\config_env.bat
call C:\Instrument\Apps\EPICS\start_ibex_server.bat
%PYTHON% run_tests.py || echo "running tests failed."
call C:\Instrument\Apps\EPICS\ISIS\JournalParser\master\test\run_tests.bat || echo "running tests failed."
C:\Instrument\Apps\EPICS\stop_ibex_server.bat
