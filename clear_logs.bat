setlocal
for /d %%i in ( C:\Instrument\Var\logs C:\Instrument\Var\autosave ) do (
    @echo Cleaning %%i
    pushd %%i
    del /s /q *.* >NUL
    popd
)
exit /b 0
