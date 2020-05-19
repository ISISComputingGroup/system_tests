import unittest
from compose.cli.main import TopLevelCommand, project_from_options
from time import sleep
from kafka import KafkaProducer, KafkaAdminClient
from kafka.errors import KafkaTimeoutError, UnrecognizedBrokerVersion
from utilities.utilities import g, load_config_if_not_already_loaded, setup_simulated_wiring_tables
import os
import datetime


NUMBER_OF_POLLS = 10
TIMEOUT = 10

docker_default_options = {
    "--no-deps": False,
    "--always-recreate-deps": False,
    "--scale": "",
    "--abort-on-container-exit": False,
    "SERVICE": "",
    "--remove-orphans": False,
    "--no-recreate": True,
    "--force-recreate": False,
    "--no-build": False,
    "--no-color": False,
    "--rmi": "none",
    "--volumes": True,  # Remove volumes when docker-compose down (don't persist kafka and zk data)
    "--follow": False,
    "--timestamps": False,
    "--tail": "all",
    "--detach": True,
    "--build": False,
}


def run_containers(cmd, options):
    print("Running docker-compose up", flush=True)
    cmd.up(options)
    print("Finished docker-compose up", flush=True)
    wait_until_kafka_ready(cmd, options)


def wait_until_kafka_ready(docker_cmd, docker_options):
    print("Waiting for Kafka broker to be ready for system tests...")
    conf = {"bootstrap_servers": "localhost:9092"}
    kafka_ready = False

    for _ in range(NUMBER_OF_POLLS):
        try:
            producer = KafkaProducer(**conf)
            record_data = producer.send("waitUntilUp", value=b"Test message")
            record_data.get(TIMEOUT)
        except (KafkaTimeoutError, UnrecognizedBrokerVersion):
            pass
        else:
            kafka_ready = True
            break

    if not kafka_ready:
        docker_cmd.down(docker_options)  # Bring down containers cleanly
        raise Exception("Kafka broker was not ready after {} seconds, aborting tests.".format(NUMBER_OF_POLLS*TIMEOUT))

    client = KafkaAdminClient(**conf)
    topic_ready = False

    for _ in range(NUMBER_OF_POLLS):
        topics = client.list_topics()
        if "TEST_runInfo" in topics:
            topic_ready = True
            print("Topic is ready!", flush=True)
            break
        sleep(TIMEOUT)

    if not topic_ready:
        docker_cmd.down(docker_options)  # Bring down containers cleanly
        raise Exception("Kafka topic was not ready after {} seconds, aborting tests.".format(NUMBER_OF_POLLS*TIMEOUT))


def create_compose_command(docker_options):
    project = project_from_options(os.path.dirname(__file__), docker_options)
    return TopLevelCommand(project)


def get_kafka_docker_options():
    options = docker_default_options
    options["--project-name"] = "kafka"
    options["--file"] = [r"docker_images\docker-compose-kafka.yml"]
    return options


def start_kafka():
    print("Starting zookeeper and kafka")
    docker_options = get_kafka_docker_options()
    cmd = create_compose_command(docker_options)

    cmd.up(docker_options)
    print("Started kafka containers")
    wait_until_kafka_ready(cmd, docker_options)


def stop_kafka():
    print("Stopping zookeeper and kafka")
    options = get_kafka_docker_options()
    options["--timeout"] = 30
    cmd = create_compose_command(options)
    cmd.down(options)


def start_filewriter():
    print("Starting file writer")
    docker_options = docker_default_options
    docker_options["--file"] = [r"docker_images\docker-compose-filewriter.yml"]
    cmd = create_compose_command(docker_options)

    cmd.up(docker_options)
    print("Started file writer")


def stop_filewriter():
    print("Stopping file writer")
    docker_options = docker_default_options
    docker_options["--file"] = [r"docker_images\docker-compose-filewriter.yml"]
    docker_options["--timeout"] = 30
    docker_options["SERVICE"] = ["filewriter"]
    cmd = create_compose_command(docker_options)
    cmd.logs(docker_options)
    cmd.down(docker_options)


class TestDatastreaming(unittest.TestCase):
    """
    Tests for datastreaming and IBEX integration
    """

    @classmethod
    def setUpClass(cls) -> None:
        start_kafka()
        start_filewriter()

    @classmethod
    def tearDownClass(cls) -> None:
        stop_filewriter()
        stop_kafka()

    def setUp(self):
        #g.set_instrument(None)
        # all tests that interact with anything but genie should try to load a config to ensure that the configurations
        # in the tests are not broken, e.g. by a schema update
        #load_config_if_not_already_loaded("empty_for_system_tests")
        pass

    def test_kafka_started(self):
        print(datetime.datetime.now())
        sleep(10)
        print(datetime.datetime.now())


if __name__ == "__main__":
    unittest.main()
