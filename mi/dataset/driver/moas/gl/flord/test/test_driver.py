"""
@package mi.dataset.driver.moas.gl.flord.test.test_driver
@file marine-integrations/mi/dataset/driver/moas/gl/flord/test/test_driver.py
@author Bill French
@brief Test cases for glider ctd data

USAGE:
 Make tests verbose and provide stdout
   * From the IDK
       $ bin/dsa/test_driver
       $ bin/dsa/test_driver -i [-t testname]
       $ bin/dsa/test_driver -q [-t testname]
"""

__author__ = 'Bill French'
__license__ = 'Apache 2.0'

import unittest

from nose.plugins.attrib import attr

from mi.core.log import get_logger ; log = get_logger()

from exceptions import Exception

from mi.idk.dataset.unit_test import DataSetTestCase
from mi.idk.dataset.unit_test import DataSetIntegrationTestCase
from mi.idk.dataset.unit_test import DataSetQualificationTestCase

from mi.idk.exceptions import SampleTimeout

from mi.dataset.dataset_driver import DataSourceConfigKey, DataSetDriverConfigKeys
from mi.dataset.dataset_driver import DriverParameter
from mi.dataset.driver.moas.gl.flord.driver import FLORDDataSetDriver
from mi.dataset.driver.moas.gl.flord.driver import DataTypeKey

from mi.dataset.parser.glider import FlordTelemeteredDataParticle, FlordRecoveredDataParticle, DataParticleType
from pyon.agent.agent import ResourceAgentState

from interface.objects import ResourceAgentErrorEvent

TELEMETERED_TEST_DIR = '/tmp/flordTelemeteredTest'
RECOVERED_TEST_DIR = '/tmp/flordRecoveredTest'

DataSetTestCase.initialize(

    driver_module='mi.dataset.driver.moas.gl.flord.driver',
    driver_class="FLORDDataSetDriver",
    agent_resource_id='123xyz',
    agent_name='Agent007',
    agent_packet_config=FLORDDataSetDriver.stream_config(),
    startup_config={
        DataSourceConfigKey.RESOURCE_ID: 'flord',
        DataSourceConfigKey.HARVESTER:
        {
            DataTypeKey.FLORD_TELEMETERED:
            {
                DataSetDriverConfigKeys.DIRECTORY: TELEMETERED_TEST_DIR,
                DataSetDriverConfigKeys.STORAGE_DIRECTORY: '/tmp/stored_flordTelemeteredTest',
                DataSetDriverConfigKeys.PATTERN: '*.mrg',
                DataSetDriverConfigKeys.FREQUENCY: 1,
            },
            DataTypeKey.FLORD_RECOVERED:
            {
                DataSetDriverConfigKeys.DIRECTORY: RECOVERED_TEST_DIR,
                DataSetDriverConfigKeys.STORAGE_DIRECTORY: '/tmp/stored_flordRecoveredTest',
                DataSetDriverConfigKeys.PATTERN: '*.mrg',
                DataSetDriverConfigKeys.FREQUENCY: 1,
            }
        },
        DataSourceConfigKey.PARSER: {
            DataTypeKey.FLORD_TELEMETERED: {}, DataTypeKey.FLORD_RECOVERED: {}
        }
    }

)

