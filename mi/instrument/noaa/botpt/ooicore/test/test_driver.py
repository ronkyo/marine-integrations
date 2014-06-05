"""
@package mi.instrument.noaa.lily.ooicore.test.test_driver
@file marine-integrations/mi/instrument/noaa/ooicore/test/test_driver.py
@author Pete Cable
@brief Test cases for ooicore driver

USAGE:
 Make tests verbose and provide stdout
   * From the IDK
       $ bin/test_driver
       $ bin/test_driver -u [-t testname]
       $ bin/test_driver -i [-t testname]
       $ bin/test_driver -q [-t testname]
"""

import time

import mi.instrument.noaa.botpt.ooicore.particles as particles
from nose.plugins.attrib import attr
from mi.core.log import get_logger
from mi.idk.unit_test import InstrumentDriverTestCase
from mi.idk.unit_test import InstrumentDriverUnitTestCase
from mi.idk.unit_test import InstrumentDriverIntegrationTestCase
from mi.idk.unit_test import InstrumentDriverQualificationTestCase
from mi.idk.unit_test import DriverTestMixin
from mi.idk.unit_test import ParameterTestConfigKey
from mi.idk.unit_test import AgentCapabilityType
from mi.core.instrument.chunker import StringChunker
from mi.core.instrument.instrument_driver import DriverConfigKey
from mi.core.instrument.instrument_driver import ResourceAgentState
from mi.core.exceptions import InstrumentDataException
from mi.instrument.noaa.botpt.ooicore.driver import NEWLINE, Parameter, Capability, InstrumentCommand, \
    ProtocolState, ProtocolEvent, InstrumentDriver, Protocol, ParameterConstraint


__author__ = 'Pete Cable'
__license__ = 'Apache 2.0'

log = get_logger()

# ##
# Driver parameters for the tests
# ##
InstrumentDriverTestCase.initialize(
    driver_module='mi.instrument.noaa.botpt.ooicore.driver',
    driver_class="InstrumentDriver",
    instrument_agent_resource_id='1D644T',
    instrument_agent_name='noaa_botpt_ooicore',
    instrument_agent_packet_config=particles.DataParticleType(),
    driver_startup_config={
        DriverConfigKey.PARAMETERS: {
            Parameter.AUTO_RELEVEL: True,
            Parameter.LEVELING_TIMEOUT: 600,
            Parameter.XTILT_TRIGGER: 300,
            Parameter.YTILT_TRIGGER: 300,
            Parameter.HEAT_DURATION: 1,
            Parameter.OUTPUT_RATE: 40,
            Parameter.SYNC_INTERVAL: 86400,
        }
    }
)

GO_ACTIVE_TIMEOUT = 180

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

INVALID_SAMPLE = "This is an invalid sample; it had better cause an exception." + NEWLINE
LILY_VALID_SAMPLE_01 = "LILY,2013/06/24 23:36:02,-235.500,  25.930,194.30, 26.04,11.96,N9655" + NEWLINE
LILY_VALID_SAMPLE_02 = "LILY,2013/06/24 23:36:04,-235.349,  26.082,194.26, 26.04,11.96,N9655" + NEWLINE
HEAT_VALID_SAMPLE_01 = "HEAT,2013/04/19 22:54:11,-001,0001,0025" + NEWLINE
HEAT_VALID_SAMPLE_02 = "HEAT,2013/04/19 22:54:11,001,0001,0025" + NEWLINE
IRIS_VALID_SAMPLE_01 = "IRIS,2013/05/29 00:25:34, -0.0882, -0.7524,28.45,N8642" + NEWLINE
IRIS_VALID_SAMPLE_02 = "IRIS,2013/05/29 00:25:36, -0.0885, -0.7517,28.49,N8642" + NEWLINE
NANO_VALID_SAMPLE_01 = "NANO,V,2013/08/22 22:48:36.013,13.888533,26.147947328" + NEWLINE
NANO_VALID_SAMPLE_02 = "NANO,P,2013/08/22 23:13:36.000,13.884067,26.172926006" + NEWLINE
#
# DATA_ON_COMMAND_RESPONSE = "LILY,2013/05/29 00:23:34," + LILY_COMMAND_STRING + LILY_DATA_ON + NEWLINE
# DATA_OFF_COMMAND_RESPONSE = "LILY,2013/05/29 00:23:34," + LILY_COMMAND_STRING + LILY_DATA_OFF + NEWLINE
# DUMP_01_COMMAND_RESPONSE = "LILY,2013/05/29 00:22:57," + LILY_COMMAND_STRING + LILY_DUMP_01 + NEWLINE
# DUMP_02_COMMAND_RESPONSE = "LILY,2013/05/29 00:23:34," + LILY_COMMAND_STRING + LILY_DUMP_02 + NEWLINE
# START_LEVELING_COMMAND_RESPONSE = "LILY,2013/05/29 00:23:34," + LILY_COMMAND_STRING + LILY_LEVEL_ON + NEWLINE
# STOP_LEVELING_COMMAND_RESPONSE = "LILY,2013/05/29 00:23:34," + LILY_COMMAND_STRING + LILY_LEVEL_OFF + NEWLINE

BOTPT_FIREHOSE_01 = NEWLINE.join(["NANO,P,2013/05/16 17:03:22.000,14.858126,25.243003840",
                                  "HEAT,2013/04/19 22:54:11,-001,0001,0025",
                                  "IRIS,2013/05/29 00:25:34, -0.0882, -0.7524,28.45,N8642",
                                  "NANO,P,2013/05/16 17:03:22.000,14.858126,25.243003840",
                                  "LILY,2013/06/24 23:36:02,-235.500,  25.930,194.30, 26.04,11.96,N9655",
                                  "HEAT,2013/04/19 22:54:11,-001,0001,0025"])

