setlocal
pushd c:\
del /q C:\Instrument\Var\logs\ioc\*.*
del /q C:\Instrument\Var\logs\conserver\*.*
del /q C:\Instrument\Var\logs\gateway\blockserver\*.*
del /q C:\Instrument\Var\logs\gateway\external\*.*
del /q C:\Instrument\Var\logs\genie_python\*.*
del /q C:\Instrument\Var\logs\deploy\*.*
del /q C:\Instrument\Var\logs\ibex_server\*.*
del /q C:\Instrument\Var\logs\IOCTestFramework\*.*
popd
exit /b 0
