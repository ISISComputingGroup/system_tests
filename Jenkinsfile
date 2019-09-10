#!groovy

pipeline {

  // agent defines where the pipeline will run.
  agent {  
    label {
      label "genie_python_system_tests"
    }
  }
  
  triggers {
    pollSCM('H/2 * * * *')
    cron('H 4 * * *')
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
        bat """
            call ibex_utils/installation_and_upgrade/instrument_install_latest_build_only.bat
            """
      }
    }
    
    stage("Unit Test Results") {
      steps {
        bat """
            run_tests.bat
            """
        junit "test-reports/**/*.xml"
      }
    }
  }
  
  post {
    failure {
      step([$class: 'Mailer', notifyEveryUnstableBuild: true, recipients: 'icp-buildserver@lists.isis.rl.ac.uk', sendToIndividuals: true])
    }
  }
  
  // The options directive is for configuration that applies to the whole job.
  options {
    buildDiscarder(logRotator(numToKeepStr:'5', daysToKeepStr: '7'))
    timeout(time: 180, unit: 'MINUTES')
    disableConcurrentBuilds()
  }
}
