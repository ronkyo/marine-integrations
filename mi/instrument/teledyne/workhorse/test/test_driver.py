"""
@package mi.instrument.teledyne.workhorse.test.test_driver
@file marine-integrations/mi/instrument/teledyne/workhorse/test/test_driver.py
@author Sung Ahn
@brief Test Driver for Workhorse
Release notes:

Generic test Driver for ADCPS-K, ADCPS-I, ADCPT-B and ADCPT-DE
"""

__author__ = 'Sung Ahn'
__license__ = 'Apache 2.0'

import time as time
import unittest
from nose.plugins.attrib import attr
from mi.core.log import get_logger

log = get_logger()

# MI imports.
from mi.idk.unit_test import AgentCapabilityType

from mi.instrument.teledyne.test.test_driver import TeledyneUnitTest
from mi.instrument.teledyne.test.test_driver import TeledyneIntegrationTest
from mi.instrument.teledyne.test.test_driver import TeledyneQualificationTest
from mi.instrument.teledyne.test.test_driver import TeledynePublicationTest

from mi.instrument.teledyne.particles import DataParticleType
from mi.instrument.teledyne.driver import TeledyneProtocolState
from mi.instrument.teledyne.driver import TeledyneProtocolEvent
from mi.instrument.teledyne.workhorse.driver import WorkhorseParameter

from mi.instrument.teledyne.workhorse.driver import TeledynePrompt
from mi.instrument.teledyne.workhorse.driver import NEWLINE

from mi.instrument.teledyne.particles import ADCP_SYSTEM_CONFIGURATION_KEY
from mi.instrument.teledyne.particles import ADCP_COMPASS_CALIBRATION_KEY

from mi.core.exceptions import InstrumentCommandException

from mi.core.instrument.instrument_driver import ResourceAgentState


# ################################### RULES ####################################
# #
# Common capabilities in the base class                                       #
# #
# Instrument specific stuff in the derived class                              #
# #
# Generator spits out either stubs or comments describing test this here,     #
# test that there.                                                            #
# #
# Qualification tests are driven through the instrument_agent                 #
# #
# ##############################################################################

class WorkhorseParameterAltValue():
    # Values that are valid, but not the ones we want to use,
    # used for testing to verify that we are setting good values.
    #

    # Probably best NOT to tweek this one.
    SERIAL_FLOW_CONTROL = '11110'
    BANNER = 1
    SAVE_NVRAM_TO_RECORDER = True  # Immutable.
    SLEEP_ENABLE = 1
    POLLED_MODE = True
    PITCH = 1
    ROLL = 1


# ##############################################################################
# UNIT TESTS                                   #
# ##############################################################################
@attr('UNIT', group='mi')
class WorkhorseDriverUnitTest(TeledyneUnitTest):
    def setUp(self):
        TeledyneUnitTest.setUp(self)


