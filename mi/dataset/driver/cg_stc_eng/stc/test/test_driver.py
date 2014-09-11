"""
@package mi.dataset.driver.cg_stc_eng.stc.test.test_driver
@file marine-integrations/mi/dataset/driver/cg_stc_eng/stc/driver.py
@author Emily Hahn
@brief Test cases for cg_stc_eng_stc driver

USAGE:
 Make tests verbose and provide stdout
   * From the IDK
       $ bin/dsa/test_driver
       $ bin/dsa/test_driver -i [-t testname]
       $ bin/dsa/test_driver -q [-t testname]
"""

__author__ = 'Emily Hahn'
__license__ = 'Apache 2.0'


from nose.plugins.attrib import attr

from mi.core.log import get_logger
log = get_logger()

from mi.core.instrument.instrument_driver import DriverEvent
from mi.idk.exceptions import SampleTimeout
from mi.core.instrument.data_particle import DataParticleKey

from pyon.core.exception import Timeout
from pyon.agent.agent import ResourceAgentState
from interface.objects import ResourceAgentConnectionLostErrorEvent
from interface.objects import ResourceAgentErrorEvent

from mi.idk.dataset.unit_test import DataSetTestCase
from mi.idk.dataset.unit_test import DataSetIntegrationTestCase
from mi.idk.dataset.unit_test import DataSetQualificationTestCase
from mi.dataset.dataset_driver import \
    DataSourceConfigKey, \
    DataSetDriverConfigKeys, \
    DriverStateKey
from mi.dataset.dataset_driver import DriverParameter
from mi.dataset.driver.cg_stc_eng.stc.driver import CgStcEngStcDataSetDriver, DataTypeKey
from mi.dataset.parser.cg_stc_eng_stc import \
    CgStcEngStcParserDataParticle, \
    CgStcEngStcParserRecoveredDataParticle, \
    CgDataParticleType
from mi.dataset.parser.rte_o_dcl import \
    RteODclParserDataParticle, \
    RteODclParserRecoveredDataParticle, \
    RteDataParticleType
from mi.dataset.parser.mopak_o_dcl import \
    MopakODclAccelParserDataParticle, \
    MopakODclRateParserDataParticle, \
    MopakODclAccelParserRecoveredDataParticle, \
    MopakODclRateParserRecoveredDataParticle, \
    MopakDataParticleType, \
    StateKey, \
    MopakODclAccelParserDataParticleKey


CG_STC_ENG_TELEM_DIR = '/tmp/dsatest/cg_telem'
MOPAK_TELEM_DIR = '/tmp/dsatest/mopak_telem'
RTE_TELEM_DIR = '/tmp/dsatest/rte_telem'
CG_STC_ENG_RECOV_DIR = '/tmp/dsatest/cg_recov'
MOPAK_RECOV_DIR = '/tmp/dsatest/mopak_recov'
RTE_RECOV_DIR = '/tmp/dsatest/rte_recov'

# Fill in driver details
DataSetTestCase.initialize(
    driver_module='mi.dataset.driver.cg_stc_eng.stc.driver',
    driver_class='CgStcEngStcDataSetDriver',
    agent_resource_id='123xyz',
    agent_name='Agent007',
    agent_packet_config=CgStcEngStcDataSetDriver.stream_config(),
    startup_config={
        DataSourceConfigKey.RESOURCE_ID: 'cg_stc_eng_stc',
        DataSourceConfigKey.HARVESTER:
        {
            DataTypeKey.CG_STC_ENG_TELEM:
            {
                DataSetDriverConfigKeys.DIRECTORY: CG_STC_ENG_TELEM_DIR,
                DataSetDriverConfigKeys.PATTERN: '*.txt',
                DataSetDriverConfigKeys.FREQUENCY: 1,
            },
            DataTypeKey.MOPAK_TELEM:
            {
                DataSetDriverConfigKeys.DIRECTORY: MOPAK_TELEM_DIR,
                DataSetDriverConfigKeys.PATTERN: '*.mopak.log',
                DataSetDriverConfigKeys.FREQUENCY: 1,
            },
            DataTypeKey.RTE_TELEM:
            {
                DataSetDriverConfigKeys.DIRECTORY: RTE_TELEM_DIR,
                DataSetDriverConfigKeys.PATTERN: '*.rte.log',
                DataSetDriverConfigKeys.FREQUENCY: 1,
            },
            DataTypeKey.CG_STC_ENG_RECOV:
            {
                DataSetDriverConfigKeys.DIRECTORY: CG_STC_ENG_RECOV_DIR,
                DataSetDriverConfigKeys.PATTERN: '*.txt',
                DataSetDriverConfigKeys.FREQUENCY: 1,
            },
            DataTypeKey.MOPAK_RECOV:
            {
                DataSetDriverConfigKeys.DIRECTORY: MOPAK_RECOV_DIR,
                DataSetDriverConfigKeys.PATTERN: '*.mopak.log',
                DataSetDriverConfigKeys.FREQUENCY: 1,
            },
            DataTypeKey.RTE_RECOV:
            {
                DataSetDriverConfigKeys.DIRECTORY: RTE_RECOV_DIR,
                DataSetDriverConfigKeys.PATTERN: '*.rte.log',
                DataSetDriverConfigKeys.FREQUENCY: 1,
            },
        },
        DataSourceConfigKey.PARSER: {
            DataTypeKey.CG_STC_ENG_TELEM: {},
            DataTypeKey.MOPAK_TELEM: {},
            DataTypeKey.RTE_TELEM: {},
            DataTypeKey.CG_STC_ENG_RECOV: {},
            DataTypeKey.MOPAK_RECOV: {},
            DataTypeKey.RTE_RECOV: {}
        }
    }
)


###############################################################################
#                            INTEGRATION TESTS                                #
# Device specific integration tests are for                                   #
# testing device specific capabilities                                        #
###############################################################################