BOTPT_FIREHOSE_02 = NEWLINE.join(["NANO,P,2013/05/16 17:03:22.000,14.858126,25.243003840",
                                  "HEAT,2013/04/19 22:54:11,-001,0001,0025",
                                  "LILY,2013/06/24 22:36:02,-235.500,  25.930,194.30, 26.04,11.96,N9655",
                                  "IRIS,2013/05/29 00:25:34, -0.0882, -0.7524,28.45,N8642",
                                  "NANO,P,2013/05/16 17:03:22.000,14.858126,25.243003840",
                                  "LILY,2013/06/24 23:36:02,-235.500,  25.930,194.30, 26.04,11.96,N9655",
                                  "HEAT,2013/04/19 22:54:11,-001,0001,0025"])

DUMP_01_STATUS = NEWLINE.join([
    "LILY,2013/06/24 23:35:41,*APPLIED GEOMECHANICS LILY Firmware V2.1 SN-N9655 ID01",
    "LILY,2013/06/24 23:35:41,*01: Vbias= 0.0000 0.0000 0.0000 0.0000",
    "LILY,2013/06/24 23:35:41,*01: Vgain= 0.0000 0.0000 0.0000 0.0000",
    "LILY,2013/06/24 23:35:41,*01: Vmin:  -2.50  -2.50   2.50   2.50",
    "LILY,2013/06/24 23:35:41,*01: Vmax:   2.50   2.50   2.50   2.50",
    "LILY,2013/06/24 23:35:41,*01: a0=    0.00000    0.00000    0.00000    0.00000    0.00000    0.00000",
    "LILY,2013/06/24 23:35:41,*01: a1=    0.00000    0.00000    0.00000    0.00000    0.00000    0.00000",
    "LILY,2013/06/24 23:35:41,*01: a2=    0.00000    0.00000    0.00000    0.00000    0.00000    0.00000",
    "LILY,2013/06/24 23:35:41,*01: a3=    0.00000    0.00000    0.00000    0.00000    0.00000    0.00000",
    "LILY,2013/06/24 23:35:41,*01: Tcoef 0: Ks=           0 Kz=           0 Tcal=           0",
    "LILY,2013/06/24 23:35:41,*01: Tcoef 1: Ks=           0 Kz=           0 Tcal=           0",
    "LILY,2013/06/24 23:35:41,*01: N_SAMP= 360 Xzero=  0.00 Yzero=  0.00",
    "LILY,2013/06/24 23:35:41,*01: TR-PASH-OFF E99-ON  SO-NMEA-SIM XY-EP 19200 baud FV-"])

DUMP_02_STATUS = NEWLINE.join([
    "LILY,2013/06/24 23:36:05,*01: TBias: 5.00",
    "LILY,2013/06/24 23:36:05,*01: Above 0.00(KZMinTemp): kz[0]=           0, kz[1]=           0",
    "LILY,2013/06/24 23:36:05,*01: Below 0.00(KZMinTemp): kz[2]=           0, kz[3]=           0",
    "LILY,2013/06/24 23:36:05,*01: ADCDelay:  310",
    "LILY,2013/06/24 23:36:05,*01: PCA Model: 84833-14",
    "LILY,2013/06/24 23:36:05,*01: Firmware Version: 2.1 Rev D",
    "LILY,2013/06/24 23:36:05,*01: X Ch Gain= 1.0000, Y Ch Gain= 1.0000, Temperature Gain= 1.0000",
    "LILY,2013/06/24 23:36:05,*01: Calibrated in uRadian, Current Output Mode: uRadian",
    "LILY,2013/06/24 23:36:05,*01: Using RS232",
    "LILY,2013/06/24 23:36:05,*01: Real Time Clock: Installed",
    "LILY,2013/06/24 23:36:05,*01: Use RTC for Timing: Yes",
    "LILY,2013/06/24 23:36:05,*01: External Flash: 2162688 Bytes Installed",
    "LILY,2013/06/24 23:36:05,*01: Flash Status (in Samples) (Used/Total): (-1/55424)",
    "LILY,2013/06/24 23:36:05,*01: Low Power Logger Data Rate: -1 Seconds per Sample",
    "LILY,2013/06/24 23:36:05,*01: Calibration method: Dynamic ",
    "LILY,2013/06/24 23:36:05,*01: Positive Limit=330.00   Negative Limit=-330.00 ",
    "IRIS,2013/06/24 23:36:05, -0.0680, -0.3284,28.07,N3616",
    "LILY,2013/06/24 23:36:05,*01: Calibration Points:023  X: Enabled  Y: Enabled",
    "LILY,2013/06/24 23:36:05,*01: Uniaxial (x2) Sensor Type (1)",
    "LILY,2013/06/24 23:36:05,*01: ADC: 16-bit(external)",
    "LILY,2013/06/24 23:36:05,*01: Compass: Installed   Magnetic Declination: 0.000000",
    "LILY,2013/06/24 23:36:05,*01: Compass: Xoffset:   12, Yoffset:  210, Xrange: 1371, Yrange: 1307",
    "LILY,2013/06/24 23:36:05,*01: PID Coeff: iMax:100.0, iMin:-100.0, iGain:0.0150, pGain: 2.50, dGain: 10.0",
    "LILY,2013/06/24 23:36:05,*01: Motor I_limit: 90.0mA",
    "LILY,2013/06/24 23:36:05,*01: Current Time: 01/11/00 02:12:32",
    "LILY,2013/06/24 23:36:06,*01: Supply Voltage: 11.96 Volts",
    "LILY,2013/06/24 23:36:06,*01: Memory Save Mode: Off",
    "LILY,2013/06/24 23:36:06,*01: Outputting Data: Yes",
    "LILY,2013/06/24 23:36:06,*01: Auto Power-Off Recovery Mode: Off",
    "LILY,2013/06/24 23:36:06,*01: Advanced Memory Mode: Off, Delete with XY-MEMD: No"])

LEVELING_STATUS = "LILY,2013/07/24 20:36:27,*  14.667,  81.642,185.21, 33.67,11.59,N9651"
LEVELED_STATUS = "LILY,2013/06/28 17:29:21,*  -2.277,  -2.165,190.81, 25.69,,Leveled!11.87,N9651"
SWITCHING_STATUS = "LILY,2013/06/28 18:04:41,*  -7.390, -14.063,190.91, 25.83,,Switching to Y!11.87,N9651"
X_OUT_OF_RANGE = "LILY,2013/03/22 19:07:28,*-330.000,-330.000,185.45," + \
                 "-6.45,,X Axis out of range, switching to Y!11.37,N9651"
