"""
@package mi.instrument.kut.ek60.ooicore.test.test_driver
@file marine-integrations/mi/instrument/kut/ek60/ooicore/driver.py
@author Richard Han
@brief Test cases for ooicore driver

USAGE:
 Make tests verbose and provide stdout
   * From the IDK
       $ bin/test_driver
       $ bin/test_driver -u [-t testname]
       $ bin/test_driver -i [-t testname]
       $ bin/test_driver -q [-t testname]
"""
from mi.core.instrument.data_particle import RawDataParticle
from mi.instrument.uw.bars.ooicore.driver import BarsDataParticleKey

__author__ = 'Richard Han'
__license__ = 'Apache 2.0'

import unittest

from nose.plugins.attrib import attr
from mock import Mock

from mi.core.log import get_logger ; log = get_logger()

# MI imports.
from mi.idk.unit_test import InstrumentDriverTestCase, ParameterTestConfigKey
from mi.idk.unit_test import InstrumentDriverUnitTestCase
from mi.idk.unit_test import InstrumentDriverIntegrationTestCase
from mi.idk.unit_test import InstrumentDriverQualificationTestCase
from mi.idk.unit_test import DriverTestMixin

from interface.objects import AgentCommand

from mi.core.instrument.logger_client import LoggerClient

from mi.core.instrument.chunker import StringChunker
from mi.core.instrument.instrument_driver import DriverAsyncEvent, DriverConfigKey
from mi.core.instrument.instrument_driver import DriverConnectionState
from mi.core.instrument.instrument_driver import DriverProtocolState

from ion.agents.instrument.instrument_agent import InstrumentAgentState
from ion.agents.instrument.direct_access.direct_access_server import DirectAccessTypes

from mi.instrument.kut.ek60.ooicore.driver import InstrumentDriver, ZPLSCStatusParticleKey
from mi.instrument.kut.ek60.ooicore.driver import DataParticleType
from mi.instrument.kut.ek60.ooicore.driver import Command
from mi.instrument.kut.ek60.ooicore.driver import ProtocolState
from mi.instrument.kut.ek60.ooicore.driver import ProtocolEvent
from mi.instrument.kut.ek60.ooicore.driver import Capability
from mi.instrument.kut.ek60.ooicore.driver import Parameter
from mi.instrument.kut.ek60.ooicore.driver import Protocol
from mi.instrument.kut.ek60.ooicore.driver import Prompt
from mi.instrument.kut.ek60.ooicore.driver import NEWLINE

###
#   Driver parameters for the tests
###
InstrumentDriverTestCase.initialize(
    driver_module='mi.instrument.kut.ek60.ooicore.driver',
    driver_class="InstrumentDriver",

    instrument_agent_resource_id = '613CAW',
    instrument_agent_name = 'kut_ek60_ooicore',
    instrument_agent_packet_config = DataParticleType(),

    driver_startup_config = {
         DriverConfigKey.PARAMETERS : {
                Parameter.FTP_IP_ADDRESS : '128.193.64.201',
                Parameter.SCHEDULE : "# Default configuration file \
--- \
file_prefix:    \"DEFAULT\" \
file_path:      \"DEFAULT\" \
max_file_size:   52428800 \
intervals: \
    name: \"default\" \
    type: \"constant\" \
    start_at:  \"00:00\" \
    duration:  \"00:15:00\" \
    repeat_every:   \"01:00\" \
    stop_repeating_at: \"23:55\" \
    interval:   1000 \
    max_range:  80 \
            frequency: \
          38000: \
              mode:   active \
              power:  100 \
              pulse_length:   256 \
          120000: \
              mode:   active \
              power:  100 \
              pulse_length:   64 \
          200000: \
              mode:   active \
              power:  120 \
              pulse_length:   64",
        }
    }
)

#################################### RULES ####################################
#                                                                             #
# Common capabilities in the base class                                       #
#                                                                             #
# Instrument specific stuff in the derived class                              #
#                                                                             #
# Generator spits out either stubs or comments describing test this here,     #
# test that there.                                                            #
#                                                                             #
# Qualification tests are driven through the instrument_agent                 #
#                                                                             #
###############################################################################

###
#   Driver constant definitions
###

