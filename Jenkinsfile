#!groovy

pipeline {

  // agent defines where the pipeline will run.
  agent {  
    label {
      label "genie_python_system_tests"
    }
  }
  
  triggers {
    [pollSCM('H/2 * * * *'),
    cron('H 4 * * *')]
  }
  
  stages {  
    stage("Checkout") {
      steps {
        echo "Branch: ${env.BRANCH_NAME}"
        checkout scm
      }
    }
    
    stage("Build") {
      steps {
        bat """
            jenkis.bat
            C:/Instrument/Apps/Python/python.exe run_tests.py || echo "running tests failed."
            """
      }
    }
   stage("Unit Test Results") {
    steps {
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
    timeout(time: 60, unit: 'MINUTES')
    disableConcurrentBuilds()
  }
}