Y_OUT_OF_RANGE = "LILY,2013/03/22 19:07:29,*-330.000,-330.000,184.63, -6.43,,Y Axis out of range!11.34,N9651"

###############################################################################
#                           DRIVER TEST MIXIN                                 #
#     Defines a set of constants and assert methods used for data particle    #
#     verification                                                            #
#                                                                             #
#  In python mixin classes are classes designed such that they wouldn't be    #
#  able to stand on their own, but are inherited by other classes generally   #
#  using multiple inheritance.                                                #
#                                                                             #
# This class defines a configuration structure for testing and common assert  #
# methods for validating data particles.                                      #
###############################################################################


class BotptTestMixinSub(DriverTestMixin):
    TYPE = ParameterTestConfigKey.TYPE
    READONLY = ParameterTestConfigKey.READONLY
    STARTUP = ParameterTestConfigKey.STARTUP
    DA = ParameterTestConfigKey.DIRECT_ACCESS
    VALUE = ParameterTestConfigKey.VALUE
    REQUIRED = ParameterTestConfigKey.REQUIRED
    DEFAULT = ParameterTestConfigKey.DEFAULT
    STATES = ParameterTestConfigKey.STATES

    _driver_parameters = {
        # Parameters defined in the IOS
        Parameter.AUTO_RELEVEL: {TYPE: bool, READONLY: False, DA: False, STARTUP: False},
        Parameter.XTILT_TRIGGER: {TYPE: float, READONLY: False, DA: False, STARTUP: False},
        Parameter.YTILT_TRIGGER: {TYPE: float, READONLY: False, DA: False, STARTUP: False},
        Parameter.LEVELING_TIMEOUT: {TYPE: int, READONLY: False, DA: False, STARTUP: False},
        Parameter.LEVELING_FAILED: {TYPE: bool, READONLY: True, DA: False, STARTUP: False},
        Parameter.OUTPUT_RATE: {TYPE: int, READONLY: False, DA: False, STARTUP: False},
        Parameter.SYNC_INTERVAL: {TYPE: int, READONLY: False, DA: False, STARTUP: False},
    }

    _samples = [LILY_VALID_SAMPLE_01, LILY_VALID_SAMPLE_02, HEAT_VALID_SAMPLE_01, HEAT_VALID_SAMPLE_02,
                IRIS_VALID_SAMPLE_01, IRIS_VALID_SAMPLE_02, NANO_VALID_SAMPLE_01, NANO_VALID_SAMPLE_02,
                LEVELING_STATUS, SWITCHING_STATUS, LEVELED_STATUS, X_OUT_OF_RANGE, Y_OUT_OF_RANGE]

    # _driver_capabilities = {
    #     # capabilities defined in the IOS
    #     Capability.ACQUIRE_STATUS: {STATES: [ProtocolState.COMMAND, ProtocolState.AUTOSAMPLE]},
    #     Capability.START_AUTOSAMPLE: {STATES: [ProtocolState.COMMAND]},
    #     Capability.STOP_AUTOSAMPLE: {STATES: [ProtocolState.AUTOSAMPLE]},
    #     Capability.START_LEVELING: {STATES: [ProtocolState.COMMAND, ProtocolState.AUTOSAMPLE]},
    #     Capability.STOP_LEVELING: {STATES: [ProtocolState.COMMAND_LEVELING, ProtocolState.AUTOSAMPLE_LEVELING]},
    # }
    #
    # _capabilities = {
    #     ProtocolState.UNKNOWN: ['DRIVER_EVENT_DISCOVER'],
    #     ProtocolState.COMMAND: ['DRIVER_EVENT_ACQUIRE_STATUS',
    #                             'DRIVER_EVENT_GET',
    #                             'DRIVER_EVENT_SET',
    #                             'DRIVER_EVENT_START_AUTOSAMPLE',
    #                             'DRIVER_EVENT_START_DIRECT',
    #                             'EXPORTED_INSTRUMENT_START_LEVELING'],
    #     ProtocolState.AUTOSAMPLE: ['DRIVER_EVENT_STOP_AUTOSAMPLE',
    #                                'DRIVER_EVENT_ACQUIRE_STATUS',
    #                                'DRIVER_EVENT_GET',
    #                                'DRIVER_EVENT_SET',
    #                                'EXPORTED_INSTRUMENT_START_LEVELING'],
    #     ProtocolState.DIRECT_ACCESS: ['DRIVER_EVENT_STOP_DIRECT',
    #                                   'EXECUTE_DIRECT'],
    #     ProtocolState.COMMAND_LEVELING: ['EXPORTED_INSTRUMENT_STOP_LEVELING',
    #                                      'DRIVER_EVENT_GET',
    #                                      'DRIVER_EVENT_SET',
    #                                      'PROTOCOL_EVENT_LEVELING_TIMEOUT'],
    #     ProtocolState.AUTOSAMPLE_LEVELING: ['EXPORTED_INSTRUMENT_STOP_LEVELING',
    #                                         'DRIVER_EVENT_GET',
    #                                         'DRIVER_EVENT_SET',
    #                                         'PROTOCOL_EVENT_LEVELING_TIMEOUT']
    # }
    #
    # _sample_chunks = [LEVELED_STATUS, VALID_SAMPLE_01, VALID_SAMPLE_02, DUMP_01_STATUS, DUMP_02_STATUS]
    #
    # _build_parsed_values_items = [
    #     (INVALID_SAMPLE, LILYDataParticle, False),
    #     (VALID_SAMPLE_01, LILYDataParticle, False),
    #     (VALID_SAMPLE_02, LILYDataParticle, False),
    #     (DUMP_01_STATUS, BotptStatus01Particle, True),
    #     (DUMP_02_STATUS, LILYStatus02Particle, True),
    # ]
    #
    # _command_response_items = [
    #     (DATA_ON_COMMAND_RESPONSE, LILY_DATA_ON),
    #     (DATA_OFF_COMMAND_RESPONSE, LILY_DATA_OFF),
    #     (DUMP_01_COMMAND_RESPONSE, LILY_DUMP_01),
    #     (DUMP_02_COMMAND_RESPONSE, LILY_DUMP_02),
    #     (START_LEVELING_COMMAND_RESPONSE, LILY_LEVEL_ON),
    #     (STOP_LEVELING_COMMAND_RESPONSE, LILY_LEVEL_OFF),
    # ]
    #
    # _test_handlers_items = [
    #     ('_handler_command_start_autosample', ProtocolState.COMMAND, ProtocolState.AUTOSAMPLE, LILY_DATA_ON),
    #     ('_handler_autosample_stop_autosample', ProtocolState.AUTOSAMPLE, ProtocolState.COMMAND, LILY_DATA_OFF),
    #     ('_handler_command_autosample_acquire_status', ProtocolState.COMMAND, None, LILY_DUMP_02),
    #     ('_handler_autosample_start_leveling', ProtocolState.AUTOSAMPLE,
    #      ProtocolState.AUTOSAMPLE_LEVELING, LILY_LEVEL_ON),
    #     ('_handler_stop_leveling', ProtocolState.AUTOSAMPLE_LEVELING,
    #      ProtocolState.AUTOSAMPLE, LILY_DATA_ON),
    #     ('_handler_command_start_leveling', ProtocolState.COMMAND,
    #      ProtocolState.COMMAND_LEVELING, LILY_LEVEL_ON),
    #     ('_handler_stop_leveling', ProtocolState.COMMAND_LEVELING,
    #      ProtocolState.COMMAND, LILY_LEVEL_OFF),
    # ]

    lily_sample_parameters_01 = {
        particles.LilySampleParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'LILY', REQUIRED: True},
        particles.LilySampleParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/06/24 23:36:02', REQUIRED: True},
        particles.LilySampleParticleKey.X_TILT: {TYPE: float, VALUE: -235.500, REQUIRED: True},
        particles.LilySampleParticleKey.Y_TILT: {TYPE: float, VALUE: 25.930, REQUIRED: True},
        particles.LilySampleParticleKey.MAG_COMPASS: {TYPE: float, VALUE: 194.30, REQUIRED: True},
        particles.LilySampleParticleKey.TEMP: {TYPE: float, VALUE: 26.04, REQUIRED: True},
        particles.LilySampleParticleKey.SUPPLY_VOLTS: {TYPE: float, VALUE: 11.96, REQUIRED: True},
        particles.LilySampleParticleKey.SN: {TYPE: unicode, VALUE: 'N9655', REQUIRED: True},
        particles.LilySampleParticleKey.OUT_OF_RANGE: {TYPE: bool, VALUE: False, REQUIRED: True}
    }

    lily_sample_parameters_02 = {
        particles.LilySampleParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'LILY', REQUIRED: True},
        particles.LilySampleParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/06/24 23:36:04', REQUIRED: True},
        particles.LilySampleParticleKey.X_TILT: {TYPE: float, VALUE: -235.349, REQUIRED: True},
        particles.LilySampleParticleKey.Y_TILT: {TYPE: float, VALUE: 26.082, REQUIRED: True},
        particles.LilySampleParticleKey.MAG_COMPASS: {TYPE: float, VALUE: 194.26, REQUIRED: True},
        particles.LilySampleParticleKey.TEMP: {TYPE: float, VALUE: 26.04, REQUIRED: True},
        particles.LilySampleParticleKey.SUPPLY_VOLTS: {TYPE: float, VALUE: 11.96, REQUIRED: True},
        particles.LilySampleParticleKey.SN: {TYPE: unicode, VALUE: 'N9655', REQUIRED: True},
        particles.LilySampleParticleKey.OUT_OF_RANGE: {TYPE: bool, VALUE: False, REQUIRED: True}
    }

    nano_sample_parameters_01 = {
        particles.NanoSampleParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'NANO', REQUIRED: True},
        particles.NanoSampleParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/08/22 22:48:36.013', REQUIRED: True},
        particles.NanoSampleParticleKey.PRESSURE: {TYPE: float, VALUE: 13.888533, REQUIRED: True},
        particles.NanoSampleParticleKey.TEMP: {TYPE: float, VALUE: 26.147947328, REQUIRED: True},
        particles.NanoSampleParticleKey.PPS_SYNC: {TYPE: unicode, VALUE: u'V', REQUIRED: True},
    }

    nano_sample_parameters_02 = {
        particles.NanoSampleParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'NANO', REQUIRED: True},
        particles.NanoSampleParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/08/22 23:13:36.000', REQUIRED: True},
        particles.NanoSampleParticleKey.PRESSURE: {TYPE: float, VALUE: 13.884067, REQUIRED: True},
        particles.NanoSampleParticleKey.TEMP: {TYPE: float, VALUE: 26.172926006, REQUIRED: True},
        particles.NanoSampleParticleKey.PPS_SYNC: {TYPE: unicode, VALUE: u'P', REQUIRED: True},
    }

    iris_sample_parameters_01 = {
        particles.IrisSampleParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'IRIS', REQUIRED: True},
        particles.IrisSampleParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/05/29 00:25:34', REQUIRED: True},
        particles.IrisSampleParticleKey.X_TILT: {TYPE: float, VALUE: -0.0882, REQUIRED: True},
        particles.IrisSampleParticleKey.Y_TILT: {TYPE: float, VALUE: -0.7524, REQUIRED: True},
        particles.IrisSampleParticleKey.TEMP: {TYPE: float, VALUE: 28.45, REQUIRED: True},
        particles.IrisSampleParticleKey.SN: {TYPE: unicode, VALUE: 'N8642', REQUIRED: True}
    }

    iris_sample_parameters_02 = {
        particles.IrisSampleParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'IRIS', REQUIRED: True},
        particles.IrisSampleParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/05/29 00:25:36', REQUIRED: True},
        particles.IrisSampleParticleKey.X_TILT: {TYPE: float, VALUE: -0.0885, REQUIRED: True},
        particles.IrisSampleParticleKey.Y_TILT: {TYPE: float, VALUE: -0.7517, REQUIRED: True},
        particles.IrisSampleParticleKey.TEMP: {TYPE: float, VALUE: 28.49, REQUIRED: True},
        particles.IrisSampleParticleKey.SN: {TYPE: unicode, VALUE: 'N8642', REQUIRED: True}
    }

    heat_sample_parameters_01 = {
        particles.HeatSampleParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'HEAT', REQUIRED: True},
        particles.HeatSampleParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/04/19 22:54:11', REQUIRED: True},
        particles.HeatSampleParticleKey.X_TILT: {TYPE: int, VALUE: -1, REQUIRED: True},
        particles.HeatSampleParticleKey.Y_TILT: {TYPE: int, VALUE: 1, REQUIRED: True},
        particles.HeatSampleParticleKey.TEMP: {TYPE: int, VALUE: 25, REQUIRED: True}
    }

    heat_sample_parameters_02 = {
        particles.HeatSampleParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'HEAT', REQUIRED: True},
        particles.HeatSampleParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/04/19 22:54:11', REQUIRED: True},
        particles.HeatSampleParticleKey.X_TILT: {TYPE: int, VALUE: 1, REQUIRED: True},
        particles.HeatSampleParticleKey.Y_TILT: {TYPE: int, VALUE: 1, REQUIRED: True},
        particles.HeatSampleParticleKey.TEMP: {TYPE: int, VALUE: 25, REQUIRED: True}
    }

    lily_status_parameters_01 = {
        particles.BotptStatusParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'LILY', REQUIRED: True},
        particles.BotptStatusParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/06/24 23:35:41', REQUIRED: True},
        particles.BotptStatusParticleKey.STATUS: {TYPE: unicode, VALUE: u'LILY', REQUIRED: True},
    }

    lily_status_parameters_02 = {
        particles.BotptStatusParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'LILY', REQUIRED: True},
        particles.BotptStatusParticleKey.TIME: {TYPE: unicode, VALUE: u'LILY,2013/06/24 23:36:05', REQUIRED: True},
        particles.BotptStatusParticleKey.STATUS: {TYPE: unicode, VALUE: u'LILY', REQUIRED: True},
    }

    iris_status_parameters_01 = {
        particles.BotptStatusParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'IRIS', REQUIRED: True},
        particles.BotptStatusParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/06/24 23:35:41', REQUIRED: True},
        particles.BotptStatusParticleKey.STATUS: {TYPE: unicode, VALUE: u'LILY', REQUIRED: True},
    }

    iris_status_parameters_02 = {
        particles.BotptStatusParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'IRIS', REQUIRED: True},
        particles.BotptStatusParticleKey.TIME: {TYPE: unicode, VALUE: u'LILY,2013/06/24 23:36:05', REQUIRED: True},
        particles.BotptStatusParticleKey.STATUS: {TYPE: unicode, VALUE: u'LILY', REQUIRED: True},
    }

    nano_status_parameters_01 = {
        particles.BotptStatusParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'NANO', REQUIRED: True},
        particles.BotptStatusParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/06/24 23:35:41', REQUIRED: True},
        particles.BotptStatusParticleKey.STATUS: {TYPE: unicode, VALUE: u'LILY', REQUIRED: True},
    }

    syst_status_parameters_01 = {
        particles.BotptStatusParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'SYST', REQUIRED: True},
        particles.BotptStatusParticleKey.TIME: {TYPE: unicode, VALUE: u'LILY,2013/06/24 23:36:05', REQUIRED: True},
        particles.BotptStatusParticleKey.STATUS: {TYPE: unicode, VALUE: u'LILY', REQUIRED: True},
    }

    lily_leveling_parameters = {
        particles.LilyLevelingParticleKey.SENSOR_ID: {TYPE: unicode, VALUE: u'LILY', REQUIRED: True},
        particles.LilyLevelingParticleKey.TIME: {TYPE: unicode, VALUE: u'2013/06/24 23:36:02', REQUIRED: True},
        particles.LilyLevelingParticleKey.X_TILT: {TYPE: float, VALUE: -235.500, REQUIRED: True},
        particles.LilyLevelingParticleKey.Y_TILT: {TYPE: float, VALUE: 25.930, REQUIRED: True},
        particles.LilyLevelingParticleKey.MAG_COMPASS: {TYPE: float, VALUE: 194.30, REQUIRED: True},
        particles.LilyLevelingParticleKey.TEMP: {TYPE: float, VALUE: 26.04, REQUIRED: True},
        particles.LilyLevelingParticleKey.SUPPLY_VOLTS: {TYPE: float, VALUE: 11.96, REQUIRED: True},
        particles.LilyLevelingParticleKey.SN: {TYPE: unicode, VALUE: 'N9655', REQUIRED: True},
        particles.LilyLevelingParticleKey.STATUS: {TYPE: unicode, VALUE: 'None', REQUIRED: True}
    }


    def assert_particle(self, data_particle, particle_type, particle_keys, sample_data, verify_values=False):
        """
        Verify sample particle
        @param data_particle: data particle
        @param particle_type: particle type
        @param particle_keys: particle data keys
        @param sample_data: sample values to verify against
        @param verify_values: bool, should we verify parameter values
        """
        self.assert_data_particle_keys(particle_keys, sample_data)
        self.assert_data_particle_header(data_particle, particle_type, require_instrument_timestamp=True)
        self.assert_data_particle_parameters(data_particle, sample_data, verify_values)

    def assert_particle_lily_sample_01(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.LILY_SAMPLE,
                             particles.LilySampleParticleKey, self.lily_sample_parameters_01, verify_values)

    def assert_particle_lily_sample_02(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.LILY_SAMPLE,
                             particles.LilySampleParticleKey, self.lily_sample_parameters_02, verify_values)

    def assert_particle_nano_sample_01(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.NANO_SAMPLE,
                             particles.NanoSampleParticleKey, self.nano_sample_parameters_01, verify_values)

    def assert_particle_nano_sample_02(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.NANO_SAMPLE,
                             particles.NanoSampleParticleKey, self.nano_sample_parameters_02, verify_values)

    def assert_particle_iris_sample_01(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.IRIS_SAMPLE,
                             particles.IrisSampleParticleKey, self.iris_sample_parameters_01, verify_values)

    def assert_particle_iris_sample_02(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.IRIS_SAMPLE,
                             particles.IrisSampleParticleKey, self.iris_sample_parameters_02, verify_values)

    def assert_particle_heat_sample_01(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.IRIS_SAMPLE,
                             particles.HeatSampleParticleKey, self.heat_sample_parameters_01, verify_values)

    def assert_particle_heat_sample_02(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.IRIS_SAMPLE,
                             particles.HeatSampleParticleKey, self.heat_sample_parameters_02, verify_values)

    def assert_particle_lily_status_01(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.LILY_STATUS1,
                             particles.BotptStatusParticleKey, self.lily_status_parameters_01, verify_values)

    def assert_particle_lily_status_02(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.LILY_STATUS2,
                             particles.BotptStatusParticleKey, self.lily_status_parameters_02, verify_values)

    def assert_particle_iris_status_01(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.IRIS_STATUS1,
                             particles.BotptStatusParticleKey, self.iris_status_parameters_01, verify_values)

    def assert_particle_iris_status_02(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.IRIS_STATUS2,
                             particles.BotptStatusParticleKey, self.iris_status_parameters_02, verify_values)

    def assert_particle_syst_status(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.SYST_STATUS,
                             particles.BotptStatusParticleKey, self.syst_status_parameters_01, verify_values)

    def assert_particle_nano_status(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.NANO_STATUS,
                             particles.BotptStatusParticleKey, self.nano_status_parameters_01, verify_values)

    def assert_particle_lily_leveling(self, data_particle, verify_values=False):
        self.assert_particle(data_particle, particles.DataParticleType.LILY_LEVELING,
                             particles.LilyLevelingParticleKey, self.lily_leveling_parameters_01, verify_values)


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
# noinspection PyProtectedMember,PyUnusedLocal
@attr('UNIT', group='mi')
class DriverUnitTest(InstrumentDriverUnitTestCase, BotptTestMixinSub):
    def setUp(self):
        InstrumentDriverUnitTestCase.setUp(self)

    def test_connect(self, initial_protocol_state=ProtocolState.COMMAND):
        driver = InstrumentDriver(self._got_data_event_callback)
        self.assert_initialize_driver(driver, initial_protocol_state)
        driver._protocol.set_init_params(self.test_config.driver_startup_config)
        driver._protocol._init_params()
        return driver

    def test_got_data(self):
        """
        Verify sample data passed through the got data method produces the correct data particles
        """
        driver = self.test_connect()

        self.assert_particle_published(driver, LILY_VALID_SAMPLE_01, self.assert_particle_lily_sample_01, True)
        self.assert_particle_published(driver, LILY_VALID_SAMPLE_02, self.assert_particle_lily_sample_02, True)
        self.assert_particle_published(driver, NANO_VALID_SAMPLE_01, self.assert_particle_nano_sample_01, True)
        self.assert_particle_published(driver, NANO_VALID_SAMPLE_02, self.assert_particle_nano_sample_02, True)
        self.assert_particle_published(driver, IRIS_VALID_SAMPLE_01, self.assert_particle_iris_sample_01, True)
        self.assert_particle_published(driver, IRIS_VALID_SAMPLE_02, self.assert_particle_iris_sample_02, True)
        self.assert_particle_published(driver, HEAT_VALID_SAMPLE_01, self.assert_particle_heat_sample_01, True)
        self.assert_particle_published(driver, HEAT_VALID_SAMPLE_02, self.assert_particle_heat_sample_02, True)

    def test_combined_samples(self):
        """
        Verify combined samples produce the correct number of chunks
        """
        chunker = StringChunker(Protocol.sieve_function)
        ts = self.get_ntp_timestamp()
        samples = [(BOTPT_FIREHOSE_01, 6),
                   (BOTPT_FIREHOSE_02, 7)]

        for data, num_samples in samples:
            chunker.add_chunk(data, ts)
            results = []
            while True:
                timestamp, result = chunker.get_next_data()
                if result:
                    results.append(result)
                    self.assertTrue(result in data)
                    self.assertEqual(timestamp, ts)
                else:
                    break

            self.assertEqual(len(results), num_samples)

    def test_chunker(self):
        chunker = StringChunker(Protocol.sieve_function)
        ts = self.get_ntp_timestamp()

        for sample in self._samples:
            chunker.add_chunk(sample, ts)
            (timestamp, result) = chunker.get_next_data()
            self.assertEqual(result, sample)
            self.assertEqual(timestamp, ts)
            (timestamp, result) = chunker.get_next_data()
            self.assertEqual(result, None)

    def test_start_stop_autosample(self):
        driver = self.test_connect()
        driver._connection.send.side_effect = self.my_send(driver)

        driver._protocol._protocol_fsm.on_event(ProtocolEvent.START_AUTOSAMPLE)
        self.assertEqual(driver._protocol.get_current_state(), ProtocolState.AUTOSAMPLE)

        driver._protocol._protocol_fsm.on_event(ProtocolEvent.STOP_AUTOSAMPLE)
        self.assertEqual(driver._protocol.get_current_state(), ProtocolState.COMMAND)

    def test_status_handlers(self):
        driver = self.test_connect()
        driver._connection.send.side_effect = self.my_send(driver)
        driver._protocol._protocol_fsm.on_event(ProtocolEvent.ACQUIRE_STATUS)

    def test_leveling_timeout(self):
        # stand up the driver in test mode
        driver = self.test_connect()
        driver._connection.send.side_effect = self.my_send(driver)

        # set the leveling timeout to 1 to speed up timeout
        driver._protocol._param_dict.set_value(Parameter.LEVELING_TIMEOUT, 1)
        driver._protocol._protocol_fsm.on_event(ProtocolEvent.START_LEVELING)

        current_state = driver._protocol.get_current_state()
        self.assertEqual(current_state, ProtocolState.COMMAND_LEVELING)

        # sleep for longer than the length of timeout, assert we have returned to COMMAND
        time.sleep(driver._protocol._param_dict.get(Parameter.LEVELING_TIMEOUT) + 1)
        current_state = driver._protocol.get_current_state()
        self.assertEqual(current_state, ProtocolState.COMMAND)

    def test_leveling_complete(self):
        driver = self.test_connect()
        driver._connection.send.side_effect = self.my_send(driver)
        driver._protocol._protocol_fsm.on_event(ProtocolEvent.START_LEVELING)
        # assert we have entered a leveling state
        self.assertEqual(driver._protocol.get_current_state(), ProtocolState.COMMAND_LEVELING)
        # feed in a leveling complete status message
        self._send_port_agent_packet(driver, LEVELED_STATUS)
        # Assert we have returned to the command state
        self.assertEquals(driver._protocol.get_current_state(), ProtocolState.COMMAND)

    def test_leveling_failure(self):
        driver = self.test_connect()
        driver._connection.send.side_effect = self.my_send(driver)
        driver._protocol._protocol_fsm.on_event(ProtocolEvent.START_LEVELING)
        # assert we have entered a leveling state
        self.assertEqual(driver._protocol.get_current_state(), ProtocolState.COMMAND_LEVELING)
        self.assertTrue(driver._protocol._param_dict.get(Parameter.AUTO_RELEVEL))
        # feed in a leveling failed status message
        try:
            self._send_port_agent_packet(driver, X_OUT_OF_RANGE + NEWLINE)
            time.sleep(1)
        except InstrumentDataException:
            self.assertFalse(driver._protocol._param_dict.get(Parameter.AUTO_RELEVEL))
        try:
            self._send_port_agent_packet(driver, Y_OUT_OF_RANGE + NEWLINE)
            time.sleep(1)
        except InstrumentDataException:
            self.assertFalse(driver._protocol._param_dict.get(Parameter.AUTO_RELEVEL))
        self.assertEqual(driver._protocol.get_current_state(), ProtocolState.COMMAND)