@attr('INT', group='mi')
class IntegrationTest(DataSetIntegrationTestCase):

    def test_get(self):
        """
        Test that we can get data from files for all 3 harvester / parsers.
        """
        # Start sampling and watch for an exception
        self.driver.start_sampling()

        self.clear_async_data()
        self.create_sample_data_set_dir('stc_status.txt', CG_STC_ENG_TELEM_DIR)
        self.assert_data(CgStcEngStcParserDataParticle, 'stc_first.result.yml',
                         count=1, timeout=10)

        self.create_sample_data_set_dir('stc_status.txt', CG_STC_ENG_RECOV_DIR)
        self.assert_data(CgStcEngStcParserRecoveredDataParticle, 'stc_first_recov.result.yml',
                         count=1, timeout=10)

        self.create_sample_data_set_dir('first.mopak.log', MOPAK_TELEM_DIR,
                                        "20140120_140004.mopak.log")
        self.assert_data((MopakODclAccelParserDataParticle,
                          MopakODclRateParserDataParticle),
                         'first_mopak.result.yml', count=5, timeout=10)

        self.create_sample_data_set_dir('first.mopak.log', MOPAK_RECOV_DIR,
                                        "20140120_140004.mopak.log")
        self.assert_data((MopakODclAccelParserRecoveredDataParticle,
                          MopakODclRateParserRecoveredDataParticle),
                         'first_mopak_recov.result.yml', count=5, timeout=10)

        self.create_sample_data_set_dir('first.rte.log', RTE_TELEM_DIR,
                                        "20140120_140004.rte.log")
        self.assert_data(RteODclParserDataParticle, 'first_rte.result.yml',
                         count=2, timeout=10)

        self.create_sample_data_set_dir('first.rte.log', RTE_RECOV_DIR,
                                        "20140120_140004.rte.log")
        self.assert_data(RteODclParserRecoveredDataParticle, 'first_rte_recov.result.yml',
                         count=2, timeout=10)

        self.create_sample_data_set_dir('stc_status_second.txt', CG_STC_ENG_TELEM_DIR)
        self.assert_data(CgStcEngStcParserDataParticle, 'stc_second.result.yml',
                         count=1, timeout=10)

        self.create_sample_data_set_dir('stc_status_second.txt', CG_STC_ENG_RECOV_DIR)
        self.assert_data(CgStcEngStcParserRecoveredDataParticle, 'stc_second_recov.result.yml',
                         count=1, timeout=10)

        self.create_sample_data_set_dir('second.mopak.log', MOPAK_TELEM_DIR,
                                        "20140120_150004.mopak.log")
        self.assert_data((MopakODclAccelParserDataParticle,
                          MopakODclRateParserDataParticle),
                         'second_mopak.result.yml', count=2, timeout=10)

        self.create_sample_data_set_dir('second.mopak.log', MOPAK_RECOV_DIR,
                                        "20140120_150004.mopak.log")
        self.assert_data((MopakODclAccelParserRecoveredDataParticle,
                          MopakODclRateParserRecoveredDataParticle),
                         'second_mopak_recov.result.yml', count=2, timeout=10)

        self.create_sample_data_set_dir('second.rte.log', RTE_TELEM_DIR,
                                        "20140120_150004.rte.log")
        self.assert_data(RteODclParserDataParticle, 'second_rte.result.yml',
                         count=2, timeout=10)

        self.create_sample_data_set_dir('second.rte.log', RTE_RECOV_DIR,
                                        "20140120_150004.rte.log")
        self.assert_data(RteODclParserRecoveredDataParticle, 'second_rte_recov.result.yml',
                         count=2, timeout=10)

    def test_get_any_order(self):
        """
        Test that we can get data from files for all 3 harvester / parsers by just 
        creating many files and getting results in any order.  
        """
        # Start sampling and watch for an exception
        self.driver.start_sampling()

        # put data files in the telemetered directories
        self.create_sample_data_set_dir('stc_status.txt', CG_STC_ENG_TELEM_DIR)
        self.create_sample_data_set_dir('stc_status_all.txt', CG_STC_ENG_TELEM_DIR)
        self.create_sample_data_set_dir('first_rate.mopak.log', MOPAK_TELEM_DIR,
                                        "20140313_191853.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_TELEM_DIR,
                                        "20140120_140004.rte.log")
        self.create_sample_data_set_dir('second_rate.mopak.log', MOPAK_TELEM_DIR,
                                        "20140313_201853.mopak.log")
        self.create_sample_data_set_dir('second.rte.log', RTE_TELEM_DIR,
                                        "20140120_150004.rte.log")

        # put data files in the recovered directories
        self.create_sample_data_set_dir('stc_status.txt', CG_STC_ENG_RECOV_DIR)
        self.create_sample_data_set_dir('stc_status_all.txt', CG_STC_ENG_RECOV_DIR)
        self.create_sample_data_set_dir('first_rate.mopak.log', MOPAK_RECOV_DIR,
                                        "20140313_191853.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_RECOV_DIR,
                                        "20140120_140004.rte.log")
        self.create_sample_data_set_dir('second_rate.mopak.log', MOPAK_RECOV_DIR,
                                        "20140313_201853.mopak.log")
        self.create_sample_data_set_dir('second.rte.log', RTE_RECOV_DIR,
                                        "20140120_150004.rte.log")

        # assert the results in a crazy order
        self.assert_data((MopakODclAccelParserRecoveredDataParticle,
                          MopakODclRateParserRecoveredDataParticle),
                         'first_rate_mopak_recov.result.yml', count=6, timeout=10)

        self.assert_data((MopakODclAccelParserDataParticle,
                          MopakODclRateParserDataParticle),
                         'first_rate_mopak.result.yml', count=6, timeout=10)

        self.assert_data(CgStcEngStcParserDataParticle, 'stc_first.result.yml',
                         count=1, timeout=10)

        self.assert_data(CgStcEngStcParserDataParticle, 'stc_all.result.yml',
                         count=1, timeout=10)

        self.assert_data(RteODclParserRecoveredDataParticle, 'first_rte_recov.result.yml',
                         count=2, timeout=10)

        self.assert_data(RteODclParserDataParticle, 'first_rte.result.yml',
                         count=2, timeout=10)

        self.assert_data(RteODclParserDataParticle, 'second_rte.result.yml',
                         count=2, timeout=10)

        self.assert_data((MopakODclAccelParserDataParticle,
                          MopakODclRateParserDataParticle),
                         'second_rate_mopak.result.yml', count=3, timeout=10)

        self.assert_data(CgStcEngStcParserRecoveredDataParticle, 'stc_first_recov.result.yml',
                         count=1, timeout=10)

        self.assert_data((MopakODclAccelParserRecoveredDataParticle,
                          MopakODclRateParserRecoveredDataParticle),
                         'second_rate_mopak_recov.result.yml', count=3, timeout=10)

        self.assert_data(CgStcEngStcParserRecoveredDataParticle, 'stc_all_recov.result.yml',
                         count=1, timeout=10)

        self.assert_data(RteODclParserRecoveredDataParticle, 'second_rte_recov.result.yml',
                         count=2, timeout=10)

    def test_harvester_new_file_exception(self):
        """
        Test an exception raised after the driver is started during
        the file read.  Should call the exception callback.
        """
        # Start sampling
        self.driver.start_sampling()

        # create the file so that it is unreadable
        self.create_sample_data_set_dir("20140313_191853.mopak.log", MOPAK_TELEM_DIR,
                                        create=True, mode=000)

        # watch for an exception
        self.assert_exception(IOError)
        self.clear_async_data()

        # create the file so that it is unreadable
        self.create_sample_data_set_dir("stc_status.txt", CG_STC_ENG_TELEM_DIR,
                                        create=True, mode=000)
        # watch for an exception
        self.assert_exception(IOError)
        self.clear_async_data()

        # create the file so that it is unreadable
        self.create_sample_data_set_dir("foo.rte.log", RTE_TELEM_DIR,
                                        create=True, mode=000)
        # watch for an exception
        self.assert_exception(IOError)

        # do it all again for recovered parsers just for the halibut

        # create the file so that it is unreadable
        self.create_sample_data_set_dir("20140313_191853.mopak.log", MOPAK_RECOV_DIR,
                                        create=True, mode=000)

        # watch for an exception
        self.assert_exception(IOError)
        self.clear_async_data()

        # create the file so that it is unreadable
        self.create_sample_data_set_dir("stc_status.txt", CG_STC_ENG_RECOV_DIR,
                                        create=True, mode=000)
        # watch for an exception
        self.assert_exception(IOError)
        self.clear_async_data()

        # create the file so that it is unreadable
        self.create_sample_data_set_dir("foo.rte.log", RTE_RECOV_DIR,
                                        create=True, mode=000)
        # watch for an exception
        self.assert_exception(IOError)

    def test_stop_resume(self):
        """
        Test the ability to stop and restart the driver sampling
        """
        # create some data to parse

        stc_filename_1 = 'stc_1.txt'
        stc_filename_2 = 'stc_2.txt'
        stc_filename_3 = 'stc_3.txt'
        mopak_filename_1 = '20140120_140004.mopak.log'
        mopak_filename_2 = '20140120_150004.mopak.log'
        rte_filename_1 = '20140120_140004.rte.log'
        rte_filename_2 = '20140120_150004.rte.log'

        # put files in the telemetered directories
        stc_telem_path_1 = self.create_sample_data_set_dir('stc_status.txt',
                                                           CG_STC_ENG_TELEM_DIR, stc_filename_1)
        stc_telem_path_2 = self.create_sample_data_set_dir('stc_status_second.txt',
                                                           CG_STC_ENG_TELEM_DIR, stc_filename_2)
        stc_telem_path_3 = self.create_sample_data_set_dir('stc_status_third.txt',
                                                           CG_STC_ENG_TELEM_DIR, stc_filename_3)
        mopak_telem_path_1 = self.create_sample_data_set_dir('first.mopak.log',
                                                             MOPAK_TELEM_DIR, mopak_filename_1)
        mopak_telem_path_2 = self.create_sample_data_set_dir('second.mopak.log',
                                                             MOPAK_TELEM_DIR, mopak_filename_2)
        rte_telem_path_1 = self.create_sample_data_set_dir('first.rte.log',
                                                           RTE_TELEM_DIR, rte_filename_1)
        rte_telem_path_2 = self.create_sample_data_set_dir('second_resume.rte.log',
                                                           RTE_TELEM_DIR, rte_filename_2)

        # put files in the recoverered directories
        stc_recov_path_1 = self.create_sample_data_set_dir('stc_status.txt',
                                                           CG_STC_ENG_RECOV_DIR, stc_filename_1)
        stc_recov_path_2 = self.create_sample_data_set_dir('stc_status_second.txt',
                                                           CG_STC_ENG_RECOV_DIR, stc_filename_2)
        stc_recov_path_3 = self.create_sample_data_set_dir('stc_status_third.txt',
                                                           CG_STC_ENG_RECOV_DIR, stc_filename_3)
        mopak_recov_path_1 = self.create_sample_data_set_dir('first.mopak.log',
                                                             MOPAK_RECOV_DIR, mopak_filename_1)
        mopak_recov_path_2 = self.create_sample_data_set_dir('second.mopak.log',
                                                             MOPAK_RECOV_DIR, mopak_filename_2)
        rte_recov_path_1 = self.create_sample_data_set_dir('first.rte.log',
                                                           RTE_RECOV_DIR, rte_filename_1)
        rte_recov_path_2 = self.create_sample_data_set_dir('second_resume.rte.log',
                                                           RTE_RECOV_DIR, rte_filename_2)

       # Create and store the new driver state
        state = {
            DataTypeKey.CG_STC_ENG_TELEM: {
                stc_filename_1: self.get_file_state(stc_telem_path_1, True),
                stc_filename_2: self.get_file_state(stc_telem_path_2, True),
                stc_filename_3: self.get_file_state(stc_telem_path_3, False)
            },
            DataTypeKey.MOPAK_TELEM: {
                mopak_filename_1: self.get_file_state(mopak_telem_path_1, False, 172),
                mopak_filename_2: self.get_file_state(mopak_telem_path_2, False, 0)
            },
            DataTypeKey.RTE_TELEM: {
                rte_filename_1: self.get_file_state(rte_telem_path_1, True, 549),
                rte_filename_2: self.get_file_state(rte_telem_path_2, False, 154)
            },
            DataTypeKey.CG_STC_ENG_RECOV: {
                stc_filename_1: self.get_file_state(stc_recov_path_1, True),
                stc_filename_2: self.get_file_state(stc_recov_path_2, True),
                stc_filename_3: self.get_file_state(stc_recov_path_3, False)
            },
            DataTypeKey.MOPAK_RECOV: {
                mopak_filename_1: self.get_file_state(mopak_recov_path_1, False, 172),
                mopak_filename_2: self.get_file_state(mopak_recov_path_2, False, 0)
            },
            DataTypeKey.RTE_RECOV: {
                rte_filename_1: self.get_file_state(rte_recov_path_1, True, 549),
                rte_filename_2: self.get_file_state(rte_recov_path_2, False, 154)
            }
        }

        log.debug('generated state %s', state)
        # fill in the rest of the mopak state info
        # telemered harvester/parser
        state[DataTypeKey.MOPAK_TELEM][mopak_filename_1][DriverStateKey.PARSER_STATE].update(
            {StateKey.TIMER_START: 33456})
        state[DataTypeKey.MOPAK_TELEM][mopak_filename_1][DriverStateKey.PARSER_STATE].update(
            {StateKey.TIMER_ROLLOVER: 0})
        state[DataTypeKey.MOPAK_TELEM][mopak_filename_2][DriverStateKey.PARSER_STATE].update(
            {StateKey.TIMER_START: None})
        state[DataTypeKey.MOPAK_TELEM][mopak_filename_2][DriverStateKey.PARSER_STATE].update(
            {StateKey.TIMER_ROLLOVER: 0})
        state[DataTypeKey.MOPAK_TELEM][mopak_filename_2][DriverStateKey.PARSER_STATE].update(
            {StateKey.POSITION: 0})
        # recovered harvester/parser
        state[DataTypeKey.MOPAK_RECOV][mopak_filename_1][DriverStateKey.PARSER_STATE].update(
            {StateKey.TIMER_START: 33456})
        state[DataTypeKey.MOPAK_RECOV][mopak_filename_1][DriverStateKey.PARSER_STATE].update(
            {StateKey.TIMER_ROLLOVER: 0})
        state[DataTypeKey.MOPAK_RECOV][mopak_filename_2][DriverStateKey.PARSER_STATE].update(
            {StateKey.TIMER_START: None})
        state[DataTypeKey.MOPAK_RECOV][mopak_filename_2][DriverStateKey.PARSER_STATE].update(
            {StateKey.TIMER_ROLLOVER: 0})
        state[DataTypeKey.MOPAK_RECOV][mopak_filename_2][DriverStateKey.PARSER_STATE].update(
            {StateKey.POSITION: 0})

        log.debug('generated state after fields %s', state)
        driver = self._get_driver_object(memento=state)

        driver.start_sampling()

        # verify data is produced by the telemetered harvesters/parsers
        self.assert_data((MopakODclAccelParserDataParticle,
                          MopakODclRateParserDataParticle),
                         'partial_second_mopak.result.yml', count=3, timeout=10)
        self.assert_data(RteODclParserDataParticle, 'second_resume_rte.result.yml',
                         count=2, timeout=10)
        self.assert_data(CgStcEngStcParserDataParticle, 'stc_third.result.yml',
                         count=1, timeout=10)

        # verify data is produced by the recovered harvesters/parsers
        self.assert_data((MopakODclAccelParserRecoveredDataParticle,
                          MopakODclRateParserRecoveredDataParticle),
                         count=3, timeout=10)
        self.assert_data(RteODclParserRecoveredDataParticle, count=2, timeout=10)
        self.assert_data(CgStcEngStcParserRecoveredDataParticle, count=1, timeout=10)

    def test_stop_start_resume(self):
        """
        Test the ability to stop and restart sampling, ingesting files in the
        correct order
        """
        self.driver.start_sampling()

        self.create_sample_data_set_dir('stc_status.txt', CG_STC_ENG_TELEM_DIR)
        self.create_sample_data_set_dir('stc_status_second.txt', CG_STC_ENG_TELEM_DIR)
        self.create_sample_data_set_dir('first.mopak.log', MOPAK_TELEM_DIR,
                                        "20140120_140004.mopak.log")
        self.create_sample_data_set_dir('second.mopak.log', MOPAK_TELEM_DIR,
                                        "20140120_150004.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_TELEM_DIR,
                                        "20140120_140004.rte.log")
        self.create_sample_data_set_dir('second.rte.log', RTE_TELEM_DIR,
                                        "20140120_150004.rte.log")

        self.create_sample_data_set_dir('stc_status.txt', CG_STC_ENG_RECOV_DIR)
        self.create_sample_data_set_dir('stc_status_second.txt', CG_STC_ENG_RECOV_DIR)
        self.create_sample_data_set_dir('first.mopak.log', MOPAK_RECOV_DIR,
                                        "20140120_140004.mopak.log")
        self.create_sample_data_set_dir('second.mopak.log', MOPAK_RECOV_DIR,
                                        "20140120_150004.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_RECOV_DIR,
                                        "20140120_140004.rte.log")
        self.create_sample_data_set_dir('second.rte.log', RTE_RECOV_DIR,
                                        "20140120_150004.rte.log")

        self.assert_data((MopakODclAccelParserDataParticle,
                          MopakODclRateParserDataParticle),
                         'first_mopak.result.yml', count=5, timeout=10)
        self.assert_file_ingested("20140120_140004.mopak.log", DataTypeKey.MOPAK_TELEM)
        self.assert_data(RteODclParserDataParticle, 'first_rte.result.yml',
                         count=2, timeout=10)
        self.assert_file_ingested("20140120_140004.rte.log", DataTypeKey.RTE_TELEM)
        self.assert_data(CgStcEngStcParserDataParticle, 'stc_first.result.yml',
                         count=1, timeout=10)
        self.assert_file_ingested("stc_status.txt", DataTypeKey.CG_STC_ENG_TELEM)

        self.assert_data((MopakODclAccelParserRecoveredDataParticle,
                          MopakODclRateParserRecoveredDataParticle),
                         'first_mopak_recov.result.yml', count=5, timeout=10)
        self.assert_file_ingested("20140120_140004.mopak.log", DataTypeKey.MOPAK_RECOV)
        self.assert_data(RteODclParserRecoveredDataParticle, 'first_rte_recov.result.yml',
                         count=2, timeout=10)
        self.assert_file_ingested("20140120_140004.rte.log", DataTypeKey.RTE_RECOV)
        self.assert_data(CgStcEngStcParserRecoveredDataParticle, 'stc_first_recov.result.yml',
                         count=1, timeout=10)
        self.assert_file_ingested("stc_status.txt", DataTypeKey.CG_STC_ENG_RECOV)

        self.driver.stop_sampling()
        self.driver.start_sampling()

        self.assert_data((MopakODclAccelParserDataParticle,
                          MopakODclRateParserDataParticle),
                         'second_mopak.result.yml', count=2, timeout=10)
        self.assert_file_ingested("20140120_150004.mopak.log", DataTypeKey.MOPAK_TELEM)
        self.assert_data(RteODclParserDataParticle, 'second_rte.result.yml',
                         count=2, timeout=10)
        self.assert_file_ingested("20140120_150004.rte.log", DataTypeKey.RTE_TELEM)
        self.assert_data(CgStcEngStcParserDataParticle, 'stc_second.result.yml',
                         count=1, timeout=10)
        self.assert_file_ingested("stc_status_second.txt", DataTypeKey.CG_STC_ENG_TELEM)

        self.assert_data((MopakODclAccelParserRecoveredDataParticle,
                          MopakODclRateParserRecoveredDataParticle),
                         'second_mopak_recov.result.yml', count=2, timeout=10)
        self.assert_file_ingested("20140120_150004.mopak.log", DataTypeKey.MOPAK_RECOV)
        self.assert_data(RteODclParserRecoveredDataParticle, 'second_rte_recov.result.yml',
                         count=2, timeout=10)
        self.assert_file_ingested("20140120_150004.rte.log", DataTypeKey.RTE_RECOV)
        self.assert_data(CgStcEngStcParserRecoveredDataParticle, 'stc_second_recov.result.yml',
                         count=1, timeout=10)
        self.assert_file_ingested("stc_status_second.txt", DataTypeKey.CG_STC_ENG_RECOV)

    def test_sample_exception_mopak(self):
        """
        Test that the mopak produces a sample exception with noisy data and confirm the
        sample exception occurs
        """
        self.create_sample_data_set_dir('noise.mopak.log', MOPAK_TELEM_DIR,
                                        "20140120_140004.mopak.log")

        # Start sampling and watch for an exception
        self.driver.start_sampling()
        self.assert_data((MopakODclAccelParserDataParticle,
                          MopakODclRateParserDataParticle),
                         'first_mopak.result.yml', count=5, timeout=10)
        self.assert_event('ResourceAgentErrorEvent')
        self.assert_file_ingested("20140120_140004.mopak.log", DataTypeKey.MOPAK_TELEM)

    def test_sample_exception_eng(self):
        """
        Test that the stc eng procuces a sample exception when the time is missing and 
        confirm the sample exception occurs
        """
        self.create_sample_data_set_dir('stc_status_missing_time.txt', CG_STC_ENG_TELEM_DIR)

        # Start sampling and watch for an exception
        self.driver.start_sampling()
        # an event catches the sample exception
        self.assert_event('ResourceAgentErrorEvent')
        self.assert_file_ingested('stc_status_missing_time.txt', DataTypeKey.CG_STC_ENG_TELEM)

    def test_encoding_exception(self):
        self.create_sample_data_set_dir('stc_status_bad_encode.txt', CG_STC_ENG_TELEM_DIR)

        # Start sampling and watch for an exception
        self.driver.start_sampling()

        # assert that the exception callback received a sample encoding exception
        self.assert_data(CgStcEngStcParserDataParticle, 'stc_bad_encode.result.yml',
                         count=1, timeout=10)
        self.assert_event('ResourceAgentErrorEvent')
        self.assert_file_ingested('stc_status_bad_encode.txt', DataTypeKey.CG_STC_ENG_TELEM)

    def test_mopak_unexpected(self):
        self.create_sample_data_set_dir('20131209_103919.3dmgx3.log', MOPAK_TELEM_DIR,
                                        "20131209_103919.mopak.log")

        # Start sampling and watch for an exception
        self.driver.start_sampling()

        self.assert_data((MopakODclAccelParserDataParticle,
                          MopakODclRateParserDataParticle), None,
                         count=2857, timeout=100)

    def test_bad_checksum(self):
        """
        Assert we skip samples with bad checksums
        """
        self.create_sample_data_set_dir('20140313_191853_bad_chksum.3dmgx3.log', MOPAK_TELEM_DIR,
                                        "20140313_191853.mopak.log")
        # Start sampling
        self.driver.start_sampling()
        # assert we get 5 samples then the file is ingested
        self.assert_data((MopakODclAccelParserDataParticle,
                          MopakODclRateParserDataParticle), None, count=5)
        self.assert_file_ingested('20140313_191853.mopak.log', DataTypeKey.MOPAK_TELEM)

    def test_mopak_timer_reset(self):
        """
        test that we get the sample exception for the mopak timer resetting
        """
        self.create_sample_data_set_dir('20140313_191853_timer_reset.3dmgx3.log', MOPAK_TELEM_DIR,
                                        "20140313_191853.mopak.log")
        # Start sampling
        self.driver.start_sampling()
        # assert we get the sample exception for the timer resetting
        self.assert_event('ResourceAgentErrorEvent')

    def test_mopak_timer_rollover(self):
        """
        confirm mopak times are increasing when expected, then rollover and confirm the timer
        resets and the timestamp keeps increasing
        """
        self.create_sample_data_set_dir('20140313_191853_rollover.3dmgx3.log', MOPAK_TELEM_DIR,
                                        "20140313_191853.mopak.log")
        # Start sampling
        self.driver.start_sampling()
        try:
            particles = self.get_samples((MopakODclAccelParserDataParticle,
                                          MopakODclRateParserDataParticle), 7, 10)
        except Timeout:
            log.error("Failed to detect particle %s, expected %d particles",
                      (MopakODclAccelParserDataParticle, MopakODclRateParserDataParticle), 7)
            self.fail("particle detection failed. Expected %d", 7)

        # expect particle increase for 5 samples, then rollover
        last_timer = 0
        last_timestamp = 0.0
        for i in range(0, 4):
            (particle_timer, particle_timestamp) = self.get_mopak_particle_time(particles[i])
            if particle_timer is None or particle_timestamp is None:
                log.warn("unable to find timer or timestamp for particle %d", i)
                self.fail("Unable to find timer or timestamp for particle %d", i)

            if particle_timer < last_timer:
                log.warn("Timer did not increase when expected")
                self.fail("Timer did not increase when expected")
            if particle_timestamp < last_timestamp:
                log.warn("Timestamp did not increase when expected")
                self.fail("Timestamp did not increase when expected")
            last_timer = particle_timer
            last_timestamp = particle_timestamp

        (particle_timer, particle_timestamp) = self.get_mopak_particle_time(particles[5])
        if particle_timer is None or particle_timestamp is None:
            log.warn("unable to find timer or timestamp for particle 5")
            self.fail("Unable to find timer or timestamp for particle 5")
        # now check that we rolled over
        if particle_timer >= last_timer:
            log.warn("Timer did not rollover when expected, last timer %d, particle timer %d",
                     last_timer, particle_timer)
            self.fail("Timer did not rollover when expected")
        if particle_timestamp < last_timestamp:
            log.warn("Timestamp did not increase on rollover when expected, particle_timestamp %f, last timestamp %f",
                     particle_timestamp, last_timestamp)
            self.fail("Timestamp did not increase on rollover when expected")
        last_timer = particle_timer
        last_timestamp = particle_timestamp

        (particle_timer, particle_timestamp) = self.get_mopak_particle_time(particles[6])
        if particle_timer < last_timer:
            log.warn("Timer did not increase when expected")
            self.fail("Timer did not increase when expected")
        if particle_timestamp < last_timestamp:
            log.warn("Timestamp did not increase when expected")
            self.fail("Timestamp did not increase when expected")

    def get_mopak_particle_time(self, particle):
        """
        Get the internal timestamp and the value of the mopak timer field from a mopak particle
        @param single particle to obtain the timestamp and timer from
        @returns tuple of particle timer and internal timestamp
        """
        particle_timer = (None, None)
        internal_timestamp = particle.get_value(DataParticleKey.INTERNAL_TIMESTAMP)
        particle_dict = particle.generate_dict()
        particle_vals = particle_dict.get('values')
        for val in particle_vals:
            # this will catch both rate and accel timers since the key has the same text string
            if val.get(DataParticleKey.VALUE_ID) == MopakODclAccelParserDataParticleKey.MOPAK_TIMER:
                particle_timer = val.get(DataParticleKey.VALUE)
        return particle_timer, internal_timestamp

    def test_partial_config(self):
        """
        test with only cg_stc_eng and rte configured
        """
        partial_config = {
            DataSourceConfigKey.RESOURCE_ID: 'cg_stc_eng_stc',
            DataSourceConfigKey.HARVESTER:
            {
                DataTypeKey.CG_STC_ENG_TELEM:
                {
                    DataSetDriverConfigKeys.DIRECTORY: CG_STC_ENG_TELEM_DIR,
                    DataSetDriverConfigKeys.PATTERN: '*.txt',
                    DataSetDriverConfigKeys.FREQUENCY: 1,
                },
                DataTypeKey.RTE_TELEM:
                {
                    DataSetDriverConfigKeys.DIRECTORY: RTE_TELEM_DIR,
                    DataSetDriverConfigKeys.PATTERN: '*.rte.log',
                    DataSetDriverConfigKeys.FREQUENCY: 1,
                }
            },
            DataSourceConfigKey.PARSER: {
                DataTypeKey.CG_STC_ENG_TELEM: {},
                DataTypeKey.RTE_TELEM: {},
            }
        }
        self.driver = self._get_driver_object(config=partial_config)
        # Start sampling and watch for an exception
        self.driver.start_sampling()

        self.create_sample_data_set_dir('stc_status.txt', CG_STC_ENG_TELEM_DIR)
        self.create_sample_data_set_dir('stc_status_all.txt', CG_STC_ENG_TELEM_DIR)
        self.create_sample_data_set_dir('first_rate.mopak.log', MOPAK_TELEM_DIR,
                                        "20140313_191853.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_TELEM_DIR,
                                        "20140120_140004.rte.log")
        self.create_sample_data_set_dir('second_rate.mopak.log', MOPAK_TELEM_DIR,
                                        "20140313_201853.mopak.log")
        self.create_sample_data_set_dir('second.rte.log', RTE_TELEM_DIR,
                                        "20140120_150004.rte.log")

        self.assert_data(CgStcEngStcParserDataParticle, 'stc_first.result.yml',
                         count=1, timeout=10)
        self.assert_data(CgStcEngStcParserDataParticle, 'stc_all.result.yml',
                         count=1, timeout=10)
        self.assert_data(RteODclParserDataParticle, 'first_rte.result.yml',
                         count=2, timeout=10)
        self.assert_data(RteODclParserDataParticle, 'second_rte.result.yml',
                         count=2, timeout=10)

    def test_single_config(self):
        """
        test with only cg_stc_eng configured
        """
        partial_config = {
            DataSourceConfigKey.RESOURCE_ID: 'cg_stc_eng_stc',
            DataSourceConfigKey.HARVESTER:
            {
                DataTypeKey.CG_STC_ENG_TELEM:
                {
                    DataSetDriverConfigKeys.DIRECTORY: CG_STC_ENG_TELEM_DIR,
                    DataSetDriverConfigKeys.PATTERN: '*.txt',
                    DataSetDriverConfigKeys.FREQUENCY: 1,
                }
            },
            DataSourceConfigKey.PARSER: {
                DataTypeKey.CG_STC_ENG_TELEM: {}
            }
        }
        self.driver = self._get_driver_object(config=partial_config)
        # Start sampling and watch for an exception
        self.driver.start_sampling()

        self.create_sample_data_set_dir('stc_status.txt', CG_STC_ENG_TELEM_DIR)
        self.create_sample_data_set_dir('stc_status_all.txt', CG_STC_ENG_TELEM_DIR)
        self.create_sample_data_set_dir('first_rate.mopak.log', MOPAK_TELEM_DIR,
                                        "20140313_191853.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_TELEM_DIR,
                                        "20140120_140004.rte.log")
        self.create_sample_data_set_dir('second_rate.mopak.log', MOPAK_TELEM_DIR,
                                        "20140313_201853.mopak.log")
        self.create_sample_data_set_dir('second.rte.log', RTE_TELEM_DIR,
                                        "20140120_150004.rte.log")

        self.assert_data(CgStcEngStcParserDataParticle, 'stc_first.result.yml',
                         count=1, timeout=10)
        self.assert_data(CgStcEngStcParserDataParticle, 'stc_all.result.yml',
                         count=1, timeout=10)

