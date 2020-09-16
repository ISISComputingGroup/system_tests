import unittest
from compose.cli.main import TopLevelCommand, project_from_options
from time import sleep
from kafka import KafkaProducer, KafkaAdminClient, KafkaConsumer, TopicPartition
from kafka.errors import KafkaTimeoutError, UnrecognizedBrokerVersion
from utilities.utilities import g, load_config_if_not_already_loaded, setup_simulated_wiring_tables
import os
import h5py
import socket
import docker
from streaming_data_types.histogram_hs00 import deserialise_hs00
import numpy

NUMBER_OF_POLLS = 10
TIMEOUT = 10


def check_docker_exists():
    try:
        client = docker.from_env()
        returned_string = client.containers.run("ubuntu:latest", "echo 1")
        return returned_string == b'1\n'
    except:
        return False


DOCKER_EXISTS = check_docker_exists()


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


def get_last_kafka_message(topic):
    consumer = KafkaConsumer()
    topic_partition = TopicPartition(topic, 0)
    consumer.assign([topic_partition])
    consumer.seek_to_end(topic_partition)
    last_offset = consumer.position(topic_partition)
    if last_offset != 0:
        consumer.seek(topic_partition, last_offset - 1)
    return next(consumer)


def run_containers(cmd, options):
    print("Running docker-compose up", flush=True)
    cmd.up(options)
    print("Finished docker-compose up", flush=True)
    wait_until_kafka_ready(cmd, options)


def wait_until_kafka_ready(docker_cmd, docker_options):
    print("Waiting for Kafka broker to be ready for system tests...")
    conf = {"bootstrap_servers": "localhost:9092"}
    kafka_ready = False
    wait_topic = "waitUntilUp"

    for _ in range(NUMBER_OF_POLLS):
        try:
            producer = KafkaProducer(**conf)
            record_data = producer.send(wait_topic, value=b"Test message")
            record_data.get(TIMEOUT)
            get_last_kafka_message(wait_topic)

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
        if "TEST_runInfo" in topics and "TEST_monitorHistograms" in topics:
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
        if DOCKER_EXISTS:
            start_kafka()
            start_filewriter()
            pass

    @classmethod
    def tearDownClass(cls) -> None:
        if DOCKER_EXISTS:
            stop_filewriter()
            stop_kafka()

    def setUp(self):
        if not DOCKER_EXISTS:
            self.skipTest("Docker not running on this machine")

        g.set_instrument(None)
        # all tests that interact with anything but genie should try to load a config to ensure that the configurations
        # in the tests are not broken, e.g. by a schema update
        load_config_if_not_already_loaded("empty_for_system_tests")

        setup_simulated_wiring_tables(True)

    def test_WHEN_run_performed_THEN_nexus_file_saved_with_events(self):
        g.begin()
        sleep(5)
        run_number = g.get_runnumber()
        g.end()
        sleep(10)  # Wait for file to finish writing, look at status instead?
        file_path = r".\docker_images\output-files\{}{}.nxs".format(socket.gethostname(), run_number)
        with h5py.File(file_path,  "r") as f:
            saved_events = f[r"/entry/events/event_id"]
            self.assertTrue(len(saved_events) > 0)

    def test_WHEN_run_performed_THEN_histogram_events_published(self):
        low, high, step = 10, 100, 5
        num_time_channels = (high-low)/step
        g.change_tcb(low=low, high=high, step=step)
        g.begin()
        sleep(1)
        g.end()
        latest_histogram_message = get_last_kafka_message("TEST_monitorHistograms")
        latest_histogram_message = deserialise_hs00(latest_histogram_message.value)

        self.assertEqual(latest_histogram_message["source"], "monitor_1")
        self.assertListEqual(latest_histogram_message["current_shape"], [g.get_number_periods(), 1, num_time_channels])
        dimensions = latest_histogram_message["dim_metadata"]

        def test_dimension(index, expected_length, expected_boundaries, expected_label):
            length = dimensions[index]["length"]
            boundaries = dimensions[index]["bin_boundaries"]
            label = dimensions[index]["label"]
            self.assertEqual(length, expected_length)
            self.assertTrue(numpy.array_equal(boundaries, expected_boundaries))
            self.assertEqual(label, expected_label)

        expected_array = numpy.arange(0.5, g.get_number_periods() + 0.6, 1)
        test_dimension(0, g.get_number_periods(), expected_array, "period_index")

        test_dimension(1, 1, numpy.array([2.5, 3.5]), "spectrum_index")

        expected_array = numpy.arange(low, high + 0.5, step)
        test_dimension(2, num_time_channels, expected_array, "time_of_flight")


if __name__ == "__main__":
    unittest.main()