###############################################################################
#                                UNIT TESTS                                   #
# Device specific unit tests are for                                          #
# testing device specific capabilities                                        #
###############################################################################
@attr('INT', group='mi')
class IntegrationTest(DataSetIntegrationTestCase):

    ## DONE
    def test_get(self):
        """
        Test that we can get data from files.  Verify that the driver sampling
        can be started and stopped.
        """
        self.clear_sample_data()

        # Start sampling and watch for an exception
        self.driver.start_sampling()

        self.clear_async_data()
        #self.create_sample_data_set_dir('single_glider_record.mrg',
        self.create_sample_data_set_dir('single_flord_record.mrg',
                                        TELEMETERED_TEST_DIR,
                                        "unit_363_2013_245_6_6.mrg")
        self.assert_data(FlordTelemeteredDataParticle,
                         'single_flord_record.mrg---result.yml',
                         count=1, timeout=10)

        self.clear_async_data()
        #self.create_sample_data_set_dir('multiple_glider_record.mrg',
        self.create_sample_data_set_dir('multiple_flord_record.mrg',
                                        TELEMETERED_TEST_DIR,
                                        "unit_363_2013_245_7_6.mrg")
        self.assert_data(FlordTelemeteredDataParticle,
                         'multiple_flord_record.mrg---result.yml',
                         count=4, timeout=10)

        self.clear_async_data()
        #self.create_sample_data_set_dir('single_glider_record.mrg',
        self.create_sample_data_set_dir('single_flord_record.mrg',
                                        RECOVERED_TEST_DIR,
                                        "unit_363_2013_245_6_6_rec.mrg")
        self.assert_data(FlordRecoveredDataParticle,
                         'single_flord_record.mrg---recovered_result.yml',
                         count=1, timeout=10)

        self.clear_async_data()
        #self.create_sample_data_set_dir('multiple_glider_record.mrg',
        self.create_sample_data_set_dir('multiple_flord_record.mrg',
                                        RECOVERED_TEST_DIR,
                                        "unit_363_2013_245_7_6.mrg")
        self.assert_data(FlordRecoveredDataParticle,
                         'multiple_flord_record.mrg---recovered_result.yml',
                         count=4, timeout=10)


        log.debug("Start second file ingestion - Telemetered")
        # Verify sort order isn't ascii, but numeric
        self.clear_async_data()
        self.create_sample_data_set_dir('unit_247_2012_051_0_0-flord.mrg',
                                        TELEMETERED_TEST_DIR,
                                        'unit_363_2013_245_10_6.mrg')
        self.assert_data(FlordTelemeteredDataParticle, count=115, timeout=30)

        log.debug("Start second file ingestion - Recovered")
        # Verify sort order isn't ascii, but numeric
        self.clear_async_data()
        self.create_sample_data_set_dir('unit_247_2012_051_0_0-flord.mrg',
                                        RECOVERED_TEST_DIR,
                                        "unit_363_2013_245_10_6.mrg")
        self.assert_data(FlordRecoveredDataParticle, count=115, timeout=30)

    ##DONE
    def test_missing_particle_parameters(self):
        """
        Test the ability of the parser to parse input files that do not contain all the data expected by the particle
        Missing parameters from the input file should have None automatically assigned as values in the particle
        """
        self.clear_sample_data()

        # Start sampling and watch for an exception
        self.driver.start_sampling()

        log.debug("IntegrationTest.test_get(): INPUT FILE MISSING 4 PARAMETERS")

        self.clear_async_data()
        self.create_sample_data_set_dir('cp_379_2014_104_18_0-ONEROW.mrg',
                                        TELEMETERED_TEST_DIR,
                                        'CopyOf-cp_379_2014_104_18_0-ONEROW.mrg')
        self.assert_data(FlordTelemeteredDataParticle,
                         'single_flord_record_missingInputData.mrg.result.yml',
                         count=1, timeout=10)

        self.clear_async_data()
        self.create_sample_data_set_dir('cp_379_2014_104_18_0-ONEROW.mrg',
                                        RECOVERED_TEST_DIR,
                                        "CopyOf-cp_379_2014_104_18_0-ONEROW.mrg")
        self.assert_data(FlordRecoveredDataParticle,
                         'single_flord_record_recovered_missingInputData.mrg.result.yml',
                         count=1, timeout=10)

    ##DONE
    def test_stop_resume(self):
        """
        Test the ability to stop and restart the process
        """
        path_1 = self.create_sample_data_set_dir('single_flord_record.mrg',
                                                 TELEMETERED_TEST_DIR,
                                                 "unit_363_2013_245_6_8.mrg")
        path_2 = self.create_sample_data_set_dir('multiple_flord_record.mrg',
                                                 TELEMETERED_TEST_DIR,
                                                 "unit_363_2013_245_6_9.mrg")
        path_3 = self.create_sample_data_set_dir('single_flord_record.mrg',
                                                 RECOVERED_TEST_DIR,
                                                 "unit_363_2013_245_6_8.mrg")
        path_4 = self.create_sample_data_set_dir('multiple_flord_record.mrg',
                                                 RECOVERED_TEST_DIR,
                                                 "unit_363_2013_245_6_9.mrg")

        # Create and store the new driver state
        state = {
            DataTypeKey.FLORD_TELEMETERED: {
            'unit_363_2013_245_6_8.mrg': self.get_file_state(path_1, True, 9217),
            'unit_363_2013_245_6_9.mrg': self.get_file_state(path_2, False, 10763)
            },
            DataTypeKey.FLORD_RECOVERED: {
            'unit_363_2013_245_6_8.mrg': self.get_file_state(path_3, True, 9217),
            'unit_363_2013_245_6_9.mrg': self.get_file_state(path_4, False, 10763)
            }
        }
        self.driver = self._get_driver_object(memento=state)

        # create some data to parse
        self.clear_async_data()

        self.driver.start_sampling()

        # verify data is produced for telemetered particle
        self.assert_data(FlordTelemeteredDataParticle, 'multiple_flord_record.mrg---rows3-4_result.yml', count=3, timeout=10)

        # verify data is produced for recovered particle
        self.assert_data(FlordRecoveredDataParticle, 'multiple_flord_record.mrg---rows3-4_recovered_result.yml', count=3, timeout=10)

    ##DONE
    def test_stop_start_ingest(self):
        """
        Test the ability to stop and restart sampling, and ingesting files in the correct order
        """
        # create some data to parse
        self.clear_async_data()

        self.driver.start_sampling()

        self.create_sample_data_set_dir('single_flord_record.mrg',
                                        TELEMETERED_TEST_DIR,
                                        "unit_363_2013_245_6_6.mrg")
        self.create_sample_data_set_dir('multiple_flord_record.mrg',
                                        TELEMETERED_TEST_DIR,
                                        "unit_363_2013_245_7_6.mrg")
        self.assert_data(FlordTelemeteredDataParticle, 'single_flord_record.mrg---result.yml', count=1, timeout=10)
        self.assert_file_ingested("unit_363_2013_245_6_6.mrg", DataTypeKey.FLORD_TELEMETERED)
        self.assert_file_not_ingested("unit_363_2013_245_7_6.mrg")

        self.driver.stop_sampling()
        self.driver.start_sampling()

        self.assert_data(FlordTelemeteredDataParticle, 'multiple_flord_record.mrg---result.yml', count=4, timeout=10)
        self.assert_file_ingested("unit_363_2013_245_7_6.mrg", DataTypeKey.FLORD_TELEMETERED)

        ####
        ## Repeat for Recovered Particle
        ####
        self.create_sample_data_set_dir('single_flord_record.mrg', RECOVERED_TEST_DIR, "unit_363_2013_245_6_6.mrg")
        self.create_sample_data_set_dir('multiple_flord_record.mrg', RECOVERED_TEST_DIR, "unit_363_2013_245_7_6.mrg")
        self.assert_data(FlordRecoveredDataParticle, 'single_flord_record.mrg---recovered_result.yml', count=1, timeout=10)
        self.assert_file_ingested("unit_363_2013_245_6_6.mrg", DataTypeKey.FLORD_RECOVERED)
        self.assert_file_not_ingested("unit_363_2013_245_7_6.mrg")

        self.driver.stop_sampling()
        self.driver.start_sampling()

        self.assert_data(FlordRecoveredDataParticle, 'multiple_flord_record.mrg---recovered_result.yml', count=4, timeout=10)
        self.assert_file_ingested("unit_363_2013_245_7_6.mrg", DataTypeKey.FLORD_RECOVERED)

    ##DONE
    def test_bad_sample(self):
        """
        Test a bad sample.  To do this we set a state to the middle of a record
        """
        path_2 = self.create_sample_data_set_dir('multiple_flord_record.mrg',
                                                 TELEMETERED_TEST_DIR, "unit_363_2013_245_6_9.mrg")
        path_4 = self.create_sample_data_set_dir('multiple_flord_record.mrg',
                                                 RECOVERED_TEST_DIR, "unit_363_2013_245_6_9.mrg")

        # Create and store the new driver state
        state = {
            DataTypeKey.FLORD_TELEMETERED: {
             'unit_363_2013_245_6_9.mrg': self.get_file_state(path_2, False, 10763)
            },
            DataTypeKey.FLORD_RECOVERED: {
            'unit_363_2013_245_6_9.mrg': self.get_file_state(path_4, False, 10763)
            }
        }
        self.driver = self._get_driver_object(memento=state)

        # create some data to parse
        self.clear_async_data()

        self.driver.start_sampling()

        # verify data is produced for telemetered particle
        self.assert_data(FlordTelemeteredDataParticle,
                         'multiple_flord_record.mrg---rows3-4_result.yml', count=3, timeout=10)

        # verify data is produced for recovered particle
        self.assert_data(FlordRecoveredDataParticle,
                         'multiple_flord_record.mrg---rows3-4_recovered_result.yml', count=3, timeout=10)

    ##DONE
    def test_sample_exception_telemetered(self):
        """
        test that a file is marked as parsed if it has a sample exception (which will happen with an empty file)
        """
        self.clear_async_data()

        config = self._driver_config()['startup_config']['harvester'][DataTypeKey.FLORD_TELEMETERED]['pattern']
        filename = config.replace("*", "foo")
        self.create_sample_data_set_dir(filename, TELEMETERED_TEST_DIR)

        # Start sampling and watch for an exception
        self.driver.start_sampling()
        # an event catches the sample exception
        self.assert_event('ResourceAgentErrorEvent')
        self.assert_file_ingested(filename, DataTypeKey.FLORD_TELEMETERED)

    ##DONE
    def test_sample_exception_recovered(self):
        """
        test that a file is marked as parsed if it has a sample exception (which will happen with an empty file)
        """
        self.clear_async_data()

        config = self._driver_config()['startup_config']['harvester'][DataTypeKey.FLORD_RECOVERED]['pattern']
        filename = config.replace("*", "foo")
        self.create_sample_data_set_dir(filename, RECOVERED_TEST_DIR)

        # Start sampling and watch for an exception
        self.driver.start_sampling()
        # an event catches the sample exception
        self.assert_event('ResourceAgentErrorEvent')
        self.assert_file_ingested(filename, DataTypeKey.FLORD_RECOVERED)

