setlocal
pushd C:\Instrument\Var\logs
del /s /q *.log
del /q ioc\*.*
del /q conserver\*.*
del /q gateway\blockserver\*.*
del /q gateway\external\*.*
del /q genie_python\*.*
del /q deploy\*.*
del /q ibex_server\*.*
del /q IOCTestFramework\*.*
del /q /s *.*
popd
exit /b 0