###############################################################################
#                           DRIVER TEST MIXIN        		                  #
#     Defines a set of constants and assert methods used for data particle    #
#     verification 														      #
#                                                                             #
#  In python mixin classes are classes designed such that they wouldn't be    #
#  able to stand on their own, but are inherited by other classes generally   #
#  using multiple inheritance.                                                #
#                                                                             #
# This class defines a configuration structure for testing and common assert  #
# methods for validating data particles.									  #
###############################################################################
class DriverTestMixinSub(DriverTestMixin):

    """
    Mixin class used for storing data particle constants and common data assertion methods.
    """

    InstrumentDriver = InstrumentDriver
    # Create some short names for the parameter test config

    TYPE = ParameterTestConfigKey.TYPE
    READONLY = ParameterTestConfigKey.READONLY
    STARTUP = ParameterTestConfigKey.STARTUP
    DA = ParameterTestConfigKey.DIRECT_ACCESS
    VALUE = ParameterTestConfigKey.VALUE
    REQUIRED = ParameterTestConfigKey.REQUIRED
    DEFAULT = ParameterTestConfigKey.DEFAULT
    STATES = ParameterTestConfigKey.STATES

    INVALID_STATUS = "This is an invalid status; it had better cause an exception."
    # VALID_STATUS_01 = "{'connected': True, \
    #                'er60_channels': {'GPT  38 kHz 00907207b7b1 6-1 OOI.38|200': {'frequency': 38000, \
    #                                                            'mode': 'active', \
    #                                                            'power': 100.0, \
    #                                                            'pulse_length': 0.000256, \
    #                                                            'sample_interval': 6.4e-05}, \
    #                'GPT 120 kHz 00907207b7dc 1-1 ES120-7CD': {'frequency': 120000, \
    #                                                           'mode': 'active', \
    #                                                           'power': 100.0, \
    #                                                           'pulse_length': 6.4e-05, \
    #                                                           'sample_interval': 1.6e-05}, \
    #                'GPT 200 kHz 00907207b7b1 6-2 OOI38|200': {'frequency': 200000, \
    #                                                           'mode': 'active', \
    #                                                           'power': 120.0, \
    #                                                           'pulse_length': 6.4e-05, \
    #                                                           'sample_interval': 1.6e-05}}, \
    #               'er60_status': {'current_running_interval': None, \
    #              'current_utc_time': '2014-07-01 17:59:34.419000', \
    #              'executable': 'c:/users/ooi/desktop/er60.lnk', \
    #              'fs_root': 'D:/', \
    #              'host': '157.237.15.100', \
    #              'next_scheduled_interval': None, \
    #              'pid': 1864, \
    #              'port': 56635, \
    #              'raw_output': {'current_raw_filename': 'OOI_BT-D20140619-T150820.raw', \
    #                             'current_raw_filesize': None, \
    #                             'file_path': 'D:\\data\\Bench_Test', \
    #                             'file_prefix': 'OOI_BT', \
    #                             'max_file_size': 52428800, \
    #                             'sample_range': 80.0, \
    #                             'save_bottom': True, \
    #                             'save_index': True, \
    #                             'save_raw': True}, \
    #              'scheduled_intervals_remaining': 0}, \
    #              'gpts_enabled': False, \
    #              'schedule': {}, \
    #              'schedule_filename': 'bench_test.yaml'}" + NEWLINE

    VALID_STATUS_01 = "{'connected': True," + NEWLINE + \
