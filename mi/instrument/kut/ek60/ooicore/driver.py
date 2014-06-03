"""
@package mi.instrument.kut.ek60.ooicore.driver
@file marine-integrations/mi/instrument/kut/ek60/ooicore/driver.py
@author Richard Han
@brief Driver for the ooicore
Release notes:

This Driver supports the Kongsberg UnderWater Technology's EK60 Instrument.
"""
import ftplib
import json
import re
import tempfile
import urllib2
from xml.dom.minidom import parseString
from mi.core.exceptions import InstrumentParameterException, InstrumentException
from mi.core.instrument.driver_dict import DriverDictKey
from mi.core.instrument.protocol_param_dict import ParameterDictVisibility, ParameterDictType
from mock import self
import yaml

__author__ = 'Richard Han'
__license__ = 'Apache 2.0'

import string

from mi.core.log import get_logger ; log = get_logger()

from mi.core.common import BaseEnum
from mi.core.exceptions import SampleException
from mi.core.instrument.instrument_protocol import CommandResponseInstrumentProtocol
from mi.core.instrument.instrument_fsm import InstrumentFSM, ThreadSafeFSM
from mi.core.instrument.instrument_driver import SingleConnectionInstrumentDriver
from mi.core.instrument.instrument_driver import DriverEvent
from mi.core.instrument.instrument_driver import DriverAsyncEvent
from mi.core.instrument.instrument_driver import DriverProtocolState
from mi.core.instrument.instrument_driver import DriverParameter
from mi.core.instrument.instrument_driver import ResourceAgentState
from mi.core.instrument.data_particle import DataParticle
from mi.core.instrument.data_particle import DataParticleKey
from mi.core.instrument.data_particle import CommonDataParticleType
from mi.core.instrument.chunker import StringChunker


# Default Instrument's IP Address
DEFAULT_HOST = "https://10.33.10.143"

# Config file name to be stored on the instrument server
ZPLSC_CONFIG_FILE_NAME = "zplsc_config.ymal"

# newline.
NEWLINE = '\r\n'

# String constants
CONNECTED = "connected"
CURRENT_RAW_FILENAME = "current_raw_filename"
CURRENT_RAW_FILESIZE = "current_raw_filesize"
CURRENT_RUNNING_INTERVAL = "current_running_interval"
CURRENT_UTC_TIME = "current_utc_time"
DURATION = "duration"
ER60_CHANNELS = "er60_channels"
ER60_STATUS  = "er60_status"
EXECUTABLE = "executable"
FILE_PATH = "file_path"
FILE_PREFIX = "file_prefix"
FREQUENCY = "frequency"
FREQ_120K = "120000"
FREQ_200K = "200000"
FREQ_38K = "38000"
FS_ROOT = "fs_root"
GPTS_ENABLED = "gpts_enabled"
HOST = "host"
INTERVAL = "interval"
INTERVALS = "intervals"
RAW_OUTPUT = "raw_output"
MAX_FILE_SIZE = "max_file_size"
MAX_RANGE = "max_range"
MODE = "mode"
NAME = "name"
NEXT_SCHEDULED_INTERVAL = "next_scheduled_interval"
PID = "pid"
PORT = "port"
POWER = "power"
PULSE_LENGTH = "pulse_length"
SAMPLE_INTERVAL = "sample_interval"
SAMPLE_RANGE = "sample_range"
SAVE_INDEX = "save_index"
SAVE_BOTTOM = "save_bottom"
SAVE_RAW = "save_raw"
SCHEDULE = "schedule"
SCHEDULE_FILENAME = "schedule_filename"
SCHEDULED_INTERVAL_REMAINING = "scheduled_interval_remaining"
START_AT = "start_at"
STOP_REPEATING_AT = "stop_repeating_at"
TYPE = "type"
USER_NAME = "ooi"
PASSWORD = "994ef22"


# default timeout.
TIMEOUT = 10

###
#    Driver Constant Definitions
###

class DataParticleType(BaseEnum):
    """
    Data particle types produced by this driver
    """
    RAW = CommonDataParticleType.RAW

class ProtocolState(BaseEnum):
    """
    Instrument protocol states
    """
    UNKNOWN = DriverProtocolState.UNKNOWN
    COMMAND = DriverProtocolState.COMMAND
    AUTOSAMPLE = DriverProtocolState.AUTOSAMPLE
    DIRECT_ACCESS = DriverProtocolState.DIRECT_ACCESS
    TEST = DriverProtocolState.TEST
    CALIBRATE = DriverProtocolState.CALIBRATE

class ProtocolEvent(BaseEnum):
    """
    Protocol events
    """
    ENTER = DriverEvent.ENTER
    EXIT = DriverEvent.EXIT
    GET = DriverEvent.GET
    SET = DriverEvent.SET
    DISCOVER = DriverEvent.DISCOVER
    START_DIRECT = DriverEvent.START_DIRECT
    STOP_DIRECT = DriverEvent.STOP_DIRECT
    ACQUIRE_SAMPLE = DriverEvent.ACQUIRE_SAMPLE
    START_AUTOSAMPLE = DriverEvent.START_AUTOSAMPLE
    STOP_AUTOSAMPLE = DriverEvent.STOP_AUTOSAMPLE
    EXECUTE_DIRECT = DriverEvent.EXECUTE_DIRECT
    CLOCK_SYNC = DriverEvent.CLOCK_SYNC
    ACQUIRE_STATUS = DriverEvent.ACQUIRE_STATUS

class Capability(BaseEnum):
    """
    Protocol events that should be exposed to users (subset of above).
    """
    ACQUIRE_SAMPLE = ProtocolEvent.ACQUIRE_SAMPLE
    START_AUTOSAMPLE = ProtocolEvent.START_AUTOSAMPLE
    STOP_AUTOSAMPLE = ProtocolEvent.STOP_AUTOSAMPLE
    CLOCK_SYNC = ProtocolEvent.CLOCK_SYNC
    ACQUIRE_STATUS  = ProtocolEvent.ACQUIRE_STATUS

class Parameter(DriverParameter):
    """
    Device specific parameters.
    """
    NAME = "name"
    TYPE = "type"
    START_AT = "start_at"
    DURATION = "duration"
    REPEAT_EVERY = "repeat_every"
    STOP_REPEATING_AT = "stop_repeating_at"
    INTERVAL = "interval"
    MAX_RANGE = "max_range"
    MINIMUM_INTERVAL = "minimum_interval"
    NUMBER = "number"
    FREQ_38K_MODE = "freq_38k_mode"
    FREQ_38K_POWER = "freq_38k_power"
    FREQ_38K_PULSE_LENGTH = "freq_38k_Pulse_length"
    FREQ_120K_MODE = "freq_120k_mode"
    FREQ_120K_POWER = "freq_120k_power"
    FREQ_120K_PULSE_LENGTH = "freq_120k_Pulse_length"
    FREQ_200K_MODE = "freq_200k_mode"
    FREQ_200K_POWER = "freq_200k_power"
    FREQ_200K_PULSE_LENGTH = "freq_200k_Pulse_length"
    FTP_IP_ADDRESS = "ftp_ip_address"
    #FTP_PORT_NUMBER = "ftp_port_number"


class Prompt(BaseEnum):
    """
    Device i/o prompts..
    """

class Command(BaseEnum):
    """
    Instrument command strings
    """
    ACQUIRE_STATUS  = 'acquire_status'
    START_AUTOSAMPLE = 'start_autosample'
    STOP_AUTOSAMPLE = 'stop_autosample'
    GET = 'get_param'
    SET = 'set_param'

class DataParticleType(BaseEnum):
    RAW = CommonDataParticleType.RAW
    ZPLSC_STATUS = 'zplsc_status'