# ##############################################################################
# INTEGRATION TESTS                                #
# ##############################################################################
@attr('INT', group='mi')
class WorkhorseDriverIntegrationTest(TeledyneIntegrationTest):
    def setUp(self):
        TeledyneIntegrationTest.setUp(self)

    # ##
    # Add instrument specific integration tests
    ###
    def test_parameters(self):
        """
        Test driver parameters and verify their type.  Startup parameters also verify the parameter
        value.  This test confirms that parameters are being read/converted properly and that
        the startup has been applied.
        """
        self.assert_initialize_driver()
        reply = self.driver_client.cmd_dvr('get_resource', WorkhorseParameter.ALL)
        self.assert_driver_parameters(reply, True)

    def test_break(self):
        self.assert_initialize_driver()
        self.assert_driver_command(TeledyneProtocolEvent.START_AUTOSAMPLE, state=TeledyneProtocolState.AUTOSAMPLE,
                                   delay=1)
        self.assert_driver_command(TeledyneProtocolEvent.STOP_AUTOSAMPLE, state=TeledyneProtocolState.COMMAND, delay=10)

    #@unittest.skip('It takes many hours for this test')
    def test_commands(self):
        """
        Run instrument commands from both command and streaming mode.
        """
        self.assert_initialize_driver()
        ####
        # First test in command mode
        ####

        self.assert_driver_command(TeledyneProtocolEvent.START_AUTOSAMPLE, state=TeledyneProtocolState.AUTOSAMPLE,
                                   delay=1)
        self.assert_driver_command(TeledyneProtocolEvent.STOP_AUTOSAMPLE, state=TeledyneProtocolState.COMMAND, delay=1)
        self.assert_driver_command(TeledyneProtocolEvent.GET_CALIBRATION)
        self.assert_driver_command(TeledyneProtocolEvent.GET_CONFIGURATION)
        self.assert_driver_command(TeledyneProtocolEvent.CLOCK_SYNC)
        self.assert_driver_command(TeledyneProtocolEvent.SCHEDULED_CLOCK_SYNC)
        self.assert_driver_command(TeledyneProtocolEvent.SAVE_SETUP_TO_RAM,
                                   expected="Parameters saved as USER defaults")
        self.assert_driver_command(TeledyneProtocolEvent.GET_ERROR_STATUS_WORD, regex='^........')
        self.assert_driver_command(TeledyneProtocolEvent.CLEAR_ERROR_STATUS_WORD, regex='^Error Status Word Cleared')
        self.assert_driver_command(TeledyneProtocolEvent.GET_FAULT_LOG, regex='^Total Unique Faults   =.*')
        self.assert_driver_command(TeledyneProtocolEvent.CLEAR_FAULT_LOG,
                                   expected='FC ..........\r\n Fault Log Cleared.\r\nClearing buffer @0x00801000\r\nDone [i=2048].\r\n')
        self.assert_driver_command(TeledyneProtocolEvent.RUN_TEST_200, regex='^  Ambient  Temperature =')
        self.assert_driver_command(TeledyneProtocolEvent.USER_SETS)
        self.assert_driver_command(TeledyneProtocolEvent.FACTORY_SETS)
        self.assert_driver_command(TeledyneProtocolEvent.ACQUIRE_STATUS)

        ####
        # Test in streaming mode
        ####
        # Put us in streaming
        self.assert_driver_command(TeledyneProtocolEvent.START_AUTOSAMPLE, state=TeledyneProtocolState.AUTOSAMPLE,
                                   delay=1)
        self.assert_driver_command_exception(TeledyneProtocolEvent.SAVE_SETUP_TO_RAM,
                                             exception_class=InstrumentCommandException)
        self.assert_driver_command_exception(TeledyneProtocolEvent.GET_ERROR_STATUS_WORD,
                                             exception_class=InstrumentCommandException)
        self.assert_driver_command_exception(TeledyneProtocolEvent.CLEAR_ERROR_STATUS_WORD,
                                             exception_class=InstrumentCommandException)
        self.assert_driver_command_exception(TeledyneProtocolEvent.GET_FAULT_LOG,
                                             exception_class=InstrumentCommandException)
        self.assert_driver_command_exception(TeledyneProtocolEvent.CLEAR_FAULT_LOG,
                                             exception_class=InstrumentCommandException)
        self.assert_driver_command_exception(TeledyneProtocolEvent.RUN_TEST_200,
                                             exception_class=InstrumentCommandException)
        self.assert_driver_command_exception(TeledyneProtocolEvent.ACQUIRE_STATUS,
                                             exception_class=InstrumentCommandException)
        self.assert_driver_command(TeledyneProtocolEvent.SCHEDULED_CLOCK_SYNC)
        self.assert_driver_command_exception(TeledyneProtocolEvent.CLOCK_SYNC,
                                             exception_class=InstrumentCommandException)
        self.assert_driver_command(TeledyneProtocolEvent.GET_CALIBRATION, regex=r'Calibration date and time:')
        self.assert_driver_command(TeledyneProtocolEvent.GET_CONFIGURATION, regex=r' Instrument S/N')
        self.assert_driver_command(TeledyneProtocolEvent.STOP_AUTOSAMPLE, state=TeledyneProtocolState.COMMAND, delay=1)

        ####
        # Test a bad command
        ####
        self.assert_driver_command_exception('ima_bad_command', exception_class=InstrumentCommandException)

    #@unittest.skip('It takes many hours for this test')
    def test_startup_params(self):
        """
        Verify that startup parameters are applied correctly. Generally this
        happens in the driver discovery method.

        since nose orders the tests by ascii value this should run first.
        """
        self.assert_initialize_driver()

        get_values = {
            WorkhorseParameter.SERIAL_FLOW_CONTROL: '11110',
            WorkhorseParameter.BANNER: False,
            WorkhorseParameter.INSTRUMENT_ID: 0,
            WorkhorseParameter.SLEEP_ENABLE: 0,
            WorkhorseParameter.SAVE_NVRAM_TO_RECORDER: True,
            WorkhorseParameter.POLLED_MODE: False,
            WorkhorseParameter.XMIT_POWER: 255,
            WorkhorseParameter.SPEED_OF_SOUND: 1485,
            WorkhorseParameter.PITCH: 0,
            WorkhorseParameter.ROLL: 0,
            WorkhorseParameter.SALINITY: 35,
            WorkhorseParameter.TIME_PER_ENSEMBLE: '00:00:00.00',
            WorkhorseParameter.TIME_PER_PING: '00:01.00',
            WorkhorseParameter.FALSE_TARGET_THRESHOLD: '050,001',
            WorkhorseParameter.BANDWIDTH_CONTROL: 0,
            WorkhorseParameter.CORRELATION_THRESHOLD: 64,
            WorkhorseParameter.SERIAL_OUT_FW_SWITCHES: '111100000',
            WorkhorseParameter.ERROR_VELOCITY_THRESHOLD: 2000,
            WorkhorseParameter.CLIP_DATA_PAST_BOTTOM: False,
            WorkhorseParameter.RECEIVER_GAIN_SELECT: 1,
            WorkhorseParameter.PINGS_PER_ENSEMBLE: 1,
            WorkhorseParameter.TRANSMIT_LENGTH: 0,
            WorkhorseParameter.PING_WEIGHT: 0,
            WorkhorseParameter.AMBIGUITY_VELOCITY: 175,
            WorkhorseParameter.SERIAL_DATA_OUT: '000 000 000',
            WorkhorseParameter.LATENCY_TRIGGER: False,
            WorkhorseParameter.HEADING_ALIGNMENT: +00000,
            WorkhorseParameter.HEADING_BIAS: +00000,
            WorkhorseParameter.DATA_STREAM_SELECTION: 0,
            WorkhorseParameter.ENSEMBLE_PER_BURST: 0,
            WorkhorseParameter.SAMPLE_AMBIENT_SOUND: False,
            WorkhorseParameter.BUFFERED_OUTPUT_PERIOD: '00:00:00'
        }
        new_set = {
            'SERIAL_FLOW_CONTROL': '11110',
            'BANNER': 1,
            'SAVE_NVRAM_TO_RECORDER': True,  # Immutable.
            'PITCH': 1,
            'ROLL': 1
        }
        # Change the values of these parameters to something before the
        # driver is reinitialized.  They should be blown away on reinit.
        new_values = {}

        p = WorkhorseParameter.dict()
        for k, v in new_set.items():
            if k not in ('BANNER', 'SERIAL_FLOW_CONTROL', 'SAVE_NVRAM_TO_RECORDER', 'TIME'):
                new_values[p[k]] = v
        self.assert_startup_parameters(self.assert_driver_parameters, new_values, get_values)

    def assert_clock_sync(self):
        """
        Verify the clock is set to at least the current date
        """
        dt = self.assert_get(WorkhorseParameter.TIME)
        lt = time.strftime("%Y/%m/%d,%H:%M:%S", time.gmtime(time.mktime(time.localtime())))
        self.assertTrue(lt[:10].upper() in dt.upper())


