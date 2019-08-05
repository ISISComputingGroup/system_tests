# genie_python_system_tests
System tests of IBEX and genie_python


## Setup

If you want to run these tests on a developer machine, some files will need to be copied from the settings directory of a build machine.

* Copy these files from `system_tests/configs/tables` into your `C:/Instrument/settings/<machine name>/tables/` directory:
    1. RCPTT_detector128.dat
    1. RCPTT_spectra128.dat
    1. RCPTT_wiring128.dat
    
* Copy these files from `system_tests/configs/tcb` into your `C:/Instrument/settings/<machine name>/tcb/` directory:
    1. RCPTT_TCB_1.dat
    1. RCPTT_TCB_2.dat
    
* Copy these folders from `system_tests/configs/configurations` into your `C:/Instrument/settings/<machine name>/configurations/` directory:
    1. block_in_title
    1. memory_usage
    1. rcptt_simple
    
Once these files are in place, run the tests with `run_tests.bat`
