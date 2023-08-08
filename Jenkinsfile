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
    buildDiscarder(logRotator(numToKeepStr:'10', daysToKeepStr: '14'))
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
            set \"MYJOB=${env.JOB_NAME}\"
            @echo Installing IBEX on node ${env.NODE_NAME}
            REM EPICS should always be a directory junction on build servers
            if exist "C:\\Instrument\\Apps\\EPICS" (
                call C:\\Instrument\\Apps\\EPICS\\stop_ibex_server.bat
                @echo Removing EPICS directory link
                rmdir "C:\\Instrument\\Apps\\EPICS"
            )
            if exist "C:\\Instrument\\Apps\\EPICS" (
                echo ERROR Unable to remove EPICS
                exit /b 1
            )
            if exist "C:\\Instrument\\Apps\\EPICS-%MYJOB%" (
                call C:\\Instrument\\Apps\\EPICS-%MYJOB%\\stop_ibex_server.bat
            ) else (
                md C:\\Instrument\\Apps\\EPICS-%MYJOB%
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
            ) else (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat
            )
            IF %errorlevel% NEQ 0 (
                @echo ERROR unable to install ibex - error code %errorlevel%
                call C:\\Instrument\\Apps\\EPICS-%MYJOB%\\stop_ibex_server.bat
                rmdir "C:\\Instrument\\Apps\\EPICS"
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
           timeout(time: 1800, unit: 'MINUTES') {
              bat """
                set \"MYJOB=${env.JOB_NAME}\"
                call C:\\Instrument\\Apps\\EPICS-%MYJOB%\\stop_ibex_server.bat
                if exist "C:\\Instrument\\Apps\\EPICS" (
                    rmdir "C:\\Instrument\\Apps\\EPICS"
                )
                del /q C:\\Instrument\\Var\\logs\\ioc\\*.*
                del /q C:\\Instrument\\Var\\logs\\conserver\\*.*
                del /q C:\\Instrument\\Var\\logs\\gateway\\blockserver\\*.*
                del /q C:\\Instrument\\Var\\logs\\gateway\\external\\*.*
                del /q C:\\Instrument\\Var\\logs\\genie_python\\*.*
                del /q C:\\Instrument\\Var\\logs\\deploy\\*.*
                del /q C:\\Instrument\\Var\\logs\\ibex_server\\*.*
                del /q C:\\Instrument\\Var\\logs\\IOCTestFramework\\*.*
                mklink /J C:\\Instrument\\Apps\\EPICS C:\\Instrument\\Apps\\EPICS-%MYJOB%
                IF %errorlevel% NEQ 0 (
                    @echo ERROR unable to make EPICS directory junction link to EPICS-%MYJOB% - error %errorlevel%
                    exit /b %errorlevel%
                )
                if not exist "C:\\Instrument\\Apps\\EPICS\\config_env.bat" (
                    @echo ERROR Unable to find config_env.bat in linked EPICS directory
                    exit /b 1
                )
                @echo Running system tests on node ${env.NODE_NAME}
                if \"%MYJOB%\" == \"System_Tests_release\" (
                    call C:\\Instrument\\Apps\\EPICS\\swap_galil.bat OLD
                ) else (
                    call C:\\Instrument\\Apps\\EPICS\\swap_galil.bat NEW
                )
                call clean_files.bat
                @echo FIRST PART OF TESTS STARTED
                call run_tests.bat
                set errcode1=%errorlevel%
                @echo FIRST PART OF TESTS FINISHED WITH CODE %errcode1%
                @echo SECOND PART OF TESTS STARTED
                @echo Running IOC tests on node ${env.NODE_NAME}
                pushd "C:\\Instrument\\Apps\\EPICS"
                call config_env.bat
                REM make will stop on first test failure as python will return an error. We can pass -i to make to ignore
		REM this and we will still usually see a problem as the python unittest XML output will list it, but we miss
		REM the case when python crashes with no XML output. So we will move back to not using -i for now
                make ioctests
                set errcode2=%errorlevel%
                popd
                @echo SECOND PART OF TESTS FINISHED WITH CODE %errcode2%
                call C:\\Instrument\\Apps\\EPICS\\stop_ibex_server.bat
                rmdir "C:\\Instrument\\Apps\\EPICS"
                @echo Finished running tests on node ${env.NODE_NAME}
                if %errcode1% NEQ 0 (
                    @echo ERROR - FIRST PART OF TESTS FAILED WITH CODE %errcode1%, SECOND PART CODE WAS %errcode2%
                    exit /b %errcode1%
                )
                if %errcode2% NEQ 0 (
                    @echo ERROR - FIRST PART OF TESTS SUCCEEDED, SECOND PART FAILED WITH CODE %errcode2%
		) else (
                    @echo SUCCESS - BOTH FIRST AND SECOND PARTS OF TESTS SUCCEEDED
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
            robocopy "C:\\Instrument\\Var\\logs\\ioc" "%WORKSPACE%\\ioc-logs" /E /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            robocopy "C:\\Instrument\\Var\\logs\\IOCTestFramework" "%WORKSPACE%\\ioctest-logs" /E /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            robocopy "C:\\Instrument\\Var\\logs\\gateway" "%WORKSPACE%\\gateway-logs" /E /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            robocopy "C:\\Instrument\\Var\\logs\\genie_python" "%WORKSPACE%\\genie_python-logs" /E /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            robocopy "C:\\Instrument\\Var\\logs\\deploy" "%WORKSPACE%\\deploy-logs" /E /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            robocopy "C:\\Instrument\\Var\\logs\\ibex_server" "%WORKSPACE%\\ibex_server-logs" /E /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            robocopy "C:\\Instrument\\Apps\\EPICS-%MYJOB%" "%WORKSPACE%\\ioctest-output" "*.xml" /S /PURGE /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            exit /b 0
        """
        archiveArtifacts artifacts: '*-logs/*.log', caseSensitive: false
        junit "test-reports/**/*.xml,**/test-reports/**/*.xml"
    }

    cleanup {
        bat """
	    @echo off
            set \"MYJOB=${env.JOB_NAME}\"
            @echo Started cleanup on node ${env.NODE_NAME}
            REM stop ibex server will already have been called if needed
            REM we could try and cleanup EPICS-%MYJOB% but unless we are short of disk space
            REM leaving it gives us a stop_ibex_server there for next job run
            rmdir "C:\\Instrument\\Apps\\EPICS" >NUL 2>&1
            rd /q /s %WORKSPACE:/=\\%\\my_venv>NUL 2>&1
            @echo Finished cleanup on node ${env.NODE_NAME}
	    @echo ***
            @echo *** Any Office365connector Matched status FAILURE message below means
            @echo *** an earlier Jenkins step failed not the Office365connector itself
            @echo *** Search log file for  ERROR  to locate true cause
            @echo ***
            exit /b 0
        """
    }
  }
  
}