###############################################################################
# Data Particles
###############################################################################
class ZPLSCStatusParticleKey(BaseEnum):
    ZPLSC_CONNECTED = "zplcs_connected"                                     # Connected to a running ER 60 instance
    ZPLSC_ACTIVE_38K_MODE = "zplcs_active_38k_mode"                         # 38K Transducer transmit mode
    ZPLSC_ACTIVE_38K_POWER = "zplcs_active_38k_power"                       # 38K Transducer transmit power in W
    ZPLSC_ACTIVE_38K_PULSE_LENGTH = "zplcs_active_38k_pulse_length"         # 38K Transducer transmit pulse length in seconds
    ZPLSC_ACTIVE_38K_SAMPLE_INTERVAL = "zplcs_active_38k_sample_interval"   # Sample interval in seconds
    ZPLSC_ACTIVE_120K_MODE = "zplcs_active_120k_mode"                       # 120K Transducer transmit mode
    ZPLSC_ACTIVE_120K_POWER = "zplcs_active_120k_power"                     # 120K Transducer transmit power in W
    ZPLSC_ACTIVE_120K_PULSE_LENGTH = "zplcs_active_120k_pulse_length"       # 120K Transducer Transmit pulse length in seconds
    ZPLSC_ACTIVE_120K_SAMPLE_INTERVAL = "zplcs_active_120k_sample_interval" # 120K Sample Interval
    ZPLSC_ACTIVE_200K_MODE = "zplcs_active_200k_mode"                       # 200K Transducer transmit mode
    ZPLSC_ACTIVE_200K_POWER = "zplcs_active_200k_power"                     # 200K Transducer transmit power in W
    ZPLSC_ACTIVE_200K_PULSE_LENGTH = "zplcs_active_220k_pulse_length"       # 200K Transducer transmit pulse length in seconds
    ZPLSC_ACTIVE_200K_SAMPLE_INTERVAL = "zplcs_active_120k_sample_interval" # 200K Transducer sample interval
    ZPLSC_CURRENT_UTC_TIME = "zplcs_current_utc_time"                       # Current UTC Time
    ZPLSC_EXECUTABLE = "zplcs_executable"                                   # Executable used to launch ER60
    ZPLSC_FS_ROOT = "zplcs_fs_root"                                         # Root directory where data/logs/configs are stored
    ZPLSC_NEXT_SCHEDULED_INTERVAL = "next_scheduled_interval"               # UTC time of next scheduled interval
    ZPLSC_HOST = "zplcs_host"                                               # Host IP Address
    ZPLSC_PID = "zplcs_pid"                                                 # PID of running ER60 process
    ZPLSC_PORT = "zplsc_port"                                               # Host port number
    ZPLSC_CURRENT_RAW_FILENAME = "zplcs_current_raw_filename"               # File name of the current .raw file
    ZPLSC_CURRENT_RAW_FILESIZE = "zplcs_current_raw_filesize"               # File size of current .raw file
    ZPLSC_FILE_PATH = "zplcs_file_path"                                     # File storage path
    ZPLSC_FILE_PREFIX = "zplcs_file_prefix"                                 # Current file prefix
    ZPLSC_MAX_FILE_SIZE = "zplcs_max_file_size"                             # Maximum file size
    ZPLSC_SAMPLE_RANGE = "zplcs_sample_range"                               # Recording range
    ZPLSC_SAVE_BOTTOM = "zplcs_save_bottom"                                 # Save bottom file
    ZPLSC_SAVE_INDEX = "zplcs_save_index"                                   # Save index file
    ZPLSC_SAVE_RAW = "zplcs_save_raw"                                       # Save raw file
    ZPLSC_SCHEDULED_INTERVAL_REMAINING = "zplcs_scheduled_interval_remaining" # Number of intervals remaining in running schedule
    ZPLSC_GPTS_ENABLED = "zplcs_gpts_enabled"                               # GPTs enabled
    ZPLSC_SCHEDULE_FILENAME = "zplcs_schedule_filename"                     # Filename for .yaml schedule file