"         'er60_channels': {'GPT  38 kHz 00907207b7b1 6-1 OOI.38|200': {'frequency': 38000," + NEWLINE + \
"                                                                      'mode': 'active'," + NEWLINE + \
"                                                                       'power': 100.0,"  + NEWLINE + \
"                                                                       'pulse_length': 0.000256," + NEWLINE + \
"                                                                       'sample_interval': 6.4e-05}," + NEWLINE + \
"                           'GPT 120 kHz 00907207b7dc 1-1 ES120-7CD': {'frequency': 120000," + NEWLINE + \
"                                                                      'mode': 'active'," + NEWLINE + \
"                                                                      'power': 100.0," + NEWLINE + \
"                                                                      'pulse_length': 6.4e-05," + NEWLINE +  \
"                                                                      'sample_interval': 1.6e-05}," + NEWLINE + \
"                           'GPT 200 kHz 00907207b7b1 6-2 OOI38|200': {'frequency': 200000," + NEWLINE + \
"                                                                      'mode': 'active'," + NEWLINE + \
"                                                                     'power': 120.0," + NEWLINE + \
"                                                                      'pulse_length': 6.4e-05," + NEWLINE + \
"                                                                      'sample_interval': 1.6e-05}}," + NEWLINE + \
"         'er60_status': {'current_running_interval': None," + NEWLINE + \
"                         'current_utc_time': '2014-07-09 01:23:39.691000'," + NEWLINE + \
"                         'executable': 'c:/users/ooi/desktop/er60.lnk'," + NEWLINE + \
"                         'fs_root': 'D:/'," + NEWLINE + \
"                         'host': '157.237.15.100'," + NEWLINE + \
"                         'next_scheduled_interval': None," + NEWLINE + \
"                         'pid': 1864," + NEWLINE + \
"                         'port': 56635," + NEWLINE + \
"                         'raw_output': {'current_raw_filename': 'OOI-D20140707-T214500.raw'," + NEWLINE + \
"                                        'current_raw_filesize': 0," + NEWLINE + \
"                                       'file_path': 'D:\\data\\QCT_1'," + NEWLINE + \
"                                        'file_prefix': 'OOI'," + NEWLINE + \
"                                        'max_file_size': 52428800," + NEWLINE + \
"                                        'sample_range': 220.0," + NEWLINE +  \
"                                        'save_bottom': True," + NEWLINE + \
"                                        'save_index': True," + NEWLINE + \
"                                        'save_raw': True}," + NEWLINE + \
"                         'scheduled_intervals_remaining': 0}," + NEWLINE + \
"         'gpts_enabled': False," + NEWLINE + \
"         'schedule': {}," + NEWLINE + \
"         'schedule_filename': 'qct_configuration_example_1.yaml'}"

    _driver_capabilities = {
        # capabilities defined in the IOS
        Capability.START_AUTOSAMPLE: {STATES: [ProtocolState.COMMAND]},
        Capability.STOP_AUTOSAMPLE: {STATES: [ProtocolState.AUTOSAMPLE]},
        Capability.START_DIRECT: {STATES: [ProtocolState.COMMAND]},
        Capability.EXECUTE_DIRECT: {STATES: [ProtocolState.DIRECT_ACCESS]},
        Capability.STOP_DIRECT: {STATES: [ProtocolState.DIRECT_ACCESS]},
        Capability.GET: {STATES: [ProtocolState.COMMAND, ProtocolState.AUTOSAMPLE]},
        Capability.SET: {STATES: [ProtocolState.COMMAND]},
        Capability.EXECUTE_DIRECT: {STATES: [ProtocolState.DIRECT_ACCESS]},
        Capability.ACQUIRE_STATUS: {STATES: [ProtocolState.COMMAND]},
    }

    ###
    #  Parameter and Type Definitions
    ###

    _driver_parameters = {
        # Parameters defined in the IOS

        Parameter.SCHEDULE: {TYPE: str, READONLY: False, DA: False, STARTUP: True, DEFAULT: "Test", VALUE: "Test"},
        Parameter.FTP_IP_ADDRESS: {TYPE: str, READONLY: False, DA: False, STARTUP: True, DEFAULT: "128.193.64.201", VALUE: "128.193.64.201"},
    }


    _sample_parameters = {
        ZPLSCStatusParticleKey.ZPLSC_CONNECTED: {TYPE: bool, VALUE: True, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_MODE: {TYPE: unicode, VALUE: 'active', REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_POWER: {TYPE: float, VALUE: 100.0, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_PULSE_LENGTH: {TYPE: float, VALUE: 6.4e-05, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_SAMPLE_INTERVAL: {TYPE: float, VALUE: 1.6e-05, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_MODE: {TYPE: unicode, VALUE: 'active', REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_POWER: {TYPE: float, VALUE: 120.0, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_PULSE_LENGTH: {TYPE: float, VALUE: 6.4e-05, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_SAMPLE_INTERVAL: {TYPE: float, VALUE: 1.6e-05, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_MODE: {TYPE: unicode, VALUE: 'active', REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_POWER: {TYPE: float, VALUE: 100.0, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_PULSE_LENGTH: {TYPE: float, VALUE: 0.000256, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_SAMPLE_INTERVAL: {TYPE: float, VALUE: 6.4e-05, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_CURRENT_UTC_TIME: {TYPE: unicode, VALUE: '2014-07-09 01:23:39.691000', REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_EXECUTABLE: {TYPE: unicode, VALUE: 'c:/users/ooi/desktop/er60.lnk', REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_FS_ROOT: {TYPE: unicode, VALUE: 'D:/', REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_NEXT_SCHEDULED_INTERVAL: {TYPE: unicode, VALUE: 'None', REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_HOST: {TYPE: unicode, VALUE: '157.237.15.100', REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_PID: {TYPE: int, VALUE: 1864, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_PORT: {TYPE: int, VALUE: 56635, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_CURRENT_RAW_FILENAME: {TYPE: unicode, VALUE: 'OOI-D20140707-T214500.raw', REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_CURRENT_RAW_FILESIZE: {TYPE: int, VALUE: 0, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_FILE_PATH: {TYPE: unicode, VALUE: 'D:\\data\\QCT_1', REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_FILE_PREFIX: {TYPE: unicode, VALUE: 'OOI', REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_MAX_FILE_SIZE: {TYPE: int, VALUE: 52428800, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_SAMPLE_RANGE: {TYPE: float, VALUE:  220.0, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_SAVE_BOTTOM: {TYPE: bool, VALUE: True, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_SAVE_INDEX: {TYPE: bool, VALUE: True, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_SAVE_RAW: {TYPE: bool, VALUE: True, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_SCHEDULED_INTERVALS_REMAINING: {TYPE: int, VALUE: 0, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_GPTS_ENABLED: {TYPE: bool, VALUE: False, REQUIRED: True},
        ZPLSCStatusParticleKey.ZPLSC_SCHEDULE_FILENAME: {TYPE: unicode, VALUE: 'qct_configuration_example_1.yaml', REQUIRED: True},

    }

    def assert_particle_sample(self, data_particle, verify_values=False):
        '''
        Verify sample particle
        @param data_particle:  ZPLSCStatusParticle status particle
        @param verify_values:  bool, should we verify parameter values
        '''
        self.assert_data_particle_keys(ZPLSCStatusParticleKey, self._sample_parameters)
        self.assert_data_particle_header(data_particle, DataParticleType.ZPLSC_STATUS, require_instrument_timestamp=False)
        self.assert_data_particle_parameters(data_particle, self._sample_parameters, verify_values)


    # def assertSampleDataParticle(self, data_particle):
    #     '''
    #     Verify a particle is a know particle to this driver and verify the particle is
    #     correct
    #     @param data_particle: Data particle of unkown type produced by the driver
    #     '''
    #     if (isinstance(data_particle, RawDataParticle)):
    #         self.assert_particle_raw(data_particle)
    #     else:
    #         log.error("Unknown Particle Detected: %s" % data_particle)
    #         self.assertFalse(True)


###############################################################################
#                                UNIT TESTS                                   #
#         Unit tests test the method calls and parameters using Mock.         #
#                                                                             #
#   These tests are especially useful for testing parsers and other data      #
#   handling.  The tests generally focus on small segments of code, like a    #
#   single function call, but more complex code using Mock objects.  However  #
#   if you find yourself mocking too much maybe it is better as an            #
#   integration test.                                                         #
#                                                                             #
#   Unit tests do not start up external processes like the port agent or      #
#   driver process.                                                           #
###############################################################################
@attr('UNIT', group='mi')
class DriverUnitTest(InstrumentDriverUnitTestCase, DriverTestMixinSub):

    def setUp(self):
        InstrumentDriverUnitTestCase.setUp(self)


    def test_driver_enums(self):
        """
        Verify that all driver enumeration has no duplicate values that might cause confusion.  Also
        do a little extra validation for the Capabilites
        """
        self.assert_enum_has_no_duplicates(DataParticleType())
        self.assert_enum_has_no_duplicates(ProtocolState())
        self.assert_enum_has_no_duplicates(ProtocolEvent())
        self.assert_enum_has_no_duplicates(Parameter())
        self.assert_enum_has_no_duplicates(Command())
        self.assert_enum_has_no_duplicates(ZPLSCStatusParticleKey())

        # Test capabilites for duplicates, them verify that capabilities is a subset of proto events
        self.assert_enum_has_no_duplicates(Capability())
        self.assert_enum_complete(Capability(), ProtocolEvent())


    def test_driver_schema(self):
        """
        get the driver schema and verify it is configured properly
        """
        driver = self.InstrumentDriver(self._got_data_event_callback)
        self.assert_driver_schema(driver, self._driver_parameters, self._driver_capabilities)

    def test_capabilities(self):
        """
        Verify the FSM reports capabilities as expected.  All states defined in this dict must
        also be defined in the protocol FSM.
        """
        capabilities = {
            ProtocolState.COMMAND: ['DRIVER_EVENT_START_AUTOSAMPLE',
                                    'DRIVER_EVENT_GET',
                                    'DRIVER_EVENT_SET',
                                    'DRIVER_EVENT_START_DIRECT',
                                    'DRIVER_EVENT_ACQUIRE_STATUS'],
            ProtocolState.AUTOSAMPLE: ['DRIVER_EVENT_STOP_AUTOSAMPLE'],
            ProtocolState.DIRECT_ACCESS: ['DRIVER_EVENT_STOP_DIRECT',
                                          'EXECUTE_DIRECT'],
            ProtocolState.UNKNOWN: ['DRIVER_EVENT_DISCOVER'],
        }
        driver = self.InstrumentDriver(self._got_data_event_callback)
        self.assert_capabilities(driver, capabilities)

    def test_protocol_filter_capabilities(self):
        """
        This tests driver filter_capabilities.
        Iterate through available capabilities, and verify that they can pass successfully through the filter.
        Test silly made up capabilities to verify they are blocked by filter.
        """
        mock_callback = Mock()
        protocol = Protocol(Prompt, NEWLINE, mock_callback)
        driver_capabilities = Capability().list()
        test_capabilities = Capability().list()

        # Add a bogus capability that will be filtered out.
        test_capabilities.append("BOGUS_CAPABILITY")

        # Verify "BOGUS_CAPABILITY was filtered out
        self.assertEquals(sorted(driver_capabilities),
                          sorted(protocol._filter_capabilities(test_capabilities)))

    def test_chunker(self):
        """
        Test the chunker and verify the particles created.
        """
        chunker = StringChunker(Protocol.sieve_function)
        self.assert_chunker_sample(chunker, self.VALID_STATUS_01)
        self.assert_chunker_sample_with_noise(chunker, self.VALID_STATUS_01)
        self.assert_chunker_fragmented_sample(chunker, self.VALID_STATUS_01)
        self.assert_chunker_combined_sample(chunker, self.VALID_STATUS_01)

    def test_got_data(self):
        """
        Verify sample data passed through the got data method produces the correct data particles
        """
        # Create and initialize the instrument driver with a mock port agent
        driver = InstrumentDriver(self._got_data_event_callback)
        self.assert_initialize_driver(driver)

        self.assert_raw_particle_published(driver, True)

        # Start validating data particles
        self.assert_particle_published(driver, self.VALID_STATUS_01, self.assert_particle_sample, True)


###############################################################################
#                            INTEGRATION TESTS                                #
#     Integration test test the direct driver / instrument interaction        #
#     but making direct calls via zeromq.                                     #
#     - Common Integration tests test the driver through the instrument agent #
#     and common for all drivers (minimum requirement for ION ingestion)      #
###############################################################################
@attr('INT', group='mi')
class DriverIntegrationTest(InstrumentDriverIntegrationTestCase):
    def setUp(self):
        InstrumentDriverIntegrationTestCase.setUp(self)



###############################################################################
#                            QUALIFICATION TESTS                              #
# Device specific qualification tests are for doing final testing of ion      #
# integration.  The generally aren't used for instrument debugging and should #
# be tackled after all unit and integration tests are complete                #
###############################################################################
@attr('QUAL', group='mi')
class DriverQualificationTest(InstrumentDriverQualificationTestCase):
    def setUp(self):
        InstrumentDriverQualificationTestCase.setUp(self)

    def test_direct_access_telnet_mode(self):
        """
        @brief This test manually tests that the Instrument Driver properly supports direct access to the physical instrument. (telnet mode)
        """
        self.assert_direct_access_start_telnet()
        self.assertTrue(self.tcp_client)

        ###
        #   Add instrument specific code here.
        ###

        self.assert_direct_access_stop_telnet()


    def test_poll(self):
        '''
        No polling for a single sample
        '''


    def test_autosample(self):
        '''
        start and stop autosample and verify data particle
        '''


    def test_get_set_parameters(self):
        '''
        verify that all parameters can be get set properly, this includes
        ensuring that read only parameters fail on set.
        '''
        self.assert_enter_command_mode()


    def test_get_capabilities(self):
        """
        @brief Walk through all driver protocol states and verify capabilities
        returned by get_current_capabilities
        """
        self.assert_enter_command_mode()
