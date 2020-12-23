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
            call run_tests.bat
            set errcode=%errorlevel%
            rmdir "C:\\Instrument\\Apps\\EPICS"
            exit /b %errcode%
          """
        }
      }
     }

  }

  post {
    always {
        junit "test-reports/**/*.xml"
    }

    cleanup {
        bat """
            set \"MYJOB=${env.JOB_NAME}\"
            rd /q /s C:\\Instrument\\Apps\\EPICS-%MYJOB%>NUL
            exit /b 0
        """
    }
  }
  
}
