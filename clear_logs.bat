setlocal
REM ignore errors as del may attempt to delete a directory
for /d %%i in ( C:\Instrument\Var\logs C:\Instrument\Var\autosave C:\Instrument\Var\logs ) do (
    @echo Cleaning %%i
    if exist "%%i" (
        pushd %%i
        del /s /q *.* >NUL 2>&1
        popd
    )
)  
exit /b 0