###############################################################################
#                            QUALIFICATION TESTS                              #
# Device specific qualification tests are for                                 #
# testing device specific capabilities                                        #
###############################################################################
@attr('QUAL', group='mi')
class QualificationTest(DataSetQualificationTestCase):

    def setUp(self):
        super(QualificationTest, self).setUp()

    ##DONE
    def test_publish_path(self):
        """
        Setup an agent/driver/harvester/parser and verify that data is
        published out the agent
        """
        self.create_sample_data_set_dir('single_flord_record.mrg',
                                        TELEMETERED_TEST_DIR,
                                        'unit_363_2013_245_6_9.mrg')
        self.assert_initialize()

        # Verify we get one sample
        try:
            result = self.data_subscribers.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 1)
            log.debug("Telemetered RESULT: %s", result)

            # Verify values
            self.assert_data_values(result, 'single_flord_record.mrg---result.yml')
        except Exception as e:
            log.error("Exception trapped: %s", e)
            self.fail("Sample timeout.")

        # Again for the recovered particle
        self.create_sample_data_set_dir('single_flord_record.mrg',
                                        RECOVERED_TEST_DIR,
                                        'unit_363_2013_245_6_9.mrg')

        # Verify we get one sample
        try:
            result = self.data_subscribers.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 1)
            log.debug("Recovered RESULT: %s", result)

            # Verify values
            self.assert_data_values(result, 'single_flord_record.mrg---recovered_result.yml')
        except Exception as e:
            log.error("Exception trapped: %s", e)
            self.fail("Sample timeout.")

    ##DONE
    def test_publish_path_missing_particle_parameters(self):
        """
        Setup an agent/driver/harvester/parser and verify that data is
        published out the agent
        """
        self.create_sample_data_set_dir('cp_379_2014_104_18_0-ONEROW.mrg',
                                        TELEMETERED_TEST_DIR,
                                        'unit_363_2013_245_6_9.mrg')
        self.assert_initialize()

        # Verify we get one sample
        try:
            result = self.data_subscribers.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 1)
            log.debug("Telemetered RESULT: %s", result)

            # Verify values
            self.assert_data_values(result, 'single_flord_record_missingInputData.mrg.result.yml')
            #self.assert_data_values(result, 'single_flord_record_expectingMissingInputData.mrg.result.yml')
        except Exception as e:
            log.error("Exception trapped: %s", e)
            self.fail("Sample timeout.")

        # Again for the recovered particle
        self.create_sample_data_set_dir('cp_379_2014_104_18_0-ONEROW.mrg',
                                        RECOVERED_TEST_DIR,
                                        'unit_363_2013_245_6_9.mrg')

        # Verify we get one sample
        try:
            result = self.data_subscribers.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 1)
            log.debug("Recovered RESULT: %s", result)

            # Verify values
            self.assert_data_values(result, 'single_flord_record_recovered_missingInputData.mrg.result.yml')
        except Exception as e:
            log.error("Exception trapped: %s", e)
            self.fail("Sample timeout.")

    ##DONE
    def test_large_import(self):
        """
        There is a bug when activating an instrument go_active times out and
        there was speculation this was due to blocking behavior in the agent.
        https://jira.oceanobservatories.org/tasks/browse/OOIION-1284
        """
        self.create_sample_data_set_dir('unit_247_2012_051_0_0-flord.mrg', TELEMETERED_TEST_DIR)
        self.assert_initialize()

        result1 = self.data_subscribers.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 115, 20)

        # again for recovered
        self.create_sample_data_set_dir('unit_247_2012_051_0_0-flord.mrg', RECOVERED_TEST_DIR)
        result2 = self.data_subscribers.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 115, 120)

    ##DONE
    def test_stop_start(self):
        """
        Test the agents ability to start data flowing, stop, then restart
        at the correct spot.
        """
        log.info("## ## ## CONFIG: %s", self._agent_config())
        self.create_sample_data_set_dir('single_flord_record.mrg',
                                        TELEMETERED_TEST_DIR,
                                        "unit_363_2013_245_6_6.mrg")

        self.assert_initialize(final_state=ResourceAgentState.COMMAND)

        # Slow down processing to 1 per second to give us time to stop
        self.dataset_agent_client.set_resource({DriverParameter.RECORDS_PER_SECOND: 1})
        self.assert_start_sampling()

        try:
            # Read the first file and verify the data
            result = self.data_subscribers.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT)
            log.debug("## ## ## RESULT: %s", result)

            # Verify values
            self.assert_data_values(result, 'single_flord_record.mrg---result.yml')
            self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 0)


            # Stop sampling: Telemetered
            self.create_sample_data_set_dir('multiple_flord_record.mrg',
                                            TELEMETERED_TEST_DIR,
                                            "unit_363_2013_245_7_6.mrg")
            # Now read the first three records of the second file then stop
            result = self.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 1)
            log.debug("## ## ## Got result 1 %s", result)
            self.assert_stop_sampling()
            self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 0)

            # Restart sampling and ensure we get the last 3 records of the file
            self.assert_start_sampling()
            result = self.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 3)
            log.debug("got result 2 %s", result)
            self.assert_data_values(result, 'multiple_flord_record.mrg---rows3-4_result.yml')
            self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 0)


            #Stop sampling: Recovered
            self.create_sample_data_set_dir('multiple_flord_record.mrg',
                                            RECOVERED_TEST_DIR,
                                            "unit_363_2013_245_7_6.mrg")
            # Now read the first three records of the second file then stop
            result = self.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 1)
            log.debug("got result 1 %s", result)
            self.assert_stop_sampling()
            self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 0)

            # Restart sampling and ensure we get the last 3 records of the file
            self.assert_start_sampling()
            result = self.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 3)
            log.debug("got result 2 %s", result)
            self.assert_data_values(result, 'multiple_flord_record.mrg---rows3-4_recovered_result.yml')
            self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 0)

        except SampleTimeout as e:
            log.error("Exception trapped: %s", e, exc_info=True)
            self.fail("Sample timeout.")

    ##DONE
    def test_shutdown_restart(self):
        """
        Test the agents ability to completely stop, then restart
        at the correct spot.
        """
        log.info("## ## ## CONFIG: %s", self._agent_config())
        self.create_sample_data_set_dir('single_flord_record.mrg',
                                        TELEMETERED_TEST_DIR,
                                        "unit_363_2013_245_6_6.mrg")

        self.assert_initialize(final_state=ResourceAgentState.COMMAND)

        # Slow down processing to 1 per second to give us time to stop
        self.dataset_agent_client.set_resource({DriverParameter.RECORDS_PER_SECOND: 1})
        self.assert_start_sampling()

        try:
            # Read the first file and verify the data
            result = self.data_subscribers.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT)
            log.debug("## ## ## RESULT: %s", result)

            # Verify values
            self.assert_data_values(result, 'single_flord_record.mrg---result.yml')
            self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 0)


            # Restart sampling: Telemetered
            self.create_sample_data_set_dir('multiple_flord_record.mrg',
                                            TELEMETERED_TEST_DIR,
                                            "unit_363_2013_245_7_6.mrg")
            # Now read the first three records of the second file then stop
            result = self.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 1)
            log.debug("## ## ## Got result 1 %s", result)
            self.assert_stop_sampling()
            self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 0)

            # stop the agent
            self.stop_dataset_agent_client()
            # re-start the agent
            self.init_dataset_agent_client()
            # re-initialize
            self.assert_initialize(final_state=ResourceAgentState.COMMAND)

            # Slow down processing to 1 per second to give us time to stop
            self.dataset_agent_client.set_resource({DriverParameter.RECORDS_PER_SECOND: 1})

            # Restart sampling and ensure we get the last 3 records of the file
            self.assert_start_sampling()
            result = self.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 3)
            log.debug("got result 2 %s", result)
            self.assert_data_values(result, 'multiple_flord_record.mrg---rows3-4_result.yml')
            self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 0)


            # Restart sampling: Recovered
            self.create_sample_data_set_dir('multiple_flord_record.mrg',
                                            RECOVERED_TEST_DIR,
                                            "unit_363_2013_245_7_6.mrg")
            # Now read the first three records of the second file then stop
            result = self.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 1)
            log.debug("got result 1 %s", result)
            self.assert_stop_sampling()
            self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 0)

            # stop the agent
            self.stop_dataset_agent_client()
            # re-start the agent
            self.init_dataset_agent_client()
            # re-initialize
            self.assert_initialize(final_state=ResourceAgentState.COMMAND)

            # Restart sampling and ensure we get the last 3 records of the file
            self.assert_start_sampling()
            result = self.get_samples(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 3)
            log.debug("got result 2 %s", result)
            self.assert_data_values(result, 'multiple_flord_record.mrg---rows3-4_recovered_result.yml')
            self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 0)

        except SampleTimeout as e:
            log.error("Exception trapped: %s", e, exc_info=True)
            self.fail("Sample timeout.")

    ##DONE
    def test_parser_exception(self):
        """
        Test an exception raised after the driver is started during
        record parsing.
        """
       # cause the error for telemetered
        self.clear_sample_data()
        self.create_sample_data_set_dir('non-input_file.mrg',
                                        TELEMETERED_TEST_DIR,
                                        "unit_363_2013_245_7_7.mrg")

        self.assert_initialize()

        self.event_subscribers.clear_events()
        self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT, 0)

        # Verify an event was raised and we are in our retry state
        self.assert_event_received(ResourceAgentErrorEvent, 40)
        self.assert_state_change(ResourceAgentState.STREAMING, 10)

        # # cause the same error for recovered
        self.event_subscribers.clear_events()
        self.clear_sample_data()
        self.create_sample_data_set_dir('non-input_file.mrg',
                                        RECOVERED_TEST_DIR,
                                        "unit_363_2013_245_7_8.mrg")

        self.assert_sample_queue_size(DataParticleType.FLORD_M_GLIDER_INSTRUMENT_RECOVERED, 0)

        # Verify an event was raised and we are in our retry state
        self.assert_event_received(ResourceAgentErrorEvent, 40)
        self.assert_state_change(ResourceAgentState.STREAMING, 10)