class ZPLSCStatusParticle(DataParticle):
    """
    Routines for parsing raw data into a status particle structure. Override
    the building of values, and the rest should come along for free.

    Sample:
    {
    "schedule_filename": "qct_configuration_example_1.yaml",
    "schedule": {
        "max_file_size": 52428800,
        "intervals": [
            {
                "max_range": 220,
                "start_at": "00:00",
                "name": "constant_active",
                "interval": 1000,
                "frequency": {
                    "38000": {
                        "bandwidth": 2425.15,
                        "pulse_length": 1024,
                        "mode": "active",
                        "power": 500,
                        "sample_interval": 256
                    },
                    "120000": {
                        "bandwidth": 8709.93,
                        "pulse_length": 256,
                        "mode": "active",
                        "power": 100,
                        "sample_interval": 64
                    },
                    "200000": {
                        "bandwidth": 10635,
                        "pulse_length": 256,
                        "mode": "active",
                        "power": 120,
                        "sample_interval": 64
                    }
                },
                "duration": "00:01:30",
                "stop_repeating_at": "23:55",
                "type": "constant"
            }
        ],
        "file_path": "QCT_1",
        "file_prefix": "OOI"
    },
    "er60_channels": {
        "GPT 200 kHz 00907207b7b1 6-2 OOI38|200": {
            "pulse_length": 0.000256,
            "frequency": 200000,
            "sample_interval": 0.000064,
            "power": 25,
            "mode": "passive"
        },
        "GPT 120 kHz 00907207b7dc 1-1 ES120-7CD": {
            "pulse_length": 0.000256,
            "frequency": 120000,
            "sample_interval": 0.000064,
            "power": 25,
            "mode": "passive"
        },
        "GPT  38 kHz 00907207b7b1 6-1 OOI.38|200": {
            "pulse_length": 0.001024,
            "frequency": 38000,
            "sample_interval": 0.000256,
            "power": 100,
            "mode": "passive"
        }
    },
    "gpts_enabled": false,
    "er60_status": {
        "executable": "c:/users/ooi/desktop/er60.lnk",
        "current_utc_time": "2014-05-28 20:55:09.971000",
        "current_running_interval": null,
        "pid": 3560,
        "host": "157.237.15.100",
        "scheduled_intervals_remaining": 96,
        "next_scheduled_interval": "2014-05-28 00:00:00.000000",
        "raw_output": {
            "max_file_size": 52428800,
            "sample_range": 30,
            "file_prefix": "OOI",
            "save_raw": true,
            "current_raw_filesize": null,
            "save_index": true,
            "save_bottom": true,
            "current_raw_filename": "OOI-D20140527-T110604.raw",
            "file_path": "D:\\data\\QCT_3"
        },
        "fs_root": "D:/",
        "port": 52890
    },
    "connected": true
    }

    """
    _data_particle_type = DataParticleType.ZPLSC_STATUS

    @staticmethod
    def regex():
        """
        Regular expression to match a sample pattern
        @return: regex string
        """
        pattern = r'#? *' # patter may or may not start with a '
        pattern += r'([0-9A-F]{6})' # temperature
        pattern += NEWLINE
        return pattern

    @staticmethod
    def regex_compiled():
        """
        get the compiled regex pattern
        @return: compiled re
        """
        return re.compile(ZPLSCStatusParticle.regex())

    def _build_parsed_values(self):
        """
        Parse ZPLSC Status response and return the ZPLSC Status particles
        @throws SampleException If there is a problem with sample

        example of ZPLSC Status:
        {
        "schedule_filename": "qct_configuration_example_1.yaml",
        "schedule": {
            "max_file_size": 52428800,
            "intervals": [
                {
                    "max_range": 220,
                    "start_at": "00:00",
                    "name": "constant_active",
                    "interval": 1000,
                    "frequency": {
                        "38000": {
                            "bandwidth": 2425.15,
                            "pulse_length": 1024,
                            "mode": "active",
                            "power": 500,
                            "sample_interval": 256
                        },
                        "120000": {
                            "bandwidth": 8709.93,
                            "pulse_length": 256,
                            "mode": "active",
                            "power": 100,
                            "sample_interval": 64
                        },
                        "200000": {
                            "bandwidth": 10635,
                            "pulse_length": 256,
                            "mode": "active",
                            "power": 120,
                            "sample_interval": 64
                        }
                    },
                    "duration": "00:01:30",
                    "stop_repeating_at": "23:55",
                    "type": "constant"
                }
            ],
            "file_path": "QCT_1",
            "file_prefix": "OOI"
        },
        "er60_channels": {
            "GPT 200 kHz 00907207b7b1 6-2 OOI38|200": {
                "pulse_length": 0.000256,
                "frequency": 200000,
                "sample_interval": 0.000064,
                "power": 25,
                "mode": "passive"
            },
            "GPT 120 kHz 00907207b7dc 1-1 ES120-7CD": {
                "pulse_length": 0.000256,
                "frequency": 120000,
                "sample_interval": 0.000064,
                "power": 25,
                "mode": "passive"
            },
            "GPT  38 kHz 00907207b7b1 6-1 OOI.38|200": {
                "pulse_length": 0.001024,
                "frequency": 38000,
                "sample_interval": 0.000256,
                "power": 100,
                "mode": "passive"
            }
        },
        "gpts_enabled": false,
        "er60_status": {
            "executable": "c:/users/ooi/desktop/er60.lnk",
            "current_utc_time": "2014-05-28 21:31:44.929000",
            "current_running_interval": null,
            "pid": 3560,
            "host": "157.237.15.100",
            "scheduled_intervals_remaining": 96,
            "next_scheduled_interval": "2014-05-28 00:00:00.000000",
            "raw_output": {
                "max_file_size": 52428800,
                "sample_range": 30,
                "file_prefix": "OOI",
                "save_raw": true,
                "current_raw_filesize": null,
                "save_index": true,
                "save_bottom": true,
                "current_raw_filename": "OOI-D20140527-T110604.raw",
                "file_path": "D:\\data\\QCT_3"
            },
            "fs_root": "D:/",
            "port": 52890
        },
        "connected": true
        }
        """
        try:
            config = json.loads(self.raw_data)
            if not isinstance(config, dict):
                raise SampleException("ZPLSC status data is not a dictionary" % self.raw_data)

            connected = config[CONNECTED]
            for key in config[ER60_CHANNELS]:
                if '200 kHz' in key:
                    active_200k_mode = config[ER60_CHANNELS][key][MODE]
                    active_200k_power = config[ER60_CHANNELS][key][POWER]
                    active_200k_pulse_length = config[ER60_CHANNELS][key][PULSE_LENGTH]
                    active_200k_sample_interval = config[ER60_CHANNELS][key][SAMPLE_INTERVAL]
                elif '120 kHz' in key:
                    active_120k_mode = config[ER60_CHANNELS][key][MODE]
                    active_120k_power = config[ER60_CHANNELS][key][POWER]
                    active_120k_pulse_length = config[ER60_CHANNELS][key][PULSE_LENGTH]
                    active_120k_sample_interval = config[ER60_CHANNELS][key][SAMPLE_INTERVAL]
                elif '38 kHz' in key:
                    active_38k_mode = config[ER60_CHANNELS][key][MODE]
                    active_38k_power = config[ER60_CHANNELS][key][POWER]
                    active_38k_pulse_length = config[ER60_CHANNELS][key][PULSE_LENGTH]
                    active_38k_sample_interval = config[ER60_CHANNELS][key][SAMPLE_INTERVAL]


            er60_status = config[ER60_STATUS]
            current_utc_time = er60_status[CURRENT_UTC_TIME]
            executable = er60_status[EXECUTABLE]
            fs_root = er60_status[FS_ROOT]
            next_scheduled_interval = er60_status[NEXT_SCHEDULED_INTERVAL]
            host = er60_status[HOST]
            pid = er60_status[PID]
            #port = er60_status[PORT]

            raw_output = config[ER60_STATUS][RAW_OUTPUT]
            current_raw_filename = raw_output[CURRENT_RAW_FILENAME]
            current_raw_filesize = raw_output[CURRENT_RAW_FILESIZE]
            file_path = raw_output[FILE_PATH]
            file_prefix = raw_output[FILE_PREFIX]
            max_file_size = raw_output[MAX_FILE_SIZE]
            sample_range = raw_output[SAMPLE_RANGE]
            save_bottom = raw_output[SAVE_BOTTOM]
            save_index = raw_output[SAVE_INDEX]
            save_raw = raw_output[SAVE_RAW]
            scheduled_interval_remaining = er60_status[SCHEDULED_INTERVAL_REMAINING]
            gpts_enabled = config[GPTS_ENABLED]
            schedule_filename = config[SCHEDULE_FILENAME]

            # intervals = []
            # for each in config['schedule']['intervals']:
            #     d = {}
            #     d[ZPLSCStatusParticleKey.FREQ_38K_MODE] = each['frequency']['38000']['mode']
            #     intervals.append(d)
            #
            # for index, each in enumerate(intervals):
            #     for key, value in each.iteritems:
            #         value_id = '%s_%d' % (key, index)
            #         result.append({DataParticleKey.VALUE_ID: value_id, DataParticleKey.VALUE: value})


        except KeyError:
             raise SampleException("ValueError while converting ZPLSC Status: [%s]" %
                                  self.raw_data)

        result = [{DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_MODE,
                   DataParticleKey.VALUE: active_200k_mode},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_POWER,
                   DataParticleKey.VALUE: active_200k_power},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_PULSE_LENGTH,
                    DataParticleKey.VALUE: active_200k_pulse_length},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_SAMPLE_INTERVAL,
                   DataParticleKey.VALUE: active_200k_sample_interval},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_MODE,
                   DataParticleKey.VALUE: active_120k_mode},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_POWER,
                   DataParticleKey.VALUE: active_120k_power},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_PULSE_LENGTH,
                    DataParticleKey.VALUE: active_120k_pulse_length},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_SAMPLE_INTERVAL,
                   DataParticleKey.VALUE: active_120k_sample_interval},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_POWER,
                   DataParticleKey.VALUE: active_120k_power},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_PULSE_LENGTH,
                    DataParticleKey.VALUE: active_38k_pulse_length},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_SAMPLE_INTERVAL,
                   DataParticleKey.VALUE: active_38k_sample_interval},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_CURRENT_UTC_TIME,
                   DataParticleKey.VALUE: current_utc_time},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_EXECUTABLE,
                   DataParticleKey.VALUE: executable},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_FS_ROOT,
                   DataParticleKey.VALUE: fs_root},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_NEXT_SCHEDULED_INTERVAL,
                   DataParticleKey.VALUE: next_scheduled_interval},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_HOST,
                   DataParticleKey.VALUE: host},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_PID,
                   DataParticleKey.VALUE: pid},
                  #{DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_PORT,
                  #DataParticleKey.VALUE: port},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_CURRENT_RAW_FILENAME,
                   DataParticleKey.VALUE: current_raw_filename},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_CURRENT_RAW_FILESIZE,
                   DataParticleKey.VALUE: current_raw_filesize},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_FILE_PATH,
                   DataParticleKey.VALUE: file_path},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_FILE_PREFIX,
                   DataParticleKey.VALUE: file_prefix},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_MAX_FILE_SIZE,
                   DataParticleKey.VALUE: max_file_size},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SAMPLE_RANGE,
                   DataParticleKey.VALUE: sample_range},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SAVE_BOTTOM,
                   DataParticleKey.VALUE: save_bottom},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SAVE_INDEX,
                   DataParticleKey.VALUE: save_index},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SAVE_RAW,
                   DataParticleKey.VALUE: save_raw},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SCHEDULED_INTERVAL_REMAINING,
                   DataParticleKey.VALUE: scheduled_interval_remaining},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_GPTS_ENABLED,
                   DataParticleKey.VALUE: gpts_enabled},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SCHEDULE_FILENAME,
                   DataParticleKey.VALUE: schedule_filename}]

        return result


###############################################################################
# Driver
###############################################################################

class InstrumentDriver(SingleConnectionInstrumentDriver):
    """
    InstrumentDriver subclass
    Subclasses SingleConnectionInstrumentDriver with connection state
    machine.
    """
    def __init__(self, evt_callback):
        """
        Driver constructor.
        @param evt_callback Driver process event callback.
        """
        #Construct superclass.
        SingleConnectionInstrumentDriver.__init__(self, evt_callback)

    ########################################################################
    # Protocol builder.
    ########################################################################

    def _build_protocol(self):
        """
        Construct the driver protocol state machine.
        """
        self._protocol = Protocol(Prompt, NEWLINE, self._driver_event)


###########################################################################
# Protocol
###########################################################################