###############################################################################
#                            INTEGRATION TESTS                                #
#     Integration test test the direct driver / instrument interaction        #
#     but making direct calls via zeromq.                                     #
#     - Common Integration tests test the driver through the instrument agent #
#     and common for all drivers (minimum requirement for ION ingestion)      #
###############################################################################
@attr('INT', group='mi')
class DriverIntegrationTest(InstrumentDriverIntegrationTestCase, BotptTestMixinSub):
    def setUp(self):
        InstrumentDriverIntegrationTestCase.setUp(self)

    def test_connect(self):
        self.assert_initialize_driver()

    def test_get(self):
        self.assert_initialize_driver()
        for param, value in self.test_config.driver_startup_config['parameters'].items():
            self.assert_get(param, value)

    def test_set(self):
        """
        Test all set commands. Verify all exception cases.
        """
        self.assert_initialize_driver()
        constraints = ParameterConstraint.dict()
        parameters = Parameter.dict()
        startup_config = self.test_config.driver_startup_config['parameters']

        for key in constraints:
            _type, minimum, maximum = constraints[key]
            key = parameters[key]
            if _type in [int, float]:
                # assert we can set in range
                self.assert_set(key, maximum - 1)
                # assert exception when out of range
                self.assert_set_exception(key, maximum + 1)
            elif _type == bool:
                # assert we can toggle a boolean parameter
                if startup_config[key]:
                    self.assert_set(key, False)
                else:
                    self.assert_set(key, True)
            # assert bad types throw an exception
            self.assert_set_exception(key, 'BOGUS')

    def test_auto_relevel(self):
        """
        @brief Test for verifying auto relevel
        """
        self.assert_initialize_driver()

        # set the leveling timeout low, so we're not here for long
        self.assert_set(Parameter.LEVELING_TIMEOUT, 60, no_get=True)

        self.assert_driver_command(Capability.STOP_LEVELING)

        self.assert_driver_command(Capability.START_AUTOSAMPLE, state=ProtocolState.AUTOSAMPLE, delay=5)

        # Set the XTILT to a low threshold so that the driver will
        # automatically start the re-leveling operation
        # NOTE: This test MAY fail if the instrument completes
        # leveling before the triggers have been reset to 300
        self.assert_set(Parameter.XTILT_TRIGGER, 0, no_get=True)

        self.assert_async_particle_generation(particles.LilyLevelingParticle,
                                              self.assert_particle_lily_leveling)

        # Now set the XTILT back to normal so that the driver will not
        # automatically start the re-leveling operation
        self.assert_set(Parameter.XTILT_TRIGGER, 300, no_get=True)

        # wait for a sample particle to indicate leveling is complete
        self.assert_async_particle_generation(particles.LilySampleParticle,
                                              self.assert_particle_lily_sample_01,
                                              timeout=60)

    def test_autosample(self):
        """
        @brief Test for turning data on
        """
        self.assert_initialize_driver()
        self.assert_driver_command(Capability.START_AUTOSAMPLE)

        for particle_type, assert_func in [
            (particles.DataParticleType.LILY_SAMPLE, self.assert_particle_lily_sample_01),
            (particles.DataParticleType.HEAT_SAMPLE, self.assert_particle_heat_sample_01),
            (particles.DataParticleType.IRIS_SAMPLE, self.assert_particle_iris_sample_01),
            (particles.DataParticleType.NANO_SAMPLE, self.assert_particle_nano_sample_01)
        ]:
            self.assert_async_particle_generation(particle_type, assert_func, particle_count=5, timeout=15)

        self.assert_driver_command(Capability.STOP_AUTOSAMPLE, state=ProtocolState.COMMAND, delay=1)

    def test_acquire_status(self):
        """
        @brief Test for acquiring status
        """
        self.assert_initialize_driver()

        # Issue acquire status command

        self.assert_driver_command(Capability.ACQUIRE_STATUS)
        for particle_type, assert_func in [
            (particles.DataParticleType.LILY_STATUS1, self.assert_particle_lily_status_01),
            (particles.DataParticleType.LILY_STATUS2, self.assert_particle_lily_status_02),
            (particles.DataParticleType.IRIS_STATUS1, self.assert_particle_iris_status_01),
            (particles.DataParticleType.IRIS_STATUS2, self.assert_particle_iris_status_02),
            (particles.DataParticleType.NANO_STATUS, self.assert_particle_nano_status),
            (particles.DataParticleType.SYST_STATUS, self.assert_particle_syst_status),
        ]:
            self.assert_async_particle_generation(particle_type, assert_func)

    def test_leveling_complete(self):
        """
        @brief Test for leveling
        """
        self.assert_initialize_driver()

        # go to autosample
        self.assert_driver_command(Capability.START_AUTOSAMPLE, state=ProtocolState.AUTOSAMPLE, delay=5)

        #Issue start leveling command
        self.assert_driver_command(Capability.START_LEVELING)

        # Leveling should complete or abort after DEFAULT_LEVELING_TIMEOUT seconds
        timeout = self.test_config.driver_startup_config[DriverConfigKey.PARAMETERS][Parameter.LEVELING_TIMEOUT]
        self.assert_state_change(ProtocolState.COMMAND, timeout)

        # wait for a sample particle to indicate leveling is complete
        self.assert_async_particle_generation(particles.LilySampleParticle,
                                              self.assert_particle_lily_sample_01)