###############################################################################
#                            QUALIFICATION TESTS                              #
# Device specific qualification tests are for                                 #
# testing device specific capabilities                                        #
###############################################################################


@attr('QUAL', group='mi')
class QualificationTest(DataSetQualificationTestCase):

    def test_publish_path(self):
        """
        Setup an agent/driver/harvester/parser and verify that data is
        published out the agent
        """
        self.create_sample_data_set_dir('stc_status.txt', CG_STC_ENG_TELEM_DIR)
        self.create_sample_data_set_dir('first.mopak.log', MOPAK_TELEM_DIR,
                                        "20140120_140004.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_TELEM_DIR,
                                        "20140120_140004.rte.log")

        self.create_sample_data_set_dir('stc_status.txt', CG_STC_ENG_RECOV_DIR)
        self.create_sample_data_set_dir('first.mopak.log', MOPAK_RECOV_DIR,
                                        "20140120_140004.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_RECOV_DIR,
                                        "20140120_140004.rte.log")

        self.assert_initialize()

        # Verify we get one sample
        try:
            result_cg = self.data_subscribers.get_samples(CgDataParticleType.TELEMETERED, 1)
            result_mopak = self.data_subscribers.get_samples(MopakDataParticleType.ACCEL_TELEM, 5)
            result_rte = self.data_subscribers.get_samples(RteDataParticleType.INSTRUMENT, 2)
            log.debug("RESULT cg: %s", result_cg)
            log.debug("RESULT mopak: %s", result_mopak)
            log.debug("RESULT rte: %s", result_rte)

            # Verify values
            self.assert_data_values(result_cg, 'stc_first.result.yml')
            self.assert_data_values(result_mopak, 'first_mopak.result.yml')
            self.assert_data_values(result_rte, 'first_rte.result.yml')

            result_cg = self.data_subscribers.get_samples(CgDataParticleType.RECOVERED, 1)
            result_mopak = self.data_subscribers.get_samples(MopakDataParticleType.ACCEL_RECOV, 5)
            result_rte = self.data_subscribers.get_samples(RteDataParticleType.RECOVERED, 2)
            log.debug("RESULT cg: %s", result_cg)
            log.debug("RESULT mopak: %s", result_mopak)
            log.debug("RESULT rte: %s", result_rte)

            # Verify values
            self.assert_data_values(result_cg, 'stc_first_recov.result.yml')
            self.assert_data_values(result_mopak, 'first_mopak_recov.result.yml')
            self.assert_data_values(result_rte, 'first_rte_recov.result.yml')

        except Exception as e:
            log.error("Exception trapped: %s", e)
            self.fail("Sample timeout.")

    def test_harvester_new_file_exception(self):
        """
        Test an exception raised after the driver is started during
        the file read.
        need to override this from base unit test class to test each file type
        exception callback called.
        """
        filename = "20140313_191853.mopak.log"
        self.assert_new_file_exception(filename, MOPAK_TELEM_DIR)

        filename = "foo.rte.log"
        self.assert_new_file_exception(filename, RTE_TELEM_DIR)

        filename = "foo.txt"
        self.assert_new_file_exception(filename, CG_STC_ENG_TELEM_DIR)

        filename = "20140313_191853.mopak.log"
        self.assert_new_file_exception(filename, MOPAK_RECOV_DIR)

        filename = "foo.rte.log"
        self.assert_new_file_exception(filename, RTE_RECOV_DIR)

        filename = "foo.txt"
        self.assert_new_file_exception(filename, CG_STC_ENG_RECOV_DIR)

    def assert_new_file_exception(self, filename, path):
        """
        assert that an exception occurs and we recover from a new un-readable file 
        """
        self.clear_sample_data()
        self.create_sample_data_set_dir(filename, path, mode=000)

        state = self.dataset_agent_client.get_agent_state()
        if state == ResourceAgentState.STREAMING:
            # stop sampling to go into command state
            self.assert_stop_sampling()
        elif state != ResourceAgentState.COMMAND:
            # we are not in stream or command, initialize
            self.assert_initialize(final_state=ResourceAgentState.COMMAND)

        self.event_subscribers.clear_events()
        self.assert_resource_command(DriverEvent.START_AUTOSAMPLE)
        self.assert_state_change(ResourceAgentState.LOST_CONNECTION, 90)
        self.assert_event_received(ResourceAgentConnectionLostErrorEvent, 10)

        self.clear_sample_data()
        self.create_sample_data_set_dir(filename, path)

        # Should automatically retry connect and transition to streaming
        self.assert_state_change(ResourceAgentState.STREAMING, 90)

    def test_large_import(self):
        """
        Test importing a large number of samples from the file at once
        (only possible with mopak and rte, since cg_stc_eng is 1 sample per file)
        """
        self.create_sample_data_set_dir('20140120_140004.mopak.log', MOPAK_TELEM_DIR)
        self.create_sample_data_set_dir('20131115.rte.log', RTE_TELEM_DIR)
        
        self.create_sample_data_set_dir('20140120_140004.mopak.log', MOPAK_RECOV_DIR)
        self.create_sample_data_set_dir('20131115.rte.log', RTE_RECOV_DIR)

        self.assert_initialize()

        # get results for each of the data particle streams
        self.get_samples(RteDataParticleType.INSTRUMENT, 23, 10)
        self.get_samples(MopakDataParticleType.ACCEL_RECOV, 2000, 180)
        # was 11964 samples
        self.get_samples(RteDataParticleType.RECOVERED, 23, 10)
        self.get_samples(MopakDataParticleType.ACCEL_RECOV, 2000, 180)

    def test_stop_start(self):
        """
        Test the agents ability to start data flowing, stop, then restart
        at the correct spot.

        Only test MOPAK and RTE, CG_STC files only have on record per file
        """

        log.info("CONFIG: %s", self._agent_config())
        self.create_sample_data_set_dir('first_rate.mopak.log', MOPAK_TELEM_DIR,
                                        "20140313_191853.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_TELEM_DIR,
                                        "20140120_140004.rte.log")

        self.create_sample_data_set_dir('first_rate.mopak.log', MOPAK_RECOV_DIR,
                                        "20140313_191853.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_RECOV_DIR,
                                        "20140120_140004.rte.log")

        self.assert_initialize(final_state=ResourceAgentState.COMMAND)

        # Slow down processing to 1 per second to give us time to stop
        self.dataset_agent_client.set_resource({DriverParameter.RECORDS_PER_SECOND: 1})
        self.assert_start_sampling()

        try:
            # Read the first file and verify the data
            result_mopak = self.get_samples(MopakDataParticleType.ACCEL_TELEM, 2)
            result2_mopak = self.get_samples(MopakDataParticleType.RATE_TELEM, 4)
            result_mopak.extend(result2_mopak)
            log.debug("RESULT MOPAK: %s", result_mopak)

            # Verify mopak telemetered values
            self.assert_data_values(result_mopak, 'first_rate_mopak.result.yml')
            self.assert_sample_queue_size(MopakDataParticleType.ACCEL_TELEM, 0)
            self.assert_sample_queue_size(MopakDataParticleType.RATE_TELEM, 0)

            result_mopak = self.get_samples(MopakDataParticleType.ACCEL_RECOV, 2)
            result2_mopak = self.get_samples(MopakDataParticleType.RATE_RECOV, 4)
            result_mopak.extend(result2_mopak)
            log.debug("RESULT MOPAK: %s", result_mopak)

            # Verify mopak recovered values
            self.assert_data_values(result_mopak, 'first_rate_mopak_recov.result.yml')
            self.assert_sample_queue_size(MopakDataParticleType.ACCEL_RECOV, 0)
            self.assert_sample_queue_size(MopakDataParticleType.RATE_RECOV, 0)

            self.create_sample_data_set_dir('second_rate.mopak.log', MOPAK_TELEM_DIR,
                                            "20140313_201853.mopak.log")

            self.create_sample_data_set_dir('second_rate.mopak.log', MOPAK_RECOV_DIR,
                                            "20140313_201853.mopak.log")

            # verify rte telemetered values
            result_rte = self.get_samples(RteDataParticleType.INSTRUMENT, 2)
            self.assert_data_values(result_rte, 'first_rte.result.yml')
            self.assert_sample_queue_size(RteDataParticleType.INSTRUMENT, 0)

            # verify rte recovered values
            result_rte = self.get_samples(RteDataParticleType.RECOVERED, 2)
            self.assert_data_values(result_rte, 'first_rte_recov.result.yml')
            self.assert_sample_queue_size(RteDataParticleType.RECOVERED, 0)

            #create new rte files
            self.create_sample_data_set_dir('four_samp.rte.log', RTE_TELEM_DIR,
                                            "20140120.rte.log")

            self.create_sample_data_set_dir('four_samp.rte.log', RTE_RECOV_DIR,
                                            "20140120.rte.log")

            # Now read the first records of the second mopak telem file then stop in the middle
            result_mopak_telem = self.get_samples(MopakDataParticleType.RATE_TELEM, 1)
            log.debug("got result 1 mopak %s", result_mopak)

            # Then read the first records of the second rte telem file and stop in the middle
            # need unique results for telemetered and recovered because they are extended later
            result_rte_telem = self.get_samples(RteDataParticleType.INSTRUMENT, 2)
            log.debug("got result 1 rte %s", result_rte)

            # Now read the first records of the second mopak recov file then stop in the middle
            result_mopak_recov = self.get_samples(MopakDataParticleType.RATE_RECOV, 1)
            log.debug("got result 1 mopak %s", result_mopak)

            # Then read the first records of the second rte recov file and stop in the middle
            result_rte_recov = self.get_samples(RteDataParticleType.RECOVERED, 2)
            log.debug("got result 1 rte %s", result_rte)

            # stop sample
            self.assert_stop_sampling()
            # Restart sampling and ensure we get the last records of the file
            self.assert_start_sampling()

            # get the second half of mopak telem and verify
            result2_mopak = self.get_samples(MopakDataParticleType.RATE_TELEM, 2)
            log.debug("got result 2 mopak %s", result2_mopak)
            result_mopak_telem.extend(result2_mopak)
            self.assert_data_values(result_mopak_telem, 'second_rate_mopak.result.yml')
            self.assert_sample_queue_size(MopakDataParticleType.ACCEL_TELEM, 0)
            self.assert_sample_queue_size(MopakDataParticleType.RATE_TELEM, 0)

            # get the second half of rte telem and verify
            result2_rte = self.get_samples(RteDataParticleType.INSTRUMENT, 2)
            log.debug("got result 2 rte %s", result2_rte)
            result_rte_telem.extend(result2_rte)
            self.assert_data_values(result_rte_telem, 'four_samp_rte.result.yml')
            self.assert_sample_queue_size(RteDataParticleType.INSTRUMENT, 0)

            # get the second half of rte recov and verify
            result2_rte = self.get_samples(RteDataParticleType.RECOVERED, 2)
            log.debug("got result 2 rte %s", result2_rte)
            result_rte_recov.extend(result2_rte)
            self.assert_data_values(result_rte_recov, 'four_samp_rte_recov.result.yml')
            self.assert_sample_queue_size(RteDataParticleType.RECOVERED, 0)

            # get the second half of mopak recov and verify
            result2_mopak = self.get_samples(MopakDataParticleType.RATE_RECOV, 2)
            log.debug("got result 2 mopak %s", result2_mopak)
            result_mopak_recov.extend(result2_mopak)
            self.assert_data_values(result_mopak_recov, 'second_rate_mopak_recov.result.yml')
            self.assert_sample_queue_size(MopakDataParticleType.ACCEL_RECOV, 0)
            self.assert_sample_queue_size(MopakDataParticleType.RATE_RECOV, 0)

        except SampleTimeout as e:
            log.error("Exception trapped: %s", e, exc_info=True)
            self.fail("Sample timeout.")

    def test_shutdown_restart(self):
        """
        Test a full stop of the dataset agent, then restart the agent 
        and confirm it restarts at the correct spot.
        """
        log.info("CONFIG: %s", self._agent_config())
        self.create_sample_data_set_dir('first_rate.mopak.log', MOPAK_TELEM_DIR,
                                        "20140313_191853.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_TELEM_DIR,
                                        "20140120_140004.rte.log")

        self.create_sample_data_set_dir('first_rate.mopak.log', MOPAK_RECOV_DIR,
                                        "20140313_191853.mopak.log")
        self.create_sample_data_set_dir('first.rte.log', RTE_RECOV_DIR,
                                        "20140120_140004.rte.log")

        self.assert_initialize(final_state=ResourceAgentState.COMMAND)

        # Slow down processing to 1 per second to give us time to stop
        self.dataset_agent_client.set_resource({DriverParameter.RECORDS_PER_SECOND: 1})
        self.assert_start_sampling()

        try:
            # Read the first file and verify the data
            result_mopak = self.get_samples(MopakDataParticleType.ACCEL_TELEM, 2)
            result2_mopak = self.get_samples(MopakDataParticleType.RATE_TELEM, 4)
            result_mopak.extend(result2_mopak)
            log.debug("RESULT MOPAK: %s", result_mopak)

            # Verify mopak telemetered values
            self.assert_data_values(result_mopak, 'first_rate_mopak.result.yml')
            self.assert_sample_queue_size(MopakDataParticleType.ACCEL_TELEM, 0)
            self.assert_sample_queue_size(MopakDataParticleType.RATE_TELEM, 0)

            result_mopak = self.get_samples(MopakDataParticleType.ACCEL_RECOV, 2)
            result2_mopak = self.get_samples(MopakDataParticleType.RATE_RECOV, 4)
            result_mopak.extend(result2_mopak)
            log.debug("RESULT MOPAK: %s", result_mopak)

            # Verify mopak recovered values
            self.assert_data_values(result_mopak, 'first_rate_mopak_recov.result.yml')
            self.assert_sample_queue_size(MopakDataParticleType.ACCEL_RECOV, 0)
            self.assert_sample_queue_size(MopakDataParticleType.RATE_RECOV, 0)

            self.create_sample_data_set_dir('second_rate.mopak.log', MOPAK_TELEM_DIR,
                                            "20140313_201853.mopak.log")

            self.create_sample_data_set_dir('second_rate.mopak.log', MOPAK_RECOV_DIR,
                                            "20140313_201853.mopak.log")

            # verify rte telemetered values
            result_rte = self.get_samples(RteDataParticleType.INSTRUMENT, 2)
            self.assert_data_values(result_rte, 'first_rte.result.yml')
            self.assert_sample_queue_size(RteDataParticleType.INSTRUMENT, 0)

            # verify rte recovered values
            result_rte = self.get_samples(RteDataParticleType.RECOVERED, 2)
            self.assert_data_values(result_rte, 'first_rte_recov.result.yml')
            self.assert_sample_queue_size(RteDataParticleType.RECOVERED, 0)

            #create new rte files
            self.create_sample_data_set_dir('four_samp.rte.log', RTE_TELEM_DIR,
                                            "20140120.rte.log")

            self.create_sample_data_set_dir('four_samp.rte.log', RTE_RECOV_DIR,
                                            "20140120.rte.log")

            # Now read the first records of the second mopak telem file then stop in the middle
            result_mopak_telem = self.get_samples(MopakDataParticleType.RATE_TELEM, 1)
            log.debug("got result 1 mopak %s", result_mopak)

            # Then read the first records of the second rte telem file and stop in the middle
            # need unique results for telemetered and recovered because they are extended later
            result_rte_telem = self.get_samples(RteDataParticleType.INSTRUMENT, 2)
            log.debug("got result 1 rte %s", result_rte)

            # Now read the first records of the second mopak recov file then stop in the middle
            result_mopak_recov = self.get_samples(MopakDataParticleType.RATE_RECOV, 1)
            log.debug("got result 1 mopak %s", result_mopak)

            # Then read the first records of the second rte recov file and stop in the middle
            result_rte_recov = self.get_samples(RteDataParticleType.RECOVERED, 2)
            log.debug("got result 1 rte %s", result_rte)

            self.assert_stop_sampling()
            # stop the agent
            self.stop_dataset_agent_client()
            # re-start the agent
            self.init_dataset_agent_client()
            #re-initialize
            self.assert_initialize(final_state=ResourceAgentState.COMMAND)
            # Restart sampling and ensure we get the last records of the file
            self.assert_start_sampling()

            # get the second half of mopak telem and verify
            result2_mopak = self.get_samples(MopakDataParticleType.RATE_TELEM, 2)
            log.debug("got result 2 mopak %s", result2_mopak)
            result_mopak_telem.extend(result2_mopak)
            self.assert_data_values(result_mopak_telem, 'second_rate_mopak.result.yml')
            self.assert_sample_queue_size(MopakDataParticleType.ACCEL_TELEM, 0)
            self.assert_sample_queue_size(MopakDataParticleType.RATE_TELEM, 0)

            # get the second half of rte telem and verify
            result2_rte = self.get_samples(RteDataParticleType.INSTRUMENT, 2)
            log.debug("got result 2 rte %s", result2_rte)
            result_rte_telem.extend(result2_rte)
            self.assert_data_values(result_rte_telem, 'four_samp_rte.result.yml')
            self.assert_sample_queue_size(RteDataParticleType.INSTRUMENT, 0)

            # get the second half of rte recov and verify
            result2_rte = self.get_samples(RteDataParticleType.RECOVERED, 2)
            log.debug("got result 2 rte %s", result2_rte)
            result_rte_recov.extend(result2_rte)
            self.assert_data_values(result_rte_recov, 'four_samp_rte_recov.result.yml')
            self.assert_sample_queue_size(RteDataParticleType.RECOVERED, 0)

            # get the second half of mopak recov and verify
            result2_mopak = self.get_samples(MopakDataParticleType.RATE_RECOV, 2)
            log.debug("got result 2 mopak %s", result2_mopak)
            result_mopak_recov.extend(result2_mopak)
            self.assert_data_values(result_mopak_recov, 'second_rate_mopak_recov.result.yml')
            self.assert_sample_queue_size(MopakDataParticleType.ACCEL_RECOV, 0)
            self.assert_sample_queue_size(MopakDataParticleType.RATE_RECOV, 0)

        except SampleTimeout as e:
            log.error("Exception trapped: %s", e, exc_info=True)
            self.fail("Sample timeout.")

    def test_parser_exception_mopak(self):
        """
        Test an exception is raised after the driver is started during
        record parsing.
        """
        # file contains invalid sample values
        self.create_sample_data_set_dir('noise.mopak.log', MOPAK_TELEM_DIR,
                                        "20140120_140004.mopak.log")

        self.create_sample_data_set_dir('noise.mopak.log', MOPAK_RECOV_DIR,
                                        "20140120_140004.mopak.log")

        self.assert_initialize()

        self.event_subscribers.clear_events()
        result = self.get_samples(MopakDataParticleType.ACCEL_TELEM, 5)
        self.assert_data_values(result, 'first_mopak.result.yml')
        self.assert_sample_queue_size(MopakDataParticleType.ACCEL_TELEM, 0)

        # Verify an event was raised and we are in our retry state
        self.assert_event_received(ResourceAgentErrorEvent, 10)
        self.assert_state_change(ResourceAgentState.STREAMING, 10)

        self.event_subscribers.clear_events()
        result = self.get_samples(MopakDataParticleType.ACCEL_RECOV, 5)
        self.assert_data_values(result, 'first_mopak_recov.result.yml')
        self.assert_sample_queue_size(MopakDataParticleType.ACCEL_RECOV, 0)

        # Verify an event was raised and we are in our retry state
        self.assert_event_received(ResourceAgentErrorEvent, 10)
        self.assert_state_change(ResourceAgentState.STREAMING, 10)

    def test_parser_sample_exception_stc(self):
        """
        Test an exception is raised after the driver is started during
        record parsing.
        """
        # file contains invalid sample values
        self.create_sample_data_set_dir('stc_status_missing_time.txt', CG_STC_ENG_TELEM_DIR)
        self.create_sample_data_set_dir('stc_status_missing_time.txt', CG_STC_ENG_RECOV_DIR)

        self.assert_initialize()

        self.event_subscribers.clear_events()
        self.assert_sample_queue_size(CgDataParticleType.TELEMETERED, 0)

        # Verify an event was raised and we are in our retry state
        self.assert_event_received(ResourceAgentErrorEvent, 10)
        self.assert_state_change(ResourceAgentState.STREAMING, 10)

        self.event_subscribers.clear_events()
        self.assert_sample_queue_size(CgDataParticleType.RECOVERED, 0)

        # Verify an event was raised and we are in our retry state
        self.assert_event_received(ResourceAgentErrorEvent, 10)
        self.assert_state_change(ResourceAgentState.STREAMING, 10)

    def test_parser_exception_stc(self):
        """
        Test an exception is raised after the driver is started during
        record parsing.
        """
        # file contains invalid sample values
        self.create_sample_data_set_dir('stc_status_bad_encode.txt', CG_STC_ENG_TELEM_DIR)
        self.create_sample_data_set_dir('stc_status_bad_encode.txt', CG_STC_ENG_RECOV_DIR)

        self.assert_initialize()

        self.event_subscribers.clear_events()
        result = self.get_samples(CgDataParticleType.TELEMETERED, 1)
        self.assert_data_values(result, 'stc_bad_encode.result.yml')
        self.assert_sample_queue_size(CgDataParticleType.TELEMETERED, 0)

        # Verify an event was raised and we are in our retry state
        self.assert_event_received(ResourceAgentErrorEvent, 10)
        self.assert_state_change(ResourceAgentState.STREAMING, 10)

        self.event_subscribers.clear_events()
        result = self.get_samples(CgDataParticleType.RECOVERED, 1)
        self.assert_data_values(result, 'stc_bad_encode_recov.result.yml')
        self.assert_sample_queue_size(CgDataParticleType.RECOVERED, 0)

        # Verify an event was raised and we are in our retry state
        self.assert_event_received(ResourceAgentErrorEvent, 10)
        self.assert_state_change(ResourceAgentState.STREAMING, 10)
