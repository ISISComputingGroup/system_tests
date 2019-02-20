# genie_python_system_tests
System tests of IBEX and genie_python

## Setup

If you want to run this directly in pycharm then:
 
 1. Open this and genie_python as a project in the same pycharm
 1. Set the dependencies in `Settings->Project->Project Dependencies` so that system_tests depends on genie_python
 1. Open the Run Configuration selector in the top-right and cick `Edit Configurations...`. Set the run enviornment of the test/run_tests to include:
 
    ```
    ICPCONFIGROOT=C:/Instrument/Settings/config/<host>/configurations
    PYTHONUNBUFFERED=1
    EPICS_CA_MAX_ARRAY_BYTES=65536
    EPICS_CA_ADDR_LIST=<ip address list as shown in Epics terminal>
    EPICS_CA_AUTO_ADDR_LIST=NO
    ```
 