###############################################################################
#                            QUALIFICATION TESTS                              #
# Device specific qualification tests are for doing final testing of ion      #
# integration.  The generally aren't used for instrument debugging and should #
# be tackled after all unit and integration tests are complete                #
###############################################################################
@attr('QUAL', group='mi')
class DriverQualificationTest(InstrumentDriverQualificationTestCase, BotptTestMixinSub):
    def setUp(self):
        InstrumentDriverQualificationTestCase.setUp(self)

    def assert_cycle(self):
        self.assert_start_autosample()
        self.assert_particle_async(DataParticleType.LILY_PARSED, self.assert_particle_sample_01)
        self.assert_particle_polled(ProtocolEvent.ACQUIRE_STATUS, self.assert_particle_status_01,
                                    DataParticleType.LILY_STATUS_01, sample_count=1)
        self.assert_particle_polled(ProtocolEvent.ACQUIRE_STATUS, self.assert_particle_status_02,
                                    DataParticleType.LILY_STATUS_02, sample_count=1)

        self.assert_stop_autosample()
        self.assert_particle_polled(ProtocolEvent.ACQUIRE_STATUS, self.assert_particle_status_01,
                                    DataParticleType.LILY_STATUS_01, sample_count=1)
        self.assert_particle_polled(ProtocolEvent.ACQUIRE_STATUS, self.assert_particle_status_02,
                                    DataParticleType.LILY_STATUS_02, sample_count=1)

    def test_cycle(self):
        self.assert_enter_command_mode()
        for x in range(4):
            log.debug('test_cycle -- PASS %d', x + 1)
            self.assert_cycle()

    def test_direct_access_telnet_mode(self):
        """
        @brief This test manually tests that the Instrument Driver properly supports
        direct access to the physical instrument. (telnet mode)
        """
        self.assert_direct_access_start_telnet()
        self.assertTrue(self.tcp_client)
        self.tcp_client.send_data(InstrumentCommand.DUMP_SETTINGS_01 + NEWLINE)
        result = self.tcp_client.expect(LILY_DUMP_01)
        self.assertTrue(result, msg='Failed to receive expected response in direct access mode.')
        self.assert_direct_access_stop_telnet()
        self.assert_state_change(ResourceAgentState.COMMAND, ProtocolState.COMMAND, 10)

    def test_leveling(self):
        self.assert_enter_command_mode()
        self.assert_set_parameter(Parameter.LEVELING_TIMEOUT, 5, False)
        self.assert_resource_command(Capability.START_LEVELING)
        self.assert_state_change(ResourceAgentState.BUSY, ProtocolState.COMMAND_LEVELING, 5)
        self.assert_state_change(ResourceAgentState.COMMAND, ProtocolState.COMMAND, 10)

    def test_get_set_parameters(self):
        """
        verify that all parameters can be get set properly, this includes
        ensuring that read only parameters fail on set.
        """
        self.assert_enter_command_mode()
        self.assert_set_parameter(Parameter.LEVELING_TIMEOUT, 5)
        self.assert_set_parameter(Parameter.AUTO_RELEVEL, False)
        self.assert_set_parameter(Parameter.XTILT_TRIGGER, 200)
        self.assert_set_parameter(Parameter.YTILT_TRIGGER, 200)
        self.assert_read_only_parameter(Parameter.LEVELING_FAILED, True)

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
                ProtocolEvent.GET,
                ProtocolEvent.SET,
                ProtocolEvent.START_AUTOSAMPLE,
                ProtocolEvent.ACQUIRE_STATUS,
                ProtocolEvent.START_LEVELING,
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
            ProtocolEvent.GET,
            ProtocolEvent.SET,
            ProtocolEvent.STOP_AUTOSAMPLE,
            ProtocolEvent.ACQUIRE_STATUS,
            ProtocolEvent.START_LEVELING,
        ]

        self.assert_start_autosample()
        self.assert_capabilities(capabilities)
        self.assert_stop_autosample()

        ##################
        #  DA Mode
        ##################

        capabilities[AgentCapabilityType.AGENT_COMMAND] = self._common_agent_commands(ResourceAgentState.DIRECT_ACCESS)
        capabilities[AgentCapabilityType.RESOURCE_COMMAND] = self._common_da_resource_commands()

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

    def test_direct_access_exit_from_autosample(self):
        """
        Verify that direct access mode can be exited while the instrument is
        sampling. This should be done for all instrument states. Override
        this function on a per-instrument basis.
        """
        self.assert_enter_command_mode()

        # go into direct access, and start sampling so ION doesnt know about it
        self.assert_direct_access_start_telnet()
        self.assertTrue(self.tcp_client)
        self.tcp_client.send_data(InstrumentCommand.DATA_ON + NEWLINE)
        self.assertTrue(self.tcp_client.expect(LILY_DATA_ON))
        self.assert_direct_access_stop_telnet()
        self.assert_agent_state(ResourceAgentState.STREAMING)