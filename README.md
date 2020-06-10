# system_tests
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

The datastreaming tests also require an installation of [docker for windows](https://docs.docker.com/docker-for-windows/install/#install-docker-desktop-on-windows).

Once these files are in place, run the tests with `run_tests.bat`


### Running all tests

To run all the tests in the test framework, `cd` to wherever you have the system_tests repository checked out and use:

```
run_tests.bat
```


### Running tests in modules

You can run tests in specific modules using the `-t` argument as follows:

```
run_tests.bat -t example_module  # Will run the stress rig tests and then the tests in the module example_module.
```

The argument is the name of the module containing the tests. This is the same as the name of the file in the `tests` directory, with the `.py` extension removed.


### Running tests in classes

You can run classes of tests in modules using the `-t` argument as follows:

```
run_tests.bat -t module.RunCommandTests # This will run all the tests in the RunCommandTests class in the module module. 
```

The argument is the "dotted name" of the class containing the tests. The dotted name takes the form `module.class`.


### Running tests by name

You can run tests by name using `-t` argument as follows:

```
run_tests.bat -t module.RunCommandTests.test_that_GIVEN_an_initialized_pump_THEN_it_is_stopped # This will run the test_that_GIVEN_an_initialized_pump_THEN_it_is_stopped test in the RunCommandTests class in the module module. 
```

The argument is the "dotted name" of the test containing the tests. The dotted name takes the form `module.class.test`.

You can run multiple tests from multiple classes in different modules.


### Running multiple individual tests, or from multiple models or classes

You can run multiple individual tests using the `-t` argument as follows:

```
run_tests.bat -t example_module.ExampleClass.test_if_num_is_correct example_module2.AnotherExampleClass.test_if_bool_is_true
```

That will test the `test_if_num_is_correct` and `test_if_bool_is_true` from their respective classes. You can also run all tests from multiple specific modules or classes that you want. 
