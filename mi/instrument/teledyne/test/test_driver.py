"""
@package mi.instrument.teledyne.test.test_driver
@file marine-integrations/mi/instrument/teledyne/test/test_driver.py
@author Roger Unwin
@brief Driver for the teledyne family
Release notes:
"""

__author__ = 'Roger Unwin'
__license__ = 'Apache 2.0'

import time
import unittest
from mi.core.log import get_logger

log = get_logger()

from nose.plugins.attrib import attr
from mi.idk.unit_test import InstrumentDriverUnitTestCase
from mi.idk.unit_test import InstrumentDriverIntegrationTestCase
from mi.idk.unit_test import InstrumentDriverQualificationTestCase
from mi.idk.unit_test import InstrumentDriverPublicationTestCase
from mi.core.exceptions import NotImplementedException
from mi.instrument.teledyne.particles import DataParticleType

from mi.instrument.teledyne.driver import TeledyneProtocolState
from mi.instrument.teledyne.driver import TeledyneProtocolEvent
from mi.instrument.teledyne.driver import TeledyneParameter

DEFAULT_CLOCK_DIFF = 5


###############################################################################
#                                UNIT TESTS                                   #
#         Unit tests test the method calls and parameters using Mock.         #
# 1. Pick a single method within the class.                                   #
# 2. Create an instance of the class                                          #
# 3. If the method to be tested tries to call out, over-ride the offending    #
#    method with a mock                                                       #
# 4. Using above, try to cover all paths through the functions                #
# 5. Negative testing if at all possible.                                     #
###############################################################################
@attr('UNIT', group='mi')
class TeledyneUnitTest(InstrumentDriverUnitTestCase):
    def setUp(self):
        InstrumentDriverUnitTestCase.setUp(self)


