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
    timeout(time: 180, unit: 'MINUTES')
    disableConcurrentBuilds()
    timestamps()
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
        echo "Branch: ${env.BRANCH_NAME}"
        checkout scm
      }
    }


      stage("Install latest IBEX") {
        steps {
         lock(resource: ELOCK, inversePrecedence: true) {
          bat """
            set \"MYJOB=${env.JOB_NAME}\"
            if \"%MYJOB%\" == \"System_Tests_debug\" (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat CLEAN EPICS_DEBUG
            ) else (
                call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat
            )
            IF %errorlevel% NEQ 0 exit /b %errorlevel%
            if exist "C:\\Instrument\\Apps\\EPICS-%MYJOB%" (
                rd /q /s C:\\Instrument\\Apps\\EPICS-%MYJOB%>NUL
            )
            move C:\\Instrument\\Apps\\EPICS C:\\Instrument\\Apps\\EPICS-%MYJOB%
            """
         }
        }
      }

      stage("Unit Test Results") {
        steps {
         lock(resource: ELOCK, inversePrecedence: true) {
          bat """
            set \"MYJOB=${env.JOB_NAME}\"
            mklink /J C:\\Instrument\\Apps\\EPICS C:\\Instrument\\Apps\\EPICS-%MYJOB%
            IF %errorlevel% NEQ 0 (
                @echo unable to make directory junction
                exit /b %errorlevel%
            )
            if not exist "C:\\Instrument\\Apps\\EPICS\\config_env.bat" (
                @echo Unable to find config_env.bat in linked directory
                exit /b 1
            )
            run_tests.bat
            """
          junit "test-reports/**/*.xml"
        }
      }
     }

  }

  post {
    cleanup {
        echo "Cleaning"
        timeout(time: 3, unit: 'HOURS') {
          bat """
                  set \"MYJOB=${env.JOB_NAME}\"
                  REM Retry delete multiple times as sometimes fails
                  rd /q /s C:\\Instrument\\Apps\\EPICS-%MYJOB%>NUL
                  rd /q /s C:\\Instrument\\Apps\\EPICS-%MYJOB%>NUL
                  rd /q /s C:\\Instrument\\Apps\\EPICS-%MYJOB%>NUL
                  exit /b 0
          """
        }
    }
  }
  
}