class Protocol(CommandResponseInstrumentProtocol):
    """
    Instrument protocol class
    Subclasses CommandResponseInstrumentProtocol
    """
    def __init__(self, prompts, newline, driver_event):
        """
        Protocol constructor.
        @param prompts A BaseEnum class containing instrument prompts.
        @param newline The newline.
        @param driver_event Driver process event callback.
        """
        # Construct protocol superclass.
        CommandResponseInstrumentProtocol.__init__(self, prompts, newline, driver_event)

        # Build protocol state machine.
        self._protocol_fsm = ThreadSafeFSM(ProtocolState, ProtocolEvent,
                            ProtocolEvent.ENTER, ProtocolEvent.EXIT)

        # Add event handlers for protocol state machine.
        self._protocol_fsm.add_handler(ProtocolState.UNKNOWN, ProtocolEvent.ENTER, self._handler_unknown_enter)
        self._protocol_fsm.add_handler(ProtocolState.UNKNOWN, ProtocolEvent.EXIT, self._handler_unknown_exit)
        self._protocol_fsm.add_handler(ProtocolState.UNKNOWN, ProtocolEvent.DISCOVER, self._handler_discover)
        self._protocol_fsm.add_handler(ProtocolState.UNKNOWN, ProtocolEvent.START_DIRECT, self._handler_command_start_direct)

        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.ENTER, self._handler_command_enter)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.EXIT, self._handler_command_exit)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.START_DIRECT, self._handler_command_start_direct)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.START_AUTOSAMPLE, self._handler_command_autosample)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.ACQUIRE_STATUS, self._handler_command_acquire_status)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.GET, self._handler_command_get)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.SET, self._handler_command_set)

        self._protocol_fsm.add_handler(ProtocolState.AUTOSAMPLE, ProtocolEvent.STOP_AUTOSAMPLE, self._handler_autosample_stop)
        self._protocol_fsm.add_handler(ProtocolState.AUTOSAMPLE, ProtocolEvent.DISCOVER, self._handler_discover)

        self._protocol_fsm.add_handler(ProtocolState.DIRECT_ACCESS, ProtocolEvent.ENTER, self._handler_direct_access_enter)
        self._protocol_fsm.add_handler(ProtocolState.DIRECT_ACCESS, ProtocolEvent.EXIT, self._handler_direct_access_exit)
        self._protocol_fsm.add_handler(ProtocolState.DIRECT_ACCESS, ProtocolEvent.STOP_DIRECT, self._handler_direct_access_stop_direct)
        self._protocol_fsm.add_handler(ProtocolState.DIRECT_ACCESS, ProtocolEvent.EXECUTE_DIRECT, self._handler_direct_access_execute_direct)

        # Construct the parameter dictionary containing device parameters,
        # current parameter values, and set formatting functions.
        self._build_driver_dict()
        self._build_command_dict()
        self._build_param_dict()

        # Add build handlers for device commands.
        self._add_build_handler(Command.GET, self._build_get_command)
        self._add_build_handler(Command.SET, self._build_set_command)
        self._add_build_handler(Command.STATUS, self._build_status_command)


        # Add response handlers for device commands.
        self._add_response_handler(Command.GET, self._parse_get_response)
        self._add_response_handler(Command.SET, self._parse_set_response)
        self._add_response_handler(Command.STATUS, self._parse_status_response)
        self._add_response_handler(Command.GET_SCHEDULE, self._parse_get_schedule)
        self._add_response_handler(Command.LIST_SCHEDULE, self._parse_list_schedule)

        # Add sample handlers.

        # State state machine in UNKNOWN state.
        self._protocol_fsm.start(ProtocolState.UNKNOWN)

        # commands sent sent to device to be filtered in responses for telnet DA
        self._sent_cmds = []

        #
        self._chunker = StringChunker(Protocol.sieve_function)

        schedule_file = self._create_schedule_file()
        self._ftp_config_file(schedule_file)
        schedule_file.close()


    @staticmethod
    def sieve_function(raw_data):
        """
        The method that splits samples
        """

        return_list = []

        return return_list

    def _build_param_dict(self):
        """
        Populate the parameter dictionary with parameters.
        For each parameter key, add match string, match lambda function,
        and value formatting function for set commands.
        """
        self._param_dict.add(Parameter.NAME,
                             r'name:\s+(\w+)',
                             lambda match : match.group(1),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Name",
                             startup_param = True,
                             direct_access = False,
                             default_value = "constant",
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.TYPE,
                             r'type:\s+\"(\w+)\" ',
                             lambda match : match.group(1),
                             self.__str__(),
                             type=ParameterDictType.STRING,
                             display_name="Type",
                             startup_param = True,
                             direct_access = False,
                             default_value = "constant",
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.START_AT,
                             r'start_at:\s+\"(\w+)\" ',
                             lambda match : match.group(1),
                             self.__str__(),
                             type=ParameterDictType.STRING,
                             display_name="Start At",
                             startup_param = True,
                             direct_access = False,
                             default_value = "00:00",
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.DURATION,
                             r'duration:\s+(\d\d:\d\d:\d\d)',
                             lambda match : match.group(1),
                             self.__str__(),
                             type=ParameterDictType.STRING,
                             display_name="Duration",
                             startup_param = True,
                             direct_access = False,
                             default_value = "00:15:00",
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.REPEAT_EVERY,
                             r'repeat_every:\s+(\d\d:\d\d-\d\d:\d\d)',
                             lambda match :match.group(1),
                             self.__str__(),
                             type=ParameterDictType.FLOAT,
                             display_name="Repeat Every",
                             startup_param = True,
                             direct_access = False,
                             default_value = "01:00",
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.STOP_REPEATING_AT,
                             r'stop_repeating_at:\s+(\d\d:\d\d-\d\d:\d\d)',
                             lambda match : match.group(1),
                             self.__str__(),
                             type=ParameterDictType.STRING,
                             display_name="Stop Repeat At",
                             startup_param = True,
                             direct_access = False,
                             default_value = "23:55",
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.INTERVAL,
                             r'interval:\s+(\w+)',
                             lambda match : match.group(1),
                             self._int_to_string(),
                             type=ParameterDictType.INT,
                             display_name="Interval",
                             startup_param = True,
                             direct_access = False,
                             default_value = 1000,
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.MAX_RANGE,
                             r'max_range:\s+(\d+)',
                             lambda match : match.group(1),
                             self._int_to_string(),
                             type=ParameterDictType.INT,
                             display_name="Max Range",
                             startup_param = True,
                             direct_access = False,
                             default_value = 80,
                             visibility=ParameterDictVisibility.IMMUTABLE)

        self._param_dict.add(Parameter.MINIMUM_INTERVAL,
                             r'minimum_interval:\s+(\d+)',
                             lambda match : match.group(1),
                             self._float_to_string,
                             type=ParameterDictType.INT,
                             display_name="Minimum Interval",
                             startup_param = True,
                             direct_access = False,
                             default_value = 0,
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.NUMBER,
                             r'number:\s+(\d+)',
                             lambda match : match.group(1),
                             self._int_to_string(),
                             type=ParameterDictType.INT,
                             display_name="Number",
                             startup_param = True,
                             direct_access = False,
                             default_value = 0,
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FREQ_38K_MODE,
                             r'number:\s+(\w+)',
                             lambda match : match.group(1),
                             self._int_to_string(),
                             type=ParameterDictType.STRING,
                             display_name="Freq 38K Mode",
                             startup_param = True,
                             direct_access = False,
                             default_value = "active",
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FREQ_38K_POWER,
                             r'number:\s+(\d+)',
                             lambda match : True if match.group(1) == 'yes' else False,
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Freq 38K Power",
                             startup_param = True,
                             direct_access = False,
                             default_value = 100,
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FREQ_38K_PULSE_LENGTH,
                             r'pulse_length:\s+(\d+)',
                             lambda match : match.group(1),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Freq 38K Pulse Length",
                             startup_param = True,
                             direct_access = False,
                             default_value = 256,
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FREQ_120K_MODE,
                             r'mode:\s+(\w+)',
                             lambda match : match.group(1),
                             self._int_to_string(),
                             type=ParameterDictType.STRING,
                             display_name="Freq 120K Mode",
                             startup_param = True,
                             direct_access = False,
                             default_value = "active",
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FREQ_120K_POWER,
                             r'power:\s+(\d+)',
                             lambda match : match.group(1),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Freq 120K Power",
                             startup_param = True,
                             direct_access = True,
                             default_value = 100,
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FREQ_120K_PULSE_LENGTH,
                             r'pulse_length:\s+(\d+)',
                             lambda match : match.group(1),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Freq 120K Pulse Length",
                             startup_param = True,
                             direct_access = False,
                             default_value = 64,
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FREQ_200K_MODE,
                             r'mode:\s+(\w+)',
                             lambda match : match.group(1),
                             self._int_to_string(),
                             type=ParameterDictType.STRING,
                             display_name="Freq 200K Mode",
                             startup_param = True,
                             direct_access = False,
                             default_value = "active",
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FREQ_200K_POWER,
                             r'power:\s+(\d+)',
                             lambda match : match.group(1),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Freq 200K Power",
                             startup_param = True,
                             direct_access = True,
                             default_value = 100,
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FREQ_200K_PULSE_LENGTH,
                             r'pulse_length:\s+(\d+)',
                             lambda match : match.group(1),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Freq 200K Pulse Length",
                             startup_param = True,
                             direct_access = True,
                             default_value = 256,
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FTP_IP_ADDRESS,
                             r'ftp address:\s+(\d\d\d\d.\d\d\d\d.\d\d\d\d.\d\d\d)',
                             lambda match : match.group(1),
                             self.__str__(),
                             type=ParameterDictType.STRING,
                             display_name="FTP Ip Address",
                             startup_param = True,
                             direct_access = True,
                             default_value = "10.33.10.143",
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FTP_PORT_NUMBER,
                             r'ftp port:\s+(\d+)',
                             lambda match : match.group(1),
                             self._int_to_string(),
                             type=ParameterDictType.INT,
                             display_name="FTP Port Number",
                             startup_param = True,
                             direct_access = True,
                             default_value = 21,
                             visibility=ParameterDictVisibility.READ_WRITE)

    def _create_schedule_file(self):
        """
        Construct a yaml configuration file with the following file format:
        # QCT Example 3 configuration file
        ---
        file_prefix:    "OOI"
        file_path:      "QCT_3"         #relative to filesystem_root/data
        max_file_size:   52428800       #50MB in bytes:  50 * 1024 * 1024

        intervals:
        name: "constant_passive"
        type: "constant"
        start_at:  "00:00"
        duration:  "00:01:30"
        repeat_every:   "00:05"
        stop_repeating_at: "23:55"
        interval:   1000
        max_range:  30
        frequency:
          38000:
              mode:   passive
              power:  100
              pulse_length:   1024
          120000:
              mode:   passive
              power:  25
              pulse_length:   256
          200000:
              mode:   passive
              power:  25
              pulse_length:   256


        """
        config = {
            'file_prefix':    "OOI",
            'file_path':      "QCT_3",
            'max_file_size':   52428800,

            'intervals': {
                'name': self._param_dict.get_config_value(Parameter.NAME),
                'type': self._param_dict.get_config_value(Parameter.TYPE),
                'start_at': self._param_dict.get_config_value(Parameter.START_AT),
                'duration': self._param_dict.get_config_value(Parameter.DURATION),
                'repeat_every': self._param_dict.get_config_value(Parameter.REPEAT_EVERY),
                'stop_repeating_at': self._param_dict.get_config_value(Parameter.STOP_REPEATING_AT),
                'interval': self._param_dict.get_config_value(Parameter.INTERVAL),
                'max_range': self._param_dict.get_config_value(Parameter.REPEAT_EVERY),
                'frequency': {
                    38000: {
                        'mode': self._param_dict.get_config_value(Parameter.FREQUENCY_38K_MODE),
                        'power': self._param_dict.get_config_value(Parameter.FREQUENCY_38K_POWER),
                        'pulse_length': self._param_dict.get_config_value(Parameter.FREQUENCY_38K_PULSE_LENGTH),
                        },
                    120000: {
                        'mode': self._param_dict.get_config_value(Parameter.FREQUENCY_120K_MODE),
                        'power': self._param_dict.get_config_value(Parameter.FREQUENCY_120K_POWER),
                        'pulse_length':   self._param_dict.get_config_value(Parameter.FREQUENCY_120K_PULSE_LENGTH),
                        },
                    200000: {
                        'mode': self._param_dict.get_config_value(Parameter.FREQUENCY_200K_MODE),
                        'power': self._param_dict.get_config_value(Parameter.FREQUENCY_200K_POWER),
                        'pulse_length': self._param_dict.get_config_value(Parameter.FREQUENCY_200K_PULSE_LENGTH),
                        },
                    }
            }
        }

        config_file = tempfile.TemporaryFile()
        config_file.write(yaml.dump(config, default_flow_style=False))


        return config_file


    def _ftp_config_file(self, config_file, file_name):
        """
        FTP the configuration file to the ZPLSC server
        """

        host = self._param_dict.get_config_value(Parameter.FTP_IP_ADDRESS)
        port = self._param_dict.get_config_value(Parameter.FTP_PORT_NUMBER)
        #user_name = 'ooi'
        #password = '994ef22'

        if ((config_file == None) or (not isinstance(config_file, tempfile))):
            raise InstrumentException("config_file is not a tempfile!")

        try:
            ftp_session = ftplib.FTP(host, USER_NAME, PASSWORD)

        except (ftplib.socket.error, ftplib.socket.gaierror), e:
            log.error("ERROR: cannot reach FTP Host %s " % (host))
            return
        log.debug("*** Connected to ftp host %s" % (host))

        # FTP the instrument's config file to the instrument sever
        ftp_session.storbinary('STOR %s ' % file_name, config_file)
        log.debug("*** Config ymal file sent")

        ftp_session.quit()


    # def _extract_xml_elements(self, node, tag, raise_exception_if_none_found=True):
    #     """
    #     extract elements with tag from an XML node
    #     @param: node - XML node to look in
    #     @param: tag - tag of elements to look for
    #     @param: raise_exception_if_none_found - raise an exception if no element is found
    #     @return: return list of elements found; empty list if none found
    #     """
    #     elements = node.getElementsByTagName(tag)
    #     if raise_exception_if_none_found and len(elements) == 0:
    #         raise SampleException("_extract_xml_elements: No %s in input data: [%s]" % (tag, self.raw_data))
    #     return elements

    # def _extract_xml_element_value(self, node, tag, raise_exception_if_none_found=True):
    #     """
    #     extract element value that has tag from an XML node
    #     @param: node - XML node to look in
    #     @param: tag - tag of elements to look for
    #     @param: raise_exception_if_none_found - raise an exception if no value is found
    #     @return: return value of element
    #     """
    #     elements = self._extract_xml_elements(node, tag, raise_exception_if_none_found)
    #     children = elements[0].childNodes
    #     if raise_exception_if_none_found and len(children) == 0:
    #         raise SampleException("_extract_xml_element_value: No value for %s in input data: [%s]" % (tag, self.raw_data))
    #     return children[0].nodeValue

    # def _get_xml_parameter(self, xml_element, parameter_name, type=float):
    #     return {DataParticleKey.VALUE_ID: parameter_name,
    #             DataParticleKey.VALUE: type(self._extract_xml_element_value(xml_element,
    #                                                                         self._map_param_to_xml_tag(parameter_name)))}

    def _build_simple_command(self, cmd):
        """
        Build handler for basic ZPLSC commands.
        @param cmd the simple sbe16 command to format.
        @retval The command to be sent to the device.
        """
        return "%s%s" % (cmd, NEWLINE)


    def _build_get_command(self, cmd, param):
        """
        Build handler for get command. Build header, msg control and
        message request which contains XML based Get request.
        @param param the parameter key to set.
        @ retval The get command to be sent to the device.
        @throws InstrumentProtocolException if the parameter is not valid or
        if the formatting function could not accept the value passed.
        """
        try:

           if param == 'INTERVAL':
               param = 'sampleinterval'
           #
           # param = "RemoteCommandDispatcher/ClientTimeoutLimit "
           # header = "REQ\0"
           # msg_control = "2,1,1\0"
           # # XML based Set Param Request
           # msg_request = "<request>" + NEWLINE + \
           #                "  <clientInfo>" + NEWLINE + \
           #                "    <cid>1</cid> " + NEWLINE + \
           #                "    <rid>28</rid> " + NEWLINE + \
           #                "  </clientInfo> " + NEWLINE + \
           #                "  <type>invokeMethod</type> " + NEWLINE + \
           #                "  <targetComponent> ParameterServer </targetComponent> " + + NEWLINE + \
           #                "  <method> " + NEWLINE + \
           #                "    <GetParameter> " + NEWLINE + \
           #                "      <paramName> " + NEWLINE + \
           #                "        %s " + NEWLINE + \
           #                "      </paramName> " + NEWLINE + \
           #                "      <time>0</time> " + NEWLINE + \
           #                "    </GetParameter> " + NEWLINE + \
           #                " </method> " + NEWLINE + \
           #                " </request> " % (param)
           #
           get_cmd = 'get' + NEWLINE
        except KeyError:
           raise InstrumentParameterException('Unknown driver parameter %s' % param)

        return get_cmd

    def _build_set_command(self, cmd, param, val):
        """
        Build handler for set commands. Build header, msg control and
        message request which contains XML based Set request.
        @param param the parameter key to set.
        @param val the parameter value to set.
        @ retval The set command to be sent to the device.
        @throws InstrumentProtocolException if the parameter is not valid or
        if the formatting function could not accept the value passed.
        """
        try:

            str_val = self._param_dict.format(param, val)

            set_cmd = '%s=%s' % (param, str_val)
            set_cmd = set_cmd + NEWLINE

        except KeyError:
           raise InstrumentParameterException('Unknown driver parameter %s' % param)

        return set_cmd

    def _parse_get_response(self, response, prompt):

        for line in response.split(NEWLINE):
            self._param_dict.update(line)

        return response

    def _parse_set_response(self, response, prompt):
        """
        Parse handler for set response.
        @param response set command response string.
        @param prompt prompt following command response.
        @throws InstrumentProtocolException if response is invalid.
        """
        #if prompt not in [Prompt.COMMAND, Prompt.EXECUTED]:
        #    raise InstrumentProtocolException('dcal command not recognized: %s.' % response)

        for line in response.split(NEWLINE):
            self._param_dict.update(line)

        return response


    def _parse_status_response(self, response, prompt):
        """
        Parse handler for status response.
        @param response status command response string.
        @param prompt prompt following command response.
        @throws InstrumentProtocolException if response is invalid.
        { 'connected': True,
          'er60_channels': {'GPT  38 kHz 00907207b7b1 6-1 OOI.38|200': {'frequency': 38000,
                                                               'mode': 'passive',
                                                               'power': 100.0,
                                                               'pulse_length': 0.001024,
                                                               'sample_interval': 0.000256},
                   'GPT 120 kHz 00907207b7dc 1-1 ES120-7CD': {'frequency': 120000,
                                                              'mode': 'passive',
                                                              'power': 25.0,
                                                              'pulse_length': 0.000256,
                                                              'sample_interval': 6.4e-05},
                   'GPT 200 kHz 00907207b7b1 6-2 OOI38|200': {'frequency': 200000,
                                                              'mode': 'passive',
                                                              'power': 25.0,
                                                              'pulse_length': 0.000256,
                                                              'sample_interval': 6.4e-05}},
          'er60_status': {'current_running_interval': 'constant_passive',
                   'current_utc_time': '2014-05-22 20:31:02.249000',
                   'executable': 'c:/users/ooi/desktop/er60.lnk',
                   'fs_root': 'D:/',
                   'host': '157.237.15.100',
                   'next_scheduled_interval': '2014-05-22 20:35:00.000000',
                   'pid': 2948,
                   'port': 56765,
                   'raw_output': {'current_raw_filename': 'OOI-D20140522-T173500.raw',
                                'current_raw_filesize': None,
                                'file_path': 'D:\\data\\QCT_3',
                                'file_prefix': 'OOI',
                                'max_file_size': 52428800,
                                'sample_range': 30.0,
                                'save_bottom': True,
                                'save_index': True,
                                'save_raw': True},
                   'scheduled_intervals_remaining': 40},

          'gpts_enabled': True,
          'schedule': {'file_path': 'QCT_3',
              'file_prefix': 'OOI',
              'intervals': [{'duration': '00:01:30',
                             'frequency': {'120000': {'bandwidth': 8709.93,
                                                      'mode': 'passive',
                                                      'power': 25,
                                                      'pulse_length': 256,
                                                      'sample_interval': 64},
                                           '200000': {'bandwidth': 10635,
                                                      'mode': 'passive',
                                                      'power': 25,
                                                      'pulse_length': 256,
                                                      'sample_interval': 64},
                                           '38000': {'bandwidth': 2425.15,
                                                     'mode': 'passive',
                                                     'power': 100,
                                                     'pulse_length': 1024,
                                                     'sample_interval': 256}},
                             'interval': 1000,
                             'max_range': 30,
                             'name': 'constant_passive',
                             'start_at': '00:00',
                             'stop_repeating_at': '23:55',
                             'type': 'constant'}],
              'max_file_size': 52428800},
          'schedule_filename': 'qct_configuration_example_3.yaml'}
        """
        # try:
        #     config = json.loads(response)
        #     file_path = config['schedule']['file_path'][0]['name']
        #     name = config['schedule']['intervals'][0]['name']
        #     type = config['schedule']['intervals'][0]['type']
        #     interval = config['schedule']['intervals'][0]['interval']
        #     start_at = config['schedule']['intervals'][0]['start_at']
        #     duration = config['schedule']['intervals'][0]['duration']
        #     max_range = config['schedule']['intervals'][0]['max_range']
        #     stop_repeating_at = config['schedule']['intervals'][0]['stop_repeating_at']
        #
        #     feq_38k_mode = config['schedule']['intervals'][0]['frequency']['38000']['mode']
        #     feq_38k_power = config['schedule']['intervals'][0]['frequency']['38000']['power']
        #     feq_38k_pulse_length = config['schedule']['intervals'][0]['frequency']['38000']['pulse_length']
        #     feq_38k_sample_interval = config['schedule']['intervals'][0]['frequency']['38000']['sample_interval']
        #     feq_120k_mode = config['schedule']['intervals'][0]['frequency']['120000']['mode']
        #     feq_120k_power = config['schedule']['intervals'][0]['frequency']['120000']['power']
        #     feq_120k_pulse_length = config['schedule']['intervals'][0]['frequency']['120000']['pulse_length']
        #     feq_120k_sample_interval = config['schedule']['intervals'][0]['frequency']['120000']['sample_interval']
        #     feq_200k_mode = config['schedule']['intervals'][0]['frequency']['120000']['mode']
        #     feq_200k_power = config['schedule']['intervals'][0]['frequency']['120000']['power']
        #     feq_120k_pulse_length = config['schedule']['intervals'][0]['frequency']['120000']['pulse_length']
        #     feq_120k_sample_interval = config['schedule']['intervals'][0]['frequency']['120000']['sample_interval']
        # except KeyError:
        #      raise InstrumentParameterException('Unknown Key in Instrument Configuration')

        return response


    def _got_chunk(self, chunk):
        """
        The base class got_data has gotten a chunk from the chunker.  Pass it to extract_sample
        with the appropriate particle objects and REGEXes.
        """


    def _build_driver_dict(self):
        """
        Populate the driver dictionary with options
        """
        self._driver_dict.add(DriverDictKey.VENDOR_SW_COMPATIBLE, True)

    def _build_command_dict(self):
        """
        Populate the command dictionary with command.
        """
        self._cmd_dict.add(Capability.START_AUTOSAMPLE, display_name="start autosample")
        self._cmd_dict.add(Capability.STOP_AUTOSAMPLE, display_name="stop autosample")
        self._cmd_dict.add(Capability.GET_CONFIGURATION, display_name="get calibrations")


    def _filter_capabilities(self, events):
        """
        Return a list of currently available capabilities.
        """
        return [x for x in events if Capability.has(x)]

    ########################################################################
    # Unknown handlers.
    ########################################################################

    def _handler_unknown_enter(self, *args, **kwargs):
        """
        Enter unknown state.
        """
        # Tell driver superclass to send a state change event.
        # Superclass will query the state.
        self._driver_event(DriverAsyncEvent.STATE_CHANGE)

    def _handler_unknown_exit(self, *args, **kwargs):
        """
        Exit unknown state.
        """
        pass

    def _handler_discover(self, *args, **kwargs):
        """
        Discover current state
        @retval (next_state, result)
        """
        next_state = None
        next_agent_state = None

        next_state = ProtocolState.COMMAND
        next_agent_state = ResourceAgentState.IDLE

        return (next_state, next_agent_state)


    ########################################################################
    # Command handlers.
    ########################################################################

    def _handler_command_enter(self, *args, **kwargs):
        """
        Enter command state.
        @throws InstrumentTimeoutException if the device cannot be woken.
        @throws InstrumentProtocolException if the update commands and not recognized.
        """

        # Tell driver superclass to send a state change event.
        # Superclass will query the state.
        self._driver_event(DriverAsyncEvent.STATE_CHANGE)

    def _handler_command_get(self, *args, **kwargs):
        """
        Get parameters while in the command state.
        @param params List of the parameters to pass to the state
        @retval returns (next_state, result) where result is a dict {}. No
            agent state changes happening with Get, so no next_agent_state
        @throw InstrumentParameterException for invalid parameter
        """
        next_state = None
        result = None
        result_vals = {}

        # Retrieve required parameter.
        # Raise if no parameter provided, or not a dict.
        try:
            params = args[0]

        except IndexError:
            raise InstrumentParameterException('_handler_command_get requires a parameter dict.')

        if ((params == None) or (not isinstance(params, list))):
            raise InstrumentParameterException("GET parameter list not a list!")

        if Parameter.ALL in params:
            params = Parameter.list()
            params.remove(Parameter.ALL)

        #self._update_params()

        # fill the return values from the update
        for param in params:
            if not Parameter.has(param):
                raise InstrumentParameterException("Invalid parameter!")
            result_vals[param] = self._param_dict.get(param)
        result = result_vals

        log.debug("Get finished, next: %s, result: %s", next_state, result)
        return (next_state, result)


    def _handler_command_set(self, *args, **kwargs):
        """
        Set parameter
        """
        next_state = None
        result = None
        next_state = None
        startup = False

        try:
            params = args[0]
        except IndexError:
            raise InstrumentParameterException('_handler_command_set Set command requires a parameter dict.')

        try:
            startup = args[1]
        except IndexError:
            pass

        if not isinstance(params, dict):
            raise InstrumentParameterException('Set parameters not a dict.')

        # For each key, val in the dict, issue set command to device.
        # Raise if the command not understood.
        else:
            self._set_params(params, startup)

        return (next_state, result)

    def _set_params(self, *args, **kwargs):
        """
        Issue commands to the instrument to set various parameters
        """
        try:
            params = args[0]
        except IndexError:
            raise InstrumentParameterException('Set command requires a parameter dict.')

        # verify param is not readonly param
        self._verify_not_readonly(*args, **kwargs)

        for (key, val) in params.iteritems():
            log.debug("KEY = %s VALUE = %s", key, val)
            self._param_dict.set_value(key, val)

        log.debug("set complete, update params")
        #self._update_params()

    def _handler_command_exit(self, *args, **kwargs):
        """
        Exit command state.
        """
        pass


    def _handler_command_start_direct(self):
        """
        Start direct access
        """
        next_state = ProtocolState.DIRECT_ACCESS
        next_agent_state = ResourceAgentState.DIRECT_ACCESS
        result = None
        log.debug("_handler_command_start_direct: entering DA mode")
        return (next_state, (next_agent_state, result))


    def load_schedule(self, filename, host=DEFAULT_HOST):
        """
        Loads a schedule file previously uploaded to the instrument and sets it as
        the active instrument configuration
        """
        url = host + '/load_schedule'

        req = urllib2.Request(url, data=json.dumps({'filename': filename}),
            headers={'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        res = f.read()
        f.close()
        return json.loads(res)



    def start_schedule(self, host=DEFAULT_HOST):
        """
        Start the currently loaded schedule
        """

        url = host + '/start_schedule'
        req = urllib2.Request(url, data={},
            headers={'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        res = f.read()
        f.close()
        return json.loads(res)


    def _stop_schedule(self, host=DEFAULT_HOST):
        """
        Stop the current schedule
        """

        url = host + '/stop_schedule'
        req = urllib2.Request(url, data={},
            headers={'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        res = f.read()
        f.close()
        return json.loads(res)


    def _handler_command_autosample(self, *args, **kwargs):
        """ Start autosample mode """

        log.debug("_handler_command_autosample")
        next_state = None
        next_agent_state = None
        result = None

        host_ip_address = self._param_dict.get_config_value(Parameter.FTP_IP_ADDRESS)
        host = 'https://' + host_ip_address

        # Generate the schedule.ymal file
        schedule_file = self._create_schedule_file()

        # Upload the schedule ymal file to the server via ftp
        self._ftp_config_file(schedule_file, ZPLSC_CONFIG_FILE_NAME)
        schedule_file.close()

        # Load the schedule file
        self.load_schedule(ZPLSC_CONFIG_FILE_NAME, host)

        # Start the schedule
        self.start_schedule(host)

        #self._do_cmd_no_resp(Command.START_AUTOSAMPLE)

        next_state = ProtocolState.AUTOSAMPLE
        next_agent_state = ResourceAgentState.STREAMING

        return (next_state, (next_agent_state, result))

    def _handler_command_acquire_status(self, *args, **kwargs):
        """ Acquire status from the instrument"""

        log.debug("_handler_command_acquire_status")

        next_state = None
        next_agent_state = None
        result = None

        host_ip_address = self._param_dict.get_config_value(Parameter.FTP_IP_ADDRESS)
        host = 'https://' + host_ip_address

        url = host + '/status.json'
        req = urllib2.Request(url)
        f = urllib2.urlopen(req)
        res = f.read()
        f.close()
        response = json.loads(res)
        #result = self._parse_status_response(response)

        particle = ZPLSCStatusParticle(response, port_timestamp=self._param_dict.get_current_timestamp())
        self._driver_event(DriverAsyncEvent.SAMPLE, particle.generate())

        return (next_state, (next_agent_state, result))


    def _parse_status_response(self, response):
        """
        Parse ZPLSC Status response and return the ZPLSC Status particles
        @throws SampleException If there is a problem with sample

        example of ZPLSC Status:
        {
        "schedule_filename": "qct_configuration_example_1.yaml",
        "schedule": {
            "max_file_size": 52428800,
            "intervals": [
                {
                    "max_range": 220,
                    "start_at": "00:00",
                    "name": "constant_active",
                    "interval": 1000,
                    "frequency": {
                        "38000": {
                            "bandwidth": 2425.15,
                            "pulse_length": 1024,
                            "mode": "active",
                            "power": 500,
                            "sample_interval": 256
                        },
                        "120000": {
                            "bandwidth": 8709.93,
                            "pulse_length": 256,
                            "mode": "active",
                            "power": 100,
                            "sample_interval": 64
                        },
                        "200000": {
                            "bandwidth": 10635,
                            "pulse_length": 256,
                            "mode": "active",
                            "power": 120,
                            "sample_interval": 64
                        }
                    },
                    "duration": "00:01:30",
                    "stop_repeating_at": "23:55",
                    "type": "constant"
                }
            ],
            "file_path": "QCT_1",
            "file_prefix": "OOI"
        },
        "er60_channels": {
            "GPT 200 kHz 00907207b7b1 6-2 OOI38|200": {
                "pulse_length": 0.000256,
                "frequency": 200000,
                "sample_interval": 0.000064,
                "power": 25,
                "mode": "passive"
            },
            "GPT 120 kHz 00907207b7dc 1-1 ES120-7CD": {
                "pulse_length": 0.000256,
                "frequency": 120000,
                "sample_interval": 0.000064,
                "power": 25,
                "mode": "passive"
            },
            "GPT  38 kHz 00907207b7b1 6-1 OOI.38|200": {
                "pulse_length": 0.001024,
                "frequency": 38000,
                "sample_interval": 0.000256,
                "power": 100,
                "mode": "passive"
            }
        },
        "gpts_enabled": false,
        "er60_status": {
            "executable": "c:/users/ooi/desktop/er60.lnk",
            "current_utc_time": "2014-05-28 21:31:44.929000",
            "current_running_interval": null,
            "pid": 3560,
            "host": "157.237.15.100",
            "scheduled_intervals_remaining": 96,
            "next_scheduled_interval": "2014-05-28 00:00:00.000000",
            "raw_output": {
                "max_file_size": 52428800,
                "sample_range": 30,
                "file_prefix": "OOI",
                "save_raw": true,
                "current_raw_filesize": null,
                "save_index": true,
                "save_bottom": true,
                "current_raw_filename": "OOI-D20140527-T110604.raw",
                "file_path": "D:\\data\\QCT_3"
            },
            "fs_root": "D:/",
            "port": 52890
        },
        "connected": true
        }
        """

        # config = json.loads(self.raw_data)
        # if not isinstance(config, dict):
        #        raise SampleException("ZPLSC status data is not a dictionary" %
        #                           self.raw_data)
        #
        # try:
        #     config = json.loads(self.raw_data)
        #
        #     connected = config[CONNECTED]
        #     for key in config[ER60_CHANNELS]:
        #         if '200 kHz' in key:
        #             active_200k_mode = config[ER60_CHANNELS][key][MODE]
        #             active_200k_power = config[ER60_CHANNELS][key][POWER]
        #             active_200k_pulse_length = config[ER60_CHANNELS][key][PULSE_LENGTH]
        #             active_200k_sample_interval = config[ER60_CHANNELS][key][SAMPLE_INTERVAL]
        #         elif '120 kHz' in key:
        #             active_120k_mode = config[ER60_CHANNELS][key][MODE]
        #             active_120k_power = config[ER60_CHANNELS][key][POWER]
        #             active_120k_pulse_length = config[ER60_CHANNELS][key][PULSE_LENGTH]
        #             active_120k_sample_interval = config[ER60_CHANNELS][key][SAMPLE_INTERVAL]
        #         elif '38 kHz' in key:
        #             active_38k_mode = config[ER60_CHANNELS][key][MODE]
        #             active_38k_power = config[ER60_CHANNELS][key][POWER]
        #             active_38k_pulse_length = config[ER60_CHANNELS][key][PULSE_LENGTH]
        #             active_38k_sample_interval = config[ER60_CHANNELS][key][SAMPLE_INTERVAL]
        #
        #
        #     er60_status = config[ER60_STATUS]
        #     current_utc_time = er60_status[CURRENT_UTC_TIME]
        #     executable = er60_status[EXECUTABLE]
        #     fs_root = er60_status[FS_ROOT]
        #     next_scheduled_interval = er60_status[NEXT_SCHEDULED_INTERVAL]
        #     host = er60_status[HOST]
        #     pid = er60_status[PID]
        #     #port = er60_status[PORT]
        #
        #     raw_output = config[ER60_STATUS][RAW_OUTPUT]
        #     current_raw_filename = raw_output[CURRENT_RAW_FILENAME]
        #     current_raw_filesize = raw_output[CURRENT_RAW_FILESIZE]
        #     file_path = raw_output[FILE_PATH]
        #     file_prefix = raw_output[FILE_PREFIX]
        #     max_file_size = raw_output[MAX_FILE_SIZE]
        #     sample_range = raw_output[SAMPLE_RANGE]
        #     save_bottom = raw_output[SAVE_BOTTOM]
        #     save_index = raw_output[SAVE_INDEX]
        #     save_raw = raw_output[SAVE_RAW]
        #     scheduled_interval_remaining = er60_status[SCHEDULED_INTERVAL_REMAINING]
        #     gpts_enabled = config[GPTS_ENABLED]
        #     schedule_filename = config[SCHEDULE_FILENAME]
        #
        #     # intervals = []
        #     # for each in config['schedule']['intervals']:
        #     #     d = {}
        #     #     d[ZPLSCStatusParticleKey.FREQ_38K_MODE] = each['frequency']['38000']['mode']
        #     #     intervals.append(d)
        #     #
        #     # for index, each in enumerate(intervals):
        #     #     for key, value in each.iteritems:
        #     #         value_id = '%s_%d' % (key, index)
        #     #         result.append({DataParticleKey.VALUE_ID: value_id, DataParticleKey.VALUE: value})
        #
        #
        # except KeyError:
        #      raise SampleException("ValueError while converting ZPLSC Status: [%s]" %
        #                           self.raw_data)
        #
        # result = [{DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_MODE,
        #            DataParticleKey.VALUE: active_200k_mode},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_POWER,
        #            DataParticleKey.VALUE: active_200k_power},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_PULSE_LENGTH,
        #             DataParticleKey.VALUE: active_200k_pulse_length},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_SAMPLE_INTERVAL,
        #            DataParticleKey.VALUE: active_200k_sample_interval},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_MODE,
        #            DataParticleKey.VALUE: active_120k_mode},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_POWER,
        #            DataParticleKey.VALUE: active_120k_power},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_PULSE_LENGTH,
        #             DataParticleKey.VALUE: active_120k_pulse_length},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_120K_SAMPLE_INTERVAL,
        #            DataParticleKey.VALUE: active_120k_sample_interval},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_POWER,
        #            DataParticleKey.VALUE: active_120k_power},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_PULSE_LENGTH,
        #             DataParticleKey.VALUE: active_38k_pulse_length},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_SAMPLE_INTERVAL,
        #            DataParticleKey.VALUE: active_38k_sample_interval},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_CURRENT_UTC_TIME,
        #            DataParticleKey.VALUE: current_utc_time},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_EXECUTABLE,
        #            DataParticleKey.VALUE: executable},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_FS_ROOT,
        #            DataParticleKey.VALUE: fs_root},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_NEXT_SCHEDULED_INTERVAL,
        #            DataParticleKey.VALUE: next_scheduled_interval},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_HOST,
        #            DataParticleKey.VALUE: host},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_PID,
        #            DataParticleKey.VALUE: pid},
        #           #{DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_PORT,
        #           #DataParticleKey.VALUE: port},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_CURRENT_RAW_FILENAME,
        #            DataParticleKey.VALUE: current_raw_filename},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_CURRENT_RAW_FILESIZE,
        #            DataParticleKey.VALUE: current_raw_filesize},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_FILE_PATH,
        #            DataParticleKey.VALUE: file_path},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_FILE_PREFIX,
        #            DataParticleKey.VALUE: file_prefix},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_MAX_FILE_SIZE,
        #            DataParticleKey.VALUE: max_file_size},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SAMPLE_RANGE,
        #            DataParticleKey.VALUE: sample_range},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SAVE_BOTTOM,
        #            DataParticleKey.VALUE: save_bottom},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SAVE_INDEX,
        #            DataParticleKey.VALUE: save_index},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SAVE_RAW,
        #            DataParticleKey.VALUE: save_raw},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SCHEDULED_INTERVAL_REMAINING,
        #            DataParticleKey.VALUE: scheduled_interval_remaining},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_GPTS_ENABLED,
        #            DataParticleKey.VALUE: gpts_enabled},
        #           {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SCHEDULE_FILENAME,
        #            DataParticleKey.VALUE: schedule_filename}]
        result = ' '
        return result


    ########################################################################
    # Autosample handlers
    ########################################################################
    def _handler_autosample_enter(self, *args, **kwargs):
        """
        Enter autosample mode
        """
        self._driver_event(DriverAsyncEvent.STATE_CHANGE)


    def _handler_autosample_stop(self):
        """
        Stop autosample mode
        """
        next_state = None
        next_agent_state = None
        result = None


        host_ip_address = self._param_dict.get_config_value(Parameter.FTP_IP_ADDRESS)
        host = 'https://' + host_ip_address

        self._stop_schedule(host)

        #self._do_cmd_no_resp(Command.STOP_AUTOSAMPLE)

        next_state = ProtocolState.COMMAND
        next_agent_state = ResourceAgentState.COMMAND

        return (next_state, (next_agent_state, result))



    ########################################################################
    # Direct access handlers.
    ########################################################################

    def _handler_direct_access_enter(self, *args, **kwargs):
        """
        Enter direct access state.
        """
        # Tell driver superclass to send a state change event.
        # Superclass will query the state.
        self._driver_event(DriverAsyncEvent.STATE_CHANGE)

        self._sent_cmds = []

    def _handler_direct_access_exit(self, *args, **kwargs):
        """
        Exit direct access state.
        """
        pass

    def _handler_direct_access_execute_direct(self, data):
        """
        """
        next_state = None
        result = None
        next_agent_state = None

        self._do_cmd_direct(data)

        # add sent command to list for 'echo' filtering in callback
        self._sent_cmds.append(data)

        return (next_state, (next_agent_state, result))

    def _handler_direct_access_stop_direct(self):
        """
        @throw InstrumentProtocolException on invalid command
        """
        next_state = None
        result = None

        next_state = ProtocolState.COMMAND
        next_agent_state = ResourceAgentState.COMMAND

        return (next_state, (next_agent_state, result))