# ##############################################################################
# QUALIFICATION TESTS                              #
# Device specific qualification tests are for doing final testing of ion      #
# integration.  The generally aren't used for instrument debugging and should #
# be tackled after all unit and integration tests are complete                #
###############################################################################
@attr('QUAL', group='mi')
class WorkhorseDriverQualificationTest(TeledyneQualificationTest):
    def setUp(self):
        TeledyneQualificationTest.setUp(self)

    def assert_configuration(self, data_particle, verify_values=False):
        """
        Verify assert_compass_calibration particle
        @param data_particle:  ADCP_COMPASS_CALIBRATION data particle
        @param verify_values:  bool, should we verify parameter values
        """
        self.assert_data_particle_keys(ADCP_SYSTEM_CONFIGURATION_KEY, self._system_configuration_data_parameters)
        self.assert_data_particle_header(data_particle, DataParticleType.ADCP_SYSTEM_CONFIGURATION)
        self.assert_data_particle_parameters(data_particle, self._system_configuration_data_parameters, verify_values)

    def assert_compass_calibration(self, data_particle, verify_values=False):
        """
        Verify assert_compass_calibration particle
        @param data_particle:  ADCP_COMPASS_CALIBRATION data particle
        @param verify_values:  bool, should we verify parameter values
        """
        self.assert_data_particle_keys(ADCP_COMPASS_CALIBRATION_KEY, self._calibration_data_parameters)
        self.assert_data_particle_header(data_particle, DataParticleType.ADCP_COMPASS_CALIBRATION)
        self.assert_data_particle_parameters(data_particle, self._calibration_data_parameters, verify_values)

    # need to override this because we are slow and dont feel like modifying the base class lightly
    def assert_set_parameter(self, name, value, verify=True):
        """
        verify that parameters are set correctly.  Assumes we are in command mode.
        """
        setParams = {name: value}
        getParams = [name]

        self.instrument_agent_client.set_resource(setParams, timeout=300)

        if verify:
            result = self.instrument_agent_client.get_resource(getParams, timeout=300)
            self.assertEqual(result[name], value)

    @unittest.skip('It takes time for this test')
    def test_direct_access_telnet_mode(self):
        """
        @brief This test manually tests that the Instrument Driver properly supports
         direct access to the physical instrument. (telnet mode)
        """

        self.assert_enter_command_mode()
        self.assert_set_parameter(WorkhorseParameter.SPEED_OF_SOUND, 1487)

        # go into direct access, and muck up a setting.
        self.assert_direct_access_start_telnet(timeout=600)

        self.tcp_client.send_data("%sEC1488%s" % (NEWLINE, NEWLINE))

        self.tcp_client.expect(TeledynePrompt.COMMAND)

        self.assert_direct_access_stop_telnet()

        # verify the setting got restored.
        self.assert_enter_command_mode()
        # Direct access is true, it should be set before
        self.assert_get_parameter(WorkhorseParameter.SPEED_OF_SOUND, 1487)

    # Only test when time is sync in startup
    @unittest.skip('It takes time for this test')
    def _test_execute_clock_sync(self):
        """
        Verify we can synchronize the instrument internal clock
        """
        self.assert_enter_command_mode()

        self.assert_execute_resource(TeledyneProtocolEvent.CLOCK_SYNC)

        # Now verify that at least the date matches
        check_new_params = self.instrument_agent_client.get_resource([WorkhorseParameter.TIME], timeout=45)

        instrument_time = time.mktime(
            time.strptime(check_new_params.get(WorkhorseParameter.TIME).lower(), "%Y/%m/%d,%H:%M:%S %Z"))

        self.assertLessEqual(abs(instrument_time - time.mktime(time.gmtime())), 45)

    @unittest.skip('It takes time for this test')
    def test_get_capabilities(self):
        """
        @brief Verify that the correct capabilities are returned from get_capabilities
        at various driver/agent states.
        """
        self.assert_enter_command_mode()

        ##################
        #  Command Mode
        ##################
        capabilities = {
            AgentCapabilityType.AGENT_COMMAND: self._common_agent_commands(ResourceAgentState.COMMAND),
            AgentCapabilityType.AGENT_PARAMETER: self._common_agent_parameters(),
            AgentCapabilityType.RESOURCE_COMMAND: [
                TeledyneProtocolEvent.CLOCK_SYNC,
                TeledyneProtocolEvent.START_AUTOSAMPLE,
                TeledyneProtocolEvent.GET_CALIBRATION,
                TeledyneProtocolEvent.RUN_TEST_200,
                TeledyneProtocolEvent.ACQUIRE_STATUS,
            ],
            AgentCapabilityType.RESOURCE_INTERFACE: None,
            AgentCapabilityType.RESOURCE_PARAMETER: self._driver_parameters.keys()
        }

        self.assert_capabilities(capabilities)

        ##################
        #  Streaming Mode
        ##################

        capabilities[AgentCapabilityType.AGENT_COMMAND] = self._common_agent_commands(ResourceAgentState.STREAMING)
        capabilities[AgentCapabilityType.RESOURCE_COMMAND] = [
            TeledyneProtocolEvent.STOP_AUTOSAMPLE,
            TeledyneProtocolEvent.GET_CALIBRATION,
        ]
        self.assert_start_autosample()
        self.assert_capabilities(capabilities)
        self.assert_stop_autosample()

        ##################
        #  DA Mode
        ##################

        capabilities[AgentCapabilityType.AGENT_COMMAND] = self._common_agent_commands(ResourceAgentState.DIRECT_ACCESS)
        capabilities[AgentCapabilityType.RESOURCE_COMMAND] = [
        ]

        self.assert_direct_access_start_telnet()
        self.assert_capabilities(capabilities)
        self.assert_direct_access_stop_telnet()

        #######################
        #  Uninitialized Mode
        #######################

        capabilities[AgentCapabilityType.AGENT_COMMAND] = self._common_agent_commands(ResourceAgentState.UNINITIALIZED)
        capabilities[AgentCapabilityType.RESOURCE_COMMAND] = []
        capabilities[AgentCapabilityType.RESOURCE_INTERFACE] = []
        capabilities[AgentCapabilityType.RESOURCE_PARAMETER] = []

        self.assert_reset()
        self.assert_capabilities(capabilities)

    @unittest.skip('It takes many hours for this test')
    def test_startup_params_first_pass(self):
        """
        Verify that startup parameters are applied correctly. Generally this
        happens in the driver discovery method.  We have two identical versions
        of this test so it is run twice.  First time to check and CHANGE, then
        the second time to check again.

        since nose orders the tests by ascii value this should run second.
        """
        self.assert_enter_command_mode()

        for k in self._driver_parameters.keys():
            if self.VALUE in self._driver_parameters[k]:
                if not self._driver_parameters[k][self.READONLY]:
                    self.assert_get_parameter(k, self._driver_parameters[k][self.VALUE])
                    log.debug("VERIFYING %s is set to %s appropriately ", k,
                              str(self._driver_parameters[k][self.VALUE]))

        self.assert_set_parameter(WorkhorseParameter.XMIT_POWER, 250)
        self.assert_set_parameter(WorkhorseParameter.SPEED_OF_SOUND, 1480)
        self.assert_set_parameter(WorkhorseParameter.PITCH, 1)
        self.assert_set_parameter(WorkhorseParameter.ROLL, 1)
        self.assert_set_parameter(WorkhorseParameter.SALINITY, 36)
        self.assert_set_parameter(WorkhorseParameter.TRANSDUCER_DEPTH, 6000, False)
        self.assert_set_parameter(WorkhorseParameter.TRANSDUCER_DEPTH, 0)

        self.assert_set_parameter(WorkhorseParameter.TIME_PER_ENSEMBLE, '00:00:01.00')
        self.assert_set_parameter(WorkhorseParameter.TIME_PER_ENSEMBLE, '01:00:00.00')

        self.assert_set_parameter(WorkhorseParameter.FALSE_TARGET_THRESHOLD, '049,002')
        self.assert_set_parameter(WorkhorseParameter.BANDWIDTH_CONTROL, 1)
        self.assert_set_parameter(WorkhorseParameter.CORRELATION_THRESHOLD, 63)

        self.assert_set_parameter(WorkhorseParameter.ERROR_VELOCITY_THRESHOLD, 1999)
        self.assert_set_parameter(WorkhorseParameter.BLANK_AFTER_TRANSMIT, 714)

        self.assert_set_parameter(WorkhorseParameter.CLIP_DATA_PAST_BOTTOM, 1)
        self.assert_set_parameter(WorkhorseParameter.RECEIVER_GAIN_SELECT, 0)
        self.assert_set_parameter(WorkhorseParameter.NUMBER_OF_DEPTH_CELLS, 99)
        self.assert_set_parameter(WorkhorseParameter.PINGS_PER_ENSEMBLE, 0)
        self.assert_set_parameter(WorkhorseParameter.DEPTH_CELL_SIZE, 790)

        self.assert_set_parameter(WorkhorseParameter.TRANSMIT_LENGTH, 1)
        self.assert_set_parameter(WorkhorseParameter.PING_WEIGHT, 1)
        self.assert_set_parameter(WorkhorseParameter.AMBIGUITY_VELOCITY, 176)

    @unittest.skip('It takes many hours for this test')
    def test_startup_params_second_pass(self):
        """
        Verify that startup parameters are applied correctly. Generally this
        happens in the driver discovery method.  We have two identical versions
        of this test so it is run twice.  First time to check and CHANGE, then
        the second time to check again.

        since nose orders the tests by ascii value this should run second.
        """
        self.assert_enter_command_mode()
        for k in self._driver_parameters.keys():
            if self.VALUE in self._driver_parameters[k]:
                if not self._driver_parameters[k][self.READONLY]:
                    self.assert_get_parameter(k, self._driver_parameters[k][self.VALUE])
                    log.debug("VERIFYING %s is set to %s appropriately ", k,
                              str(self._driver_parameters[k][self.VALUE]))

        # Change these values anyway just in case it ran first.
        self.assert_set_parameter(WorkhorseParameter.XMIT_POWER, 250)
        self.assert_set_parameter(WorkhorseParameter.SPEED_OF_SOUND, 1480)
        self.assert_set_parameter(WorkhorseParameter.SPEED_OF_SOUND, 1500)
        self.assert_set_parameter(WorkhorseParameter.PITCH, 1)
        self.assert_set_parameter(WorkhorseParameter.ROLL, 1)
        self.assert_set_parameter(WorkhorseParameter.SALINITY, 36)
        self.assert_set_parameter(WorkhorseParameter.TIME_PER_ENSEMBLE, '00:00:01.00')
        self.assert_set_parameter(WorkhorseParameter.TIME_PER_PING, '00:02.00')
        self.assert_set_parameter(WorkhorseParameter.FALSE_TARGET_THRESHOLD, '049,002')
        self.assert_set_parameter(WorkhorseParameter.BANDWIDTH_CONTROL, 1)
        self.assert_set_parameter(WorkhorseParameter.CORRELATION_THRESHOLD, 63)
        self.assert_set_parameter(WorkhorseParameter.ERROR_VELOCITY_THRESHOLD, 1999)
        self.assert_set_parameter(WorkhorseParameter.BLANK_AFTER_TRANSMIT, 714)
        self.assert_set_parameter(WorkhorseParameter.BLANK_AFTER_TRANSMIT, 352)
        self.assert_set_parameter(WorkhorseParameter.CLIP_DATA_PAST_BOTTOM, 1)
        self.assert_set_parameter(WorkhorseParameter.RECEIVER_GAIN_SELECT, 0)
        self.assert_set_parameter(WorkhorseParameter.NUMBER_OF_DEPTH_CELLS, 99)
        self.assert_set_parameter(WorkhorseParameter.NUMBER_OF_DEPTH_CELLS, 30)
        self.assert_set_parameter(WorkhorseParameter.PINGS_PER_ENSEMBLE, 0)
        self.assert_set_parameter(WorkhorseParameter.PINGS_PER_ENSEMBLE, 1)
        self.assert_set_parameter(WorkhorseParameter.DEPTH_CELL_SIZE, 790)
        self.assert_set_parameter(WorkhorseParameter.TRANSMIT_LENGTH, 1)
        self.assert_set_parameter(WorkhorseParameter.PING_WEIGHT, 1)
        self.assert_set_parameter(WorkhorseParameter.AMBIGUITY_VELOCITY, 176)


###############################################################################
#                             PUBLICATION TESTS                               #
# Device specific publication tests are for                                    #
# testing device specific capabilities                                        #
###############################################################################
@attr('PUB', group='mi')
class WorkhorseDriverPublicationTest(TeledynePublicationTest):
    def setUp(self):
        TeledynePublicationTest.setUp(self)


