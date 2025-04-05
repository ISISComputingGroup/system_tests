#!groovy

pipeline {

  // agent defines where the pipeline will run.
  agent {  
    label {
      label("${params.LABEL}")
    }
  }
  
  triggers {
    pollSCM('H/2 * * * *')
    cron("${params.CRON}")
  }

  environment {
      NODE = "${env.NODE_NAME}"
      ELOCK = "epics_${NODE}"
  }

  // The options directive is for configuration that applies to the whole job.
  options {
    buildDiscarder(logRotator(numToKeepStr:'5', daysToKeepStr: '14'))
    timestamps()
    // as we "checkout scm" as a stage, we do not need to do it here too
    skipDefaultCheckout(true)
    office365ConnectorWebhooks([[
                    name: "Office 365",
                    notifyBackToNormal: true,
                    startNotification: false,
                    notifyFailure: true,
                    notifySuccess: false,
                    notifyNotBuilt: false,
                    notifyAborted: false,
                    notifyRepeatedFailure: true,
                    notifyUnstable: true,
                    url: "${env.MSTEAMS_URL}"
            ]]
    )
    disableConcurrentBuilds()
    //throttleJobProperty(
    //      categories: ['system_tests'],
    //      throttleEnabled: true,
    //      throttleOption: 'category'
    //)
  }

  stages {  
    stage("Checkout") {
      steps {
        retry(3) {
            echo "Branch: ${env.BRANCH_NAME}"
            checkout scm
        }
      }
    }


      stage("Install latest IBEX") {
        steps {
         lock(resource: ELOCK, inversePrecedence: false) {
          bat """
            setlocal
            set \"MYJOB=${env.JOB_NAME}\"
            @echo Installing IBEX on node ${env.NODE_NAME}
            REM EPICS should always be a directory junction on build servers
            if exist "C:\\Instrument\\Apps\\EPICS\\stop_ibex_server.bat" (
                call C:\\Instrument\\Apps\\EPICS\\stop_ibex_server.bat
            )
            if exist "C:\\Instrument\\Apps\\EPICS-%MYJOB%" (
                call C:\\Instrument\\Apps\\EPICS-%MYJOB%\\stop_ibex_server.bat
            ) else (
                md C:\\Instrument\\Apps\\EPICS-%MYJOB%
            )
            REM clear logs early to stop reporting previous errors
            REM in case install aborts
            call %WORKSPACE%\\clear_logs.bat
            if exist "C:\\Instrument\\Apps\\EPICS" (
                @echo Removing EPICS directory link
                rmdir "C:\\Instrument\\Apps\\EPICS"
            )
            REM EPICS should be a junction but occasionally it seems to be a real directory
            REM usually happens when a build gets terminated early, but unsure of exact reasons
            if exist "C:\\Instrument\\Apps\\EPICS" (
                @echo WARNING: Needing to removing EPICS directory files as not a junction
                rmdir /s /q "C:\\Instrument\\Apps\\EPICS"
                if exist "C:\\Instrument\\Apps\\EPICS" rmdir /s /q "C:\\Instrument\\Apps\\EPICS"
            )
            if exist "C:\\Instrument\\Apps\\EPICS" (
                echo ERROR: Unable to remove EPICS
                exit /b 1
            )
            if not exist "C:\\Instrument\\Apps\\EPICS-%MYJOB%" (
                @echo unable to create C:\\Instrument\\Apps\\EPICS-%MYJOB%
                exit /b 1
            )
            mklink /j C:\\Instrument\\Apps\\EPICS C:\\Instrument\\Apps\\EPICS-%MYJOB%
            if %errorlevel% NEQ 0 (
                @echo unable to create junction from C:\\Instrument\\Apps\\EPICS to C:\\Instrument\\Apps\\EPICS-%MYJOB%
                exit /b 1
            )
            dir C:\\Instrument\\Apps
            if \"%MYJOB%\" == \"System_Tests_debug\" (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat CLEAN EPICS_DEBUG
            ) else if \"%MYJOB%\" == \"System_Tests_static\" (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat CLEAN EPICS_STATIC
            ) else if \"%MYJOB%\" == \"System_Tests_static_debug\" (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat CLEAN EPICS_STATIC_DEBUG
            ) else if \"%MYJOB%\" == \"System_Tests_release\" (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat RELEASE
            ) else if \"%MYJOB%\" == \"System_Tests_win32\" (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat CLEAN EPICS x86
            ) else if \"%MYJOB%\" == \"System_Tests_Win11\" (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat CLEAN EPICS
            ) else if \"%MYJOB%\" == \"System_Tests_Win11_Win11\" (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat CLEAN EPICS x64 win11
            ) else (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat
            )
            IF %errorlevel% NEQ 0 (
                @echo ERROR: unable to install ibex - error code %errorlevel%
                call C:\\Instrument\\Apps\\EPICS-%MYJOB%\\stop_ibex_server.bat
                rmdir "C:\\Instrument\\Apps\\EPICS"
                rd /s /q C:\\Instrument\\Apps\\EPICS-%MYJOB% >NUL 2>&1
                exit /b 1
            )
            dir C:\\Instrument\\Apps
            """
         }
        }
      }

      stage("Run Tests") {
        steps {
          lock(resource: ELOCK, inversePrecedence: false) {
           timeout(time: 18, unit: 'HOURS') {
              bat """
                set \"MYJOB=${env.JOB_NAME}\"
                call C:\\Instrument\\Apps\\EPICS-%MYJOB%\\stop_ibex_server.bat
                if exist "C:\\Instrument\\Apps\\EPICS" (
                    rmdir "C:\\Instrument\\Apps\\EPICS"
                )
                REM as ELOCK is released between stages clear logs to be safe
                call %WORKSPACE%\\clear_logs.bat
                mklink /J C:\\Instrument\\Apps\\EPICS C:\\Instrument\\Apps\\EPICS-%MYJOB%
                IF %errorlevel% NEQ 0 (
                    @echo ERROR: unable to make EPICS directory junction link to EPICS-%MYJOB% - error %errorlevel%
                    exit /b %errorlevel%
                )
                if not exist "C:\\Instrument\\Apps\\EPICS\\config_env.bat" (
                    @echo ERROR: Unable to find config_env.bat in linked EPICS directory
                    exit /b 1
                )
                @echo Running system tests on node ${env.NODE_NAME}
                if \"%MYJOB%\" == \"System_Tests_galilold\" (
                    call C:\\Instrument\\Apps\\EPICS\\swap_galil.bat OLD
        ) else if \"%MYJOB%\" == \"System_Tests_release\" (
                    call C:\\Instrument\\Apps\\EPICS\\swap_galil.bat OLD
                ) else (
                    call C:\\Instrument\\Apps\\EPICS\\swap_galil.bat NEW
        )
                call clean_files.bat
                @echo FIRST PART OF TESTS STARTED
                call run_tests.bat
                set errcode1=%errorlevel%
                if %errcode1% NEQ 0 (
                    @echo ERROR: FIRST PART OF TESTS FAILED WITH CODE %errcode1%
                ) else (
                    @echo OK: FIRST PART OF TESTS SUCCEEDED
                )
                @echo SECOND PART OF TESTS STARTED
                @echo Running IOC tests on node ${env.NODE_NAME}
                pushd "C:\\Instrument\\Apps\\EPICS"
                call config_env.bat
                REM make will usually stop on first test failure as python will return an error. We can pass -i to make to ignore
        REM this and we will still usually see a problem as the python unittest XML output will list it, but we miss
        REM the case when python crashes with no XML output. So we will try using -k which looks to "keep going"
                REM but still return an overall failure code
                make -k ioctests
                set errcode2=%errorlevel%
                popd
                @echo SECOND PART OF TESTS FINISHED WITH CODE %errcode2%
                call C:\\Instrument\\Apps\\EPICS\\stop_ibex_server.bat
                rmdir "C:\\Instrument\\Apps\\EPICS"
                @echo Finished running tests on node ${env.NODE_NAME}
                if %errcode1% NEQ 0 (
                    @echo ERROR: FIRST PART OF TESTS FAILED WITH CODE %errcode1%, SECOND PART CODE WAS %errcode2%
                    exit /b %errcode1%
                )
                if %errcode2% NEQ 0 (
                    @echo ERROR: FIRST PART OF TESTS SUCCEEDED, SECOND PART FAILED WITH CODE %errcode2%
        ) else (
                    @echo OK: BOTH FIRST AND SECOND PARTS OF TESTS SUCCEEDED
        )
                exit /b %errcode2%
             """
          }
        }
       }
      }

  }

  post {
    always {
        bat """
            set \"MYJOB=${env.JOB_NAME}\"
            @echo Saving test output on node ${env.NODE_NAME}
            robocopy "C:\\Instrument\\Var\\logs" "%WORKSPACE%\\var-logs" /S /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            robocopy "C:\\data" "%WORKSPACE%\\icp-logs" "journal.txt" "journal*.xml" /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            robocopy "C:\\data\\log" "%WORKSPACE%\\icp-logs" "*.log" /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            robocopy "C:\\Instrument\\Apps\\EPICS-%MYJOB%" "%WORKSPACE%\\ioctest-output" "*.xml" /S /PURGE /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            exit /b 0
        """
        archiveArtifacts artifacts: 'var-logs/**/*.*, icp-logs/*.*', caseSensitive: false
        junit "test-reports/**/*.xml,**/test-reports/**/*.xml"
        logParser ([
            projectRulePath: 'log_parse_rules.txt',
            parsingRulesPath: '',
            showGraphs: true, 
            unstableOnWarning: false,
            useProjectRule: true,
        ])
    }

    cleanup {
        bat """
            @echo off
            set \"MYJOB=${env.JOB_NAME}\"
            @echo Started cleanup on node ${env.NODE_NAME}
            REM call stop ibex server in case job aborted and not called
            REM this cleans things up for next clone
            if exist "C:\\Instrument\\Apps\\EPICS-%MYJOB%" (
                call C:\\Instrument\\Apps\\EPICS-%MYJOB%\\stop_ibex_server.bat
            )
            rmdir "C:\\Instrument\\Apps\\EPICS" >NUL 2>&1
            rd /s /q C:\\Instrument\\Apps\\EPICS-%MYJOB% >NUL 2>&1
            rd /q /s %WORKSPACE:/=\\%\\my_venv>NUL 2>&1
            REM clear logs as we have already archived them. Though we clear
            REM logs before an install also remove them here in case
            REM next job git checkout aborts and tries to report same errors
            REM as now all over again
            call %WORKSPACE%\\clear_logs.bat
            @echo Finished cleanup on node ${env.NODE_NAME}
            @echo ***
            @echo *** Any Office365connector Matched status FAILURE message below means
            @echo *** an earlier Jenkins step failed not the Office365connector itself
            @echo *** Search log file for  ERROR:  to locate true cause
            @echo ***
            exit /b 0
        """
    }
  }
  
}
