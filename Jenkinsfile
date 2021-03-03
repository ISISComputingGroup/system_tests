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
    cron('H 4 * * *')
  }

  environment {
      NODE = "${env.NODE_NAME}"
      ELOCK = "epics_${NODE}"
  }

  // The options directive is for configuration that applies to the whole job.
  options {
    buildDiscarder(logRotator(numToKeepStr:'5', daysToKeepStr: '7'))
    disableConcurrentBuilds()
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
         lock(resource: ELOCK, inversePrecedence: true) {
          bat """
            set \"MYJOB=${env.JOB_NAME}\"
            REM EPICS should always be a directory junction on build servers
            if exist "C:\\Instrument\\Apps\\EPICS" (
                call C:\\Instrument\\Apps\\EPICS\\stop_ibex_server.bat
                rmdir "C:\\Instrument\\Apps\\EPICS"
            )
            if \"%MYJOB%\" == \"System_Tests_debug\" (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat CLEAN EPICS_DEBUG
            ) else (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat
            )
            REM preserve error code as we need always need to rename EPICS directory
            set insterr=%errorlevel%
            if exist "C:\\Instrument\\Apps\\EPICS-%MYJOB%" (
                REM Retry delete multiple times as sometimes fails
                rd /q /s C:\\Instrument\\Apps\\EPICS-%MYJOB%>NUL
                rd /q /s C:\\Instrument\\Apps\\EPICS-%MYJOB%>NUL
                rd /q /s C:\\Instrument\\Apps\\EPICS-%MYJOB%>NUL
            )
            move C:\\Instrument\\Apps\\EPICS C:\\Instrument\\Apps\\EPICS-%MYJOB%
            set moveerr=%errorlevel%
            IF %insterr% NEQ 0 (
                @echo ERROR unable to install ibex
                exit /b %insterr%
            )
            IF %moveerr% NEQ 0 (
                @echo ERROR unable to rename directory
                exit /b %moveerr%
            )
            """
         }
        }
      }

      stage("System Tests") {
        steps {
         lock(resource: ELOCK, inversePrecedence: true) {
           timeout(time: 360, unit: 'MINUTES') {
          bat """
            set \"MYJOB=${env.JOB_NAME}\"
            if exist "C:\\Instrument\\Apps\\EPICS" (
                call C:\\Instrument\\Apps\\EPICS\\stop_ibex_server.bat
                rmdir "C:\\Instrument\\Apps\\EPICS"
            )
            mklink /J C:\\Instrument\\Apps\\EPICS C:\\Instrument\\Apps\\EPICS-%MYJOB%
            IF %errorlevel% NEQ 0 (
                @echo ERROR unable to make directory junction
                exit /b %errorlevel%
            )
            if not exist "C:\\Instrument\\Apps\\EPICS\\config_env.bat" (
                @echo ERROR Unable to find config_env.bat in linked directory
                exit /b 1
            )
            del /q C:\\Instrument\\Var\\logs\\ioc\\*.*
            call clean_files.bat
            call run_tests.bat
            set errcode=%errorlevel%
            rmdir "C:\\Instrument\\Apps\\EPICS"
            exit /b %errcode%
          """
          }
        }
      }
     }

  }

  post {
    always {
        bat """
            robocopy "C:\\Instrument\\Var\\logs\\ioc" "%WORKSPACE%\\ioc-logs" /E /R:2 /MT /NFL /NDL /NP /NC /NS /LOG:NUL
            exit /b 0
        """
        archiveArtifacts artifacts: 'ioc-logs/*.log', caseSensitive: false
        junit "test-reports/**/*.xml"
    }

    cleanup {
        bat """
            set \"MYJOB=${env.JOB_NAME}\"
            REM not ideal to call without lock, and retaking lock may be a potential race condition
            REM however the directory junction will only exist if the previous step times out      
            if exist "C:\\Instrument\\Apps\\EPICS" (
                call "C:\\Instrument\\Apps\\EPICS-%MYJOB%\\stop_ibex_server.bat"
            )
            rd /q /s C:\\Instrument\\Apps\\EPICS-%MYJOB%>NUL
            rd /q /s %WORKSPACE%\\my_venv>NUL
            exit /b 0
        """
    }
  }
  
}
