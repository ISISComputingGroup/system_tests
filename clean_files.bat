setlocal
pushd c:\data
del /q /f data.run* current.run* selog.sq3* *.nxs *.raw *.log *.txt *.xml log\*.* events\*.*
del /q /f /s events\*
popd
exit /b 0