###############################################################################
#                            INTEGRATION TESTS                                #
#     Integration test test the direct driver / instrument interaction        #
#     but making direct calls via zeromq.                                     #
#     - Common Integration tests test the driver through the instrument agent #
#     and common for all drivers (minimum requirement for ION ingestion)      #
###############################################################################
@attr('INT', group='mi')
class TeledyneIntegrationTest(InstrumentDriverIntegrationTestCase):

    def setUp(self):
        InstrumentDriverIntegrationTestCase.setUp(self)

    def _is_time_set(self, time_param, expected_time, time_format="%d %b %Y %H:%M:%S", tolerance=DEFAULT_CLOCK_DIFF):
        """
        Verify is what we expect it to be within a given tolerance
        @param time_param: driver parameter
        @param expected_time: what the time should be in seconds since unix epoch or formatted time string
        @param time_format: date time format
        @param tolerance: how close to the set time should the get be?
        """
        log.debug("Expected time un-formatted: %s", expected_time)

        result_time = self.assert_get(time_param)

        log.debug("RESULT TIME = " + str(result_time))
        log.debug("TIME FORMAT = " + time_format)
        result_time_struct = time.strptime(result_time, time_format)
        converted_time = time.mktime(result_time_struct)

        if isinstance(expected_time, float):
            expected_time_struct = time.localtime(expected_time)
        else:
            expected_time_struct = time.strptime(expected_time, time_format)

        log.debug("Current Time: %s, Expected Time: %s", time.strftime("%d %b %y %H:%M:%S", result_time_struct),
                  time.strftime("%d %b %y %H:%M:%S", expected_time_struct))

        log.debug("Current Time: %s, Expected Time: %s, Tolerance: %s",
                  converted_time, time.mktime(expected_time_struct), tolerance)

        # Verify the clock is set within the tolerance
        return abs(converted_time - time.mktime(expected_time_struct)) <= tolerance

    ###
    #   Test scheduled events
    ###
    def assert_compass_calibration(self):
        """
        Verify a calibration particle was generated
        """
        raise NotImplementedException()

    def assert_acquire_status(self):
        """
        Verify a status particle was generated
        """
        raise NotImplementedException()

    def assert_clock_sync(self):
        """
        Verify the clock is set to at least the current date
        """
        dt = self.assert_get(TeledyneParameter.TIME)
        lt = time.strftime("%Y/%m/%d,%H:%M:%S", time.gmtime(time.mktime(time.localtime())))
        self.assertTrue(lt[:13].upper() in dt.upper())

    def assert_acquire_status(self):
        """
        Assert that Acquire_status return the following ASYNC particles
        """
        self.assert_async_particle_generation(DataParticleType.ADCP_COMPASS_CALIBRATION, self.assert_calibration,
                                              timeout=60)
        self.assert_async_particle_generation(DataParticleType.ADCP_ANCILLARY_SYSTEM_DATA, self.assert_ancillary_data,
                                              timeout=60)
        self.assert_async_particle_generation(DataParticleType.ADCP_TRANSMIT_PATH, self.assert_transmit_data,
                                              timeout=60)

    def assert_transmit_data(self, data_particle, verify_values=True):
        """
        Verify an adcpt ps0 data particle
        @param data_particle: ADCP_PS0DataParticle data particle
        @param verify_values: bool, should we verify parameter values
        """
        self.assert_data_particle_header(data_particle, DataParticleType.ADCP_TRANSMIT_PATH)

    def assert_ancillary_data(self, data_particle, verify_values=True):
        """
        Verify an adcp ps0 data particle
        @param data_particle: ADCP_PS0DataParticle data particle
        @param verify_values: bool, should we verify parameter values
        """
        self.assert_data_particle_header(data_particle, DataParticleType.ADCP_ANCILLARY_SYSTEM_DATA)

    def assert_calibration(self, data_particle, verify_values=True):
        self.assert_data_particle_header(data_particle, DataParticleType.ADCP_COMPASS_CALIBRATION)

    def test_scheduled_interval_clock_sync_command(self):
        """
        Verify the scheduled clock sync is triggered and functions as expected
        """
        self.assert_initialize_driver()
        self.assert_set(TeledyneParameter.CLOCK_SYNCH_INTERVAL, '00:00:04')
        time.sleep(10)

        self.assert_set(TeledyneParameter.CLOCK_SYNCH_INTERVAL, '00:00:00')
        self.assert_current_state(TeledyneProtocolState.COMMAND)

    def test_scheduled_interval_acquire_status_command(self):
        """
        Verify the scheduled clock sync is triggered and functions as expected
        """
        self.assert_initialize_driver()
        self.assert_set(TeledyneParameter.GET_STATUS_INTERVAL, '00:00:04')
        time.sleep(10)
        self.assert_acquire_status()

        self.assert_set(TeledyneParameter.GET_STATUS_INTERVAL, '00:00:00')
        self.assert_current_state(TeledyneProtocolState.COMMAND)

        failed = False
        try:
            self.assert_acquire_status()
            failed = True
        except AssertionError:
            pass
        self.assertFalse(failed)

    @unittest.skip('It takes many hours for this test')
    def test_scheduled_acquire_status_autosample(self):
        """
        Verify the scheduled acquire status is triggered and functions as expected
        """

        self.assert_initialize_driver()
        self.assert_current_state(TeledyneProtocolState.COMMAND)
        self.assert_set(TeledyneParameter.GET_STATUS_INTERVAL, '00:00:04')
        self.assert_driver_command(TeledyneProtocolEvent.START_AUTOSAMPLE)
        self.assert_current_state(TeledyneProtocolState.AUTOSAMPLE)
        time.sleep(10)
        self.assert_acquire_status()
        self.assert_driver_command(TeledyneProtocolEvent.STOP_AUTOSAMPLE)
        self.assert_current_state(TeledyneProtocolState.COMMAND)
        self.assert_set(TeledyneParameter.GET_STATUS_INTERVAL, '00:00:00')
        self.assert_current_state(TeledyneProtocolState.COMMAND)

    @unittest.skip('It takes many hours for this test')
    def test_scheduled_clock_sync_autosample(self):
        """
        Verify the scheduled clock sync is triggered and functions as expected
        """

        self.assert_initialize_driver()
        self.assert_current_state(TeledyneProtocolState.COMMAND)
        self.assert_set(TeledyneParameter.CLOCK_SYNCH_INTERVAL, '00:00:04')
        self.assert_driver_command(TeledyneProtocolEvent.START_AUTOSAMPLE)
        self.assert_current_state(TeledyneProtocolState.AUTOSAMPLE)
        time.sleep(10)
        self.assert_driver_command(TeledyneProtocolEvent.STOP_AUTOSAMPLE)
        self.assert_current_state(TeledyneProtocolState.COMMAND)
        self.assert_set(TeledyneParameter.CLOCK_SYNCH_INTERVAL, '00:00:00')
        self.assert_current_state(TeledyneProtocolState.COMMAND)

    @unittest.skip('It takes time')
    def test_acquire_status(self):
        """
        Verify the acquire_status command is functional
        """

        self.assert_initialize_driver()
        self.assert_driver_command(TeledyneProtocolEvent.ACQUIRE_STATUS)
        self.assert_acquire_status()

    # This will be called by test_set_range()
    def _tst_set_xmit_power(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # XMIT_POWER:  -- Int 0-255
        self.assert_set(TeledyneParameter.XMIT_POWER, 0)
        self.assert_set(TeledyneParameter.XMIT_POWER, 128)
        self.assert_set(TeledyneParameter.XMIT_POWER, 254)

        self.assert_set_exception(TeledyneParameter.XMIT_POWER, "LEROY JENKINS")
        self.assert_set_exception(TeledyneParameter.XMIT_POWER, 256)
        self.assert_set_exception(TeledyneParameter.XMIT_POWER, -1)
        self.assert_set_exception(TeledyneParameter.XMIT_POWER, 3.1415926)
        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.XMIT_POWER, self._driver_parameters[TeledyneParameter.XMIT_POWER][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_speed_of_sound(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # SPEED_OF_SOUND:  -- Int 1485 (1400 - 1600)
        self.assert_set(TeledyneParameter.SPEED_OF_SOUND, 1400)
        self.assert_set(TeledyneParameter.SPEED_OF_SOUND, 1450)
        self.assert_set(TeledyneParameter.SPEED_OF_SOUND, 1500)
        self.assert_set(TeledyneParameter.SPEED_OF_SOUND, 1550)
        self.assert_set(TeledyneParameter.SPEED_OF_SOUND, 1600)

        self.assert_set_exception(TeledyneParameter.SPEED_OF_SOUND, 0)
        self.assert_set_exception(TeledyneParameter.SPEED_OF_SOUND, 1399)

        self.assert_set_exception(TeledyneParameter.SPEED_OF_SOUND, 1601)
        self.assert_set_exception(TeledyneParameter.SPEED_OF_SOUND, "LEROY JENKINS")
        self.assert_set_exception(TeledyneParameter.SPEED_OF_SOUND, -256)
        self.assert_set_exception(TeledyneParameter.SPEED_OF_SOUND, -1)
        self.assert_set_exception(TeledyneParameter.SPEED_OF_SOUND, 3.1415926)

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.SPEED_OF_SOUND,
                        self._driver_parameters[TeledyneParameter.SPEED_OF_SOUND][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_salinity(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # SALINITY:  -- Int (0 - 40)
        self.assert_set(TeledyneParameter.SALINITY, 1)
        self.assert_set(TeledyneParameter.SALINITY, 10)
        self.assert_set(TeledyneParameter.SALINITY, 20)
        self.assert_set(TeledyneParameter.SALINITY, 30)
        self.assert_set(TeledyneParameter.SALINITY, 40)

        self.assert_set_exception(TeledyneParameter.SALINITY, "LEROY JENKINS")

        # AssertionError: Unexpected exception: ES no value match (40 != -1)
        self.assert_set_exception(TeledyneParameter.SALINITY, -1)

        # AssertionError: Unexpected exception: ES no value match (35 != 41)
        self.assert_set_exception(TeledyneParameter.SALINITY, 41)

        self.assert_set_exception(TeledyneParameter.SALINITY, 3.1415926)

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.SALINITY, self._driver_parameters[TeledyneParameter.SALINITY][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_sensor_source(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # SENSOR_SOURCE:  -- (0/1) for 7 positions.
        # note it lacks capability to have a 1 in the #6 position
        self.assert_set(TeledyneParameter.SENSOR_SOURCE, "0000000")
        self.assert_set(TeledyneParameter.SENSOR_SOURCE, "1111101")
        self.assert_set(TeledyneParameter.SENSOR_SOURCE, "1010101")
        self.assert_set(TeledyneParameter.SENSOR_SOURCE, "0101000")
        self.assert_set(TeledyneParameter.SENSOR_SOURCE, "1100100")

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.SENSOR_SOURCE, "1111101")

        self.assert_set_exception(TeledyneParameter.SENSOR_SOURCE, "LEROY JENKINS")
        self.assert_set_exception(TeledyneParameter.SENSOR_SOURCE, 2)
        self.assert_set_exception(TeledyneParameter.SENSOR_SOURCE, -1)
        self.assert_set_exception(TeledyneParameter.SENSOR_SOURCE, "1111112")
        self.assert_set_exception(TeledyneParameter.SENSOR_SOURCE, "11111112")
        self.assert_set_exception(TeledyneParameter.SENSOR_SOURCE, 3.1415926)

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.SENSOR_SOURCE,
                        self._driver_parameters[TeledyneParameter.SENSOR_SOURCE][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_time_per_ensemble(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # TIME_PER_ENSEMBLE:  -- String 01:00:00.00 (hrs:min:sec.sec/100)
        self.assert_set(TeledyneParameter.TIME_PER_ENSEMBLE, "00:00:00.00")
        self.assert_set(TeledyneParameter.TIME_PER_ENSEMBLE, "00:00:01.00")
        self.assert_set(TeledyneParameter.TIME_PER_ENSEMBLE, "00:01:00.00")

        self.assert_set_exception(TeledyneParameter.TIME_PER_ENSEMBLE, '30:30:30.30')
        self.assert_set_exception(TeledyneParameter.TIME_PER_ENSEMBLE, '59:59:59.99')
        self.assert_set_exception(TeledyneParameter.TIME_PER_ENSEMBLE, "LEROY JENKINS")
        self.assert_set_exception(TeledyneParameter.TIME_PER_ENSEMBLE, 2)
        self.assert_set_exception(TeledyneParameter.TIME_PER_ENSEMBLE, -1)
        self.assert_set_exception(TeledyneParameter.TIME_PER_ENSEMBLE, '99:99:99.99')
        self.assert_set_exception(TeledyneParameter.TIME_PER_ENSEMBLE, '-1:-1:-1.+1')
        self.assert_set_exception(TeledyneParameter.TIME_PER_ENSEMBLE, 3.1415926)

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.TIME_PER_ENSEMBLE,
                        self._driver_parameters[TeledyneParameter.TIME_PER_ENSEMBLE][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_pitch(self):
        ###
        #   test get set of a variety of parameter ranges
        ###
        # PITCH:  -- Int -6000 to 6000
        self.assert_set(TeledyneParameter.PITCH, -6000)
        self.assert_set(TeledyneParameter.PITCH, -4000)
        self.assert_set(TeledyneParameter.PITCH, -2000)
        self.assert_set(TeledyneParameter.PITCH, -1)
        self.assert_set(TeledyneParameter.PITCH, 0)
        self.assert_set(TeledyneParameter.PITCH, 1)
        self.assert_set(TeledyneParameter.PITCH, 2000)
        self.assert_set(TeledyneParameter.PITCH, 4000)
        self.assert_set(TeledyneParameter.PITCH, 6000)

        self.assert_set_exception(TeledyneParameter.PITCH, "LEROY JENKINS")
        self.assert_set_exception(TeledyneParameter.PITCH, -6001)
        self.assert_set_exception(TeledyneParameter.PITCH, 6001)
        self.assert_set_exception(TeledyneParameter.PITCH, 3.1415926)

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.PITCH, self._driver_parameters[TeledyneParameter.PITCH][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_roll(self):
        ###
        #   test get set of a variety of parameter ranges
        ###
        # ROLL:  -- Int -6000 to 6000
        self.assert_set(TeledyneParameter.ROLL, -6000)
        self.assert_set(TeledyneParameter.ROLL, -4000)
        self.assert_set(TeledyneParameter.ROLL, -2000)
        self.assert_set(TeledyneParameter.ROLL, -1)
        self.assert_set(TeledyneParameter.ROLL, 0)
        self.assert_set(TeledyneParameter.ROLL, 1)
        self.assert_set(TeledyneParameter.ROLL, 2000)
        self.assert_set(TeledyneParameter.ROLL, 4000)
        self.assert_set(TeledyneParameter.ROLL, 6000)

        self.assert_set_exception(TeledyneParameter.ROLL, "LEROY JENKINS")
        self.assert_set_exception(TeledyneParameter.ROLL, -6001)
        self.assert_set_exception(TeledyneParameter.ROLL, 6001)
        self.assert_set_exception(TeledyneParameter.ROLL, 3.1415926)
        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.ROLL, self._driver_parameters[TeledyneParameter.ROLL][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_time_per_ping(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # TIME_PER_PING: '00:01.00'
        self.assert_set(TeledyneParameter.TIME_PER_PING, '01:00.00')
        self.assert_set(TeledyneParameter.TIME_PER_PING, '59:59.99')
        self.assert_set(TeledyneParameter.TIME_PER_PING, '30:30.30')

        self.assert_set_exception(TeledyneParameter.TIME_PER_PING, "LEROY JENKINS")
        self.assert_set_exception(TeledyneParameter.TIME_PER_PING, 2)
        self.assert_set_exception(TeledyneParameter.TIME_PER_PING, -1)
        self.assert_set_exception(TeledyneParameter.TIME_PER_PING, '99:99.99')
        self.assert_set_exception(TeledyneParameter.TIME_PER_PING, '-1:-1.+1')
        self.assert_set_exception(TeledyneParameter.TIME_PER_PING, 3.1415926)

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.TIME_PER_PING,
                        self._driver_parameters[TeledyneParameter.TIME_PER_PING][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_false_target_threshold(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # FALSE_TARGET_THRESHOLD: string of 0-255,0-255
        self.assert_set(TeledyneParameter.FALSE_TARGET_THRESHOLD, "000,000")
        self.assert_set(TeledyneParameter.FALSE_TARGET_THRESHOLD, "255,000")
        self.assert_set(TeledyneParameter.FALSE_TARGET_THRESHOLD, "000,255")
        self.assert_set(TeledyneParameter.FALSE_TARGET_THRESHOLD, "255,255")

        self.assert_set_exception(TeledyneParameter.FALSE_TARGET_THRESHOLD, "256,000")
        self.assert_set_exception(TeledyneParameter.FALSE_TARGET_THRESHOLD, "256,255")
        self.assert_set_exception(TeledyneParameter.FALSE_TARGET_THRESHOLD, "000,256")
        self.assert_set_exception(TeledyneParameter.FALSE_TARGET_THRESHOLD, "255,256")
        self.assert_set_exception(TeledyneParameter.FALSE_TARGET_THRESHOLD, -1)

        self.assert_set_exception(TeledyneParameter.FALSE_TARGET_THRESHOLD, "LEROY JENKINS")

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.FALSE_TARGET_THRESHOLD,
                        self._driver_parameters[TeledyneParameter.FALSE_TARGET_THRESHOLD][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_bandwidth_control(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # BANDWIDTH_CONTROL: 0/1,
        self.assert_set(TeledyneParameter.BANDWIDTH_CONTROL, 1)

        self.assert_set_exception(TeledyneParameter.BANDWIDTH_CONTROL, -1)
        self.assert_set_exception(TeledyneParameter.BANDWIDTH_CONTROL, 2)
        self.assert_set_exception(TeledyneParameter.BANDWIDTH_CONTROL, "LEROY JENKINS")
        self.assert_set_exception(TeledyneParameter.BANDWIDTH_CONTROL, 3.1415926)

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.BANDWIDTH_CONTROL,
                        self._driver_parameters[TeledyneParameter.BANDWIDTH_CONTROL][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_correlation_threshold(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # CORRELATION_THRESHOLD: int 064, 0 - 255
        self.assert_set(TeledyneParameter.CORRELATION_THRESHOLD, 50)
        self.assert_set(TeledyneParameter.CORRELATION_THRESHOLD, 100)
        self.assert_set(TeledyneParameter.CORRELATION_THRESHOLD, 150)
        self.assert_set(TeledyneParameter.CORRELATION_THRESHOLD, 200)
        self.assert_set(TeledyneParameter.CORRELATION_THRESHOLD, 255)

        self.assert_set_exception(TeledyneParameter.CORRELATION_THRESHOLD, "LEROY JENKINS")
        self.assert_set_exception(TeledyneParameter.CORRELATION_THRESHOLD, -256)
        self.assert_set_exception(TeledyneParameter.CORRELATION_THRESHOLD, -1)
        self.assert_set_exception(TeledyneParameter.CORRELATION_THRESHOLD, 3.1415926)

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.CORRELATION_THRESHOLD,
                        self._driver_parameters[TeledyneParameter.CORRELATION_THRESHOLD][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_error_velocity_threshold(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # ERROR_VELOCITY_THRESHOLD: int (0-5000 mm/s) NOTE it enforces 0-9999
        # decimals are truncated to ints
        self.assert_set(TeledyneParameter.ERROR_VELOCITY_THRESHOLD, 0)
        self.assert_set(TeledyneParameter.ERROR_VELOCITY_THRESHOLD, 128)
        self.assert_set(TeledyneParameter.ERROR_VELOCITY_THRESHOLD, 2000)
        self.assert_set(TeledyneParameter.ERROR_VELOCITY_THRESHOLD, 5000)

        self.assert_set_exception(TeledyneParameter.ERROR_VELOCITY_THRESHOLD, "LEROY JENKINS")
        self.assert_set_exception(TeledyneParameter.ERROR_VELOCITY_THRESHOLD, -1)
        self.assert_set_exception(TeledyneParameter.ERROR_VELOCITY_THRESHOLD, 10000)
        self.assert_set_exception(TeledyneParameter.ERROR_VELOCITY_THRESHOLD, -3.1415926)
        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.ERROR_VELOCITY_THRESHOLD,
                        self._driver_parameters[TeledyneParameter.ERROR_VELOCITY_THRESHOLD][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_blank_after_transmit(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # BLANK_AFTER_TRANSMIT: int 704, (0 - 9999)
        self.assert_set(TeledyneParameter.BLANK_AFTER_TRANSMIT, 0)
        self.assert_set(TeledyneParameter.BLANK_AFTER_TRANSMIT, 128)
        self.assert_set(TeledyneParameter.BLANK_AFTER_TRANSMIT, 9999)

        self.assert_set_exception(TeledyneParameter.BLANK_AFTER_TRANSMIT, "LEROY JENKINS")
        self.assert_set_exception(TeledyneParameter.BLANK_AFTER_TRANSMIT, -1)
        self.assert_set_exception(TeledyneParameter.BLANK_AFTER_TRANSMIT, 10000)
        self.assert_set_exception(TeledyneParameter.BLANK_AFTER_TRANSMIT, -3.1415926)
        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.BLANK_AFTER_TRANSMIT,
                        self._driver_parameters[TeledyneParameter.BLANK_AFTER_TRANSMIT][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_clip_data_past_bottom(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # CLIP_DATA_PAST_BOTTOM: True/False,
        self.assert_set(TeledyneParameter.CLIP_DATA_PAST_BOTTOM, True)

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.CLIP_DATA_PAST_BOTTOM,
                        self._driver_parameters[TeledyneParameter.CLIP_DATA_PAST_BOTTOM][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_receiver_gain_select(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # RECEIVER_GAIN_SELECT: (0/1),
        self.assert_set(TeledyneParameter.RECEIVER_GAIN_SELECT, 0)
        self.assert_set(TeledyneParameter.RECEIVER_GAIN_SELECT, 1)

        self.assert_set_exception(TeledyneParameter.RECEIVER_GAIN_SELECT, 2)
        self.assert_set_exception(TeledyneParameter.RECEIVER_GAIN_SELECT, -1)

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.RECEIVER_GAIN_SELECT,
                        self._driver_parameters[TeledyneParameter.RECEIVER_GAIN_SELECT][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_number_of_depth_cells(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # NUMBER_OF_DEPTH_CELLS:  -- int (1-255) 100,
        self.assert_set(TeledyneParameter.NUMBER_OF_DEPTH_CELLS, 1)
        self.assert_set(TeledyneParameter.NUMBER_OF_DEPTH_CELLS, 128)

        self.assert_set_exception(TeledyneParameter.NUMBER_OF_DEPTH_CELLS, 256)
        self.assert_set_exception(TeledyneParameter.NUMBER_OF_DEPTH_CELLS, 0)
        self.assert_set_exception(TeledyneParameter.NUMBER_OF_DEPTH_CELLS, -1)

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.NUMBER_OF_DEPTH_CELLS,
                        self._driver_parameters[TeledyneParameter.NUMBER_OF_DEPTH_CELLS][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_pings_per_ensemble(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # PINGS_PER_ENSEMBLE: -- int  (0-16384) 1,
        self.assert_set(TeledyneParameter.PINGS_PER_ENSEMBLE, 0)
        self.assert_set(TeledyneParameter.PINGS_PER_ENSEMBLE, 16384)

        self.assert_set_exception(TeledyneParameter.PINGS_PER_ENSEMBLE, 16385)
        self.assert_set_exception(TeledyneParameter.PINGS_PER_ENSEMBLE, -1)
        self.assert_set_exception(TeledyneParameter.PINGS_PER_ENSEMBLE, 32767)
        self.assert_set_exception(TeledyneParameter.PINGS_PER_ENSEMBLE, 3.1415926)
        self.assert_set_exception(TeledyneParameter.PINGS_PER_ENSEMBLE, "LEROY JENKINS")
        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.PINGS_PER_ENSEMBLE,
                        self._driver_parameters[TeledyneParameter.PINGS_PER_ENSEMBLE][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_depth_cell_size(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # DEPTH_CELL_SIZE: int 80 - 3200
        self.assert_set(TeledyneParameter.DEPTH_CELL_SIZE, 80)

        self.assert_set_exception(TeledyneParameter.DEPTH_CELL_SIZE, 3201)
        self.assert_set_exception(TeledyneParameter.DEPTH_CELL_SIZE, -1)
        self.assert_set_exception(TeledyneParameter.DEPTH_CELL_SIZE, 2)
        self.assert_set_exception(TeledyneParameter.DEPTH_CELL_SIZE, 3.1415926)
        self.assert_set_exception(TeledyneParameter.DEPTH_CELL_SIZE, "LEROY JENKINS")
        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.DEPTH_CELL_SIZE,
                        self._driver_parameters[TeledyneParameter.DEPTH_CELL_SIZE][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_transmit_length(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # TRANSMIT_LENGTH: int 0 to 3200
        self.assert_set(TeledyneParameter.TRANSMIT_LENGTH, 80)
        self.assert_set(TeledyneParameter.TRANSMIT_LENGTH, 3200)

        self.assert_set_exception(TeledyneParameter.TRANSMIT_LENGTH, 3201)
        self.assert_set_exception(TeledyneParameter.TRANSMIT_LENGTH, -1)
        self.assert_set_exception(TeledyneParameter.TRANSMIT_LENGTH, 3.1415926)
        self.assert_set_exception(TeledyneParameter.TRANSMIT_LENGTH, "LEROY JENKINS")

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.TRANSMIT_LENGTH,
                        self._driver_parameters[TeledyneParameter.TRANSMIT_LENGTH][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_ping_weight(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # PING_WEIGHT: (0/1),
        self.assert_set(TeledyneParameter.PING_WEIGHT, 0)
        self.assert_set(TeledyneParameter.PING_WEIGHT, 1)

        self.assert_set_exception(TeledyneParameter.PING_WEIGHT, 2)
        self.assert_set_exception(TeledyneParameter.PING_WEIGHT, -1)
        self.assert_set_exception(TeledyneParameter.PING_WEIGHT, 3.1415926)
        self.assert_set_exception(TeledyneParameter.PING_WEIGHT, "LEROY JENKINS")
        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.PING_WEIGHT,
                        self._driver_parameters[TeledyneParameter.PING_WEIGHT][self.VALUE])

    # This will be called by test_set_range()
    def _tst_set_ambiguity_velocity(self):
        ###
        #   test get set of a variety of parameter ranges
        ###

        # AMBIGUITY_VELOCITY: int 2 - 700
        self.assert_set(TeledyneParameter.AMBIGUITY_VELOCITY, 2)
        self.assert_set(TeledyneParameter.AMBIGUITY_VELOCITY, 333)
        self.assert_set(TeledyneParameter.AMBIGUITY_VELOCITY, 700)

        self.assert_set_exception(TeledyneParameter.AMBIGUITY_VELOCITY, 0)
        self.assert_set_exception(TeledyneParameter.AMBIGUITY_VELOCITY, 1)
        self.assert_set_exception(TeledyneParameter.AMBIGUITY_VELOCITY, -1)
        self.assert_set_exception(TeledyneParameter.AMBIGUITY_VELOCITY, 3.1415926)
        self.assert_set_exception(TeledyneParameter.AMBIGUITY_VELOCITY, "LEROY JENKINS")

        #
        # Reset to good value.
        #
        self.assert_set(TeledyneParameter.AMBIGUITY_VELOCITY,
                        self._driver_parameters[TeledyneParameter.AMBIGUITY_VELOCITY][self.VALUE])

    # ReadOnly parameter setting exception tests
    #@unittest.skip('It takes many hours for this test')
    def test_set_parameter_test(self):
        self.assert_initialize_driver()

        self.assert_set_exception(TeledyneParameter.HEADING_ALIGNMENT, +10000)
        self.assert_set_exception(TeledyneParameter.HEADING_ALIGNMENT, +40000)
        self.assert_set_exception(TeledyneParameter.ENSEMBLE_PER_BURST, 600)
        self.assert_set_exception(TeledyneParameter.ENSEMBLE_PER_BURST, 70000)
        self.assert_set_exception(TeledyneParameter.LATENCY_TRIGGER, 1)
        self.assert_set_exception(TeledyneParameter.DATA_STREAM_SELECTION, 10)
        self.assert_set_exception(TeledyneParameter.DATA_STREAM_SELECTION, 19)
        self.assert_set_exception(TeledyneParameter.BUFFERED_OUTPUT_PERIOD, "00:00:11")


###############################################################################
#                            QUALIFICATION TESTS                              #
# Device specific qualification tests are for                                 #
# testing device specific capabilities                                        #
###############################################################################
@attr('QUAL', group='mi')
class TeledyneQualificationTest(InstrumentDriverQualificationTestCase):
    def setUp(self):
        InstrumentDriverQualificationTestCase.setUp(self)


###############################################################################
#                             PUBLICATION  TESTS                              #
# Device specific publication tests are for                                   #
# testing device specific capabilities                                        #
###############################################################################
@attr('PUB', group='mi')
class TeledynePublicationTest(InstrumentDriverPublicationTestCase):
    def setUp(self):
        InstrumentDriverPublicationTestCase.setUp(self)
