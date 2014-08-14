"""
@package mi.instrument.kut.ek60.ooicore.driver
@file marine-integrations/mi/instrument/kut/ek60/ooicore/driver.py
@author Richard Han
@brief Driver for the ooicore
Release notes:
This Driver supports the Kongsberg UnderWater Technology's EK60 Instrument.
"""

__author__ = 'Richard Han & Craig Risien'
__license__ = 'Apache 2.0'

from mi.instrument.kut.ek60.ooicore.zplsc_echogram import ZPLSCEchogram

from collections import defaultdict
from modest_image import ModestImage, imshow
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

import ftplib
import json
import re
import tempfile
import urllib2
import numpy as np
import pprint as pp

from struct import unpack

from xml.dom.minidom import parseString
from mi.core.exceptions import InstrumentParameterException, InstrumentException
from mi.core.instrument.driver_dict import DriverDictKey
from mi.core.instrument.protocol_param_dict import ParameterDictVisibility, ParameterDictType
from mock import self
import yaml

import string

from mi.core.log import get_logger
from mi.core.log import get_logging_metaclass

log = get_logger()

from mi.core.common import BaseEnum
from mi.core.exceptions import SampleException
from mi.core.exceptions import InstrumentProtocolException

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


# newline.
NEWLINE = '\r\n'

# Default Instrument's IP Address
DEFAULT_HOST = "https://128.193.64.201"
YAML_FILE_NAME = "driver_schedule.yaml"

USER_NAME = "ooi"
PASSWORD = "994ef22"

common_matches = {
    'float': r'-?\d*\.?\d+',
    'int': r'-?\d+',
    'str': r'\w+',
    'fn': r'\S+',
    'rest': r'.*\r\n',
    'tod': r'\d{8}T\d{6}',
    'data': r'[^\*]+',
    'crc': r'[0-9a-fA-F]{4}'
}

DEFAULT_CONFIG = {
            'file_prefix':    "Driver DEFAULT CONFIG_PREFIX",
            'file_path':      "DEFAULT_FILE_PATH",  #relative to filesystem_root/data
            'max_file_size':   288,  #50MB in bytes:  50 * 1024 * 1024

            'intervals': {
                'name': "default",
                'type': "constant",
                'start_at': "00:00",
                'duration': "00:15:00",
                'repeat_every': "01:00",
                'stop_repeating_at': "23:55",
                'interval': 1000,
                'max_range': 80,
                'frequency': {
                    38000: {
                        'mode': 'active',
                        'power': 100,
                        'pulse_length': 256,
                        },
                    120000: {
                        'mode': 'active',
                        'power': 100,
                        'pulse_length': 64,
                        },
                    200000: {
                        'mode': 'active',
                        'power': 120,
                        'pulse_length': 64,
                        },
                    }
            }
        }

DEFAULT_YAML = "# Driver DEFAULT_YAML file " + NEWLINE + \
               "--- " + NEWLINE + \
               "file_prefix:    \"DEFAULT_DRIVER\"" + NEWLINE + \
               "file_path:      \"DEFAULT_DRIVER\"" + NEWLINE + \
               "max_file_size:   299 " + NEWLINE + \
               "intervals: " + NEWLINE + \
               "name: \"default\"" + NEWLINE + \
               "type: \"constant\"" + NEWLINE + \
               "start_at:  \"00:00\"" + NEWLINE + \
               "duration:  \"00:15:00\"" + NEWLINE + \
               "repeat_every:   \"01:00\"" + NEWLINE + \
               "stop_repeating_at: \"23:55\"" + NEWLINE + \
               "interval:   1000" + NEWLINE + \
               "max_range:  80 " + NEWLINE + \
               "frequency: " + NEWLINE + \
               "  38000: " + NEWLINE + \
               "    mode:   active" + NEWLINE + \
               "    power:  100 " + NEWLINE + \
               "    pulse_length:   256" + NEWLINE + \
               "  120000: " + NEWLINE + \
               "    mode:   active" + NEWLINE + \
               "   power:  100 " + NEWLINE + \
               "pulse_length:   64" + NEWLINE + \
               "  200000: " + NEWLINE + \
               "    mode:   active" + NEWLINE +  \
               "   power:  120 " + NEWLINE + \
               "   pulse_length:   64"

# Config file name to be stored on the instrument server
ZPLSC_CONFIG_FILE_NAME = "zplsc_config.ymal"


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
SCHEDULED_INTERVALS_REMAINING = "scheduled_intervals_remaining"
START_AT = "start_at"
STOP_REPEATING_AT = "stop_repeating_at"
TYPE = "type"

# set global regex expressions to find all sample, annotation and NMEA sentences
SAMPLE_REGEX = r'RAW\d{1}'
SAMPLE_MATCHER = re.compile(SAMPLE_REGEX, re.DOTALL)

ANNOTATE_REGEX = r'TAG\d{1}'
ANNOTATE_MATCHER = re.compile(ANNOTATE_REGEX, re.DOTALL)

NMEA_REGEX = r'NME\d{1}'
NMEA_MATCHER = re.compile(NMEA_REGEX, re.DOTALL)

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
    START_AUTOSAMPLE = DriverEvent.START_AUTOSAMPLE
    STOP_AUTOSAMPLE = DriverEvent.STOP_AUTOSAMPLE
    EXECUTE_DIRECT = DriverEvent.EXECUTE_DIRECT
    ACQUIRE_STATUS = DriverEvent.ACQUIRE_STATUS

class Capability(BaseEnum):
    """
    Protocol events that should be exposed to users (subset of above).
    """
    START_AUTOSAMPLE = ProtocolEvent.START_AUTOSAMPLE
    STOP_AUTOSAMPLE = ProtocolEvent.STOP_AUTOSAMPLE
    START_DIRECT = ProtocolEvent.START_DIRECT
    EXECUTE_DIRECT = ProtocolEvent.EXECUTE_DIRECT
    STOP_DIRECT = ProtocolEvent.STOP_DIRECT
    ACQUIRE_STATUS  = ProtocolEvent.ACQUIRE_STATUS
    GET = ProtocolEvent.GET
    SET = ProtocolEvent.SET

class Parameter(DriverParameter):
    """
    Device specific parameters.
    """
    SCHEDULE = "schedule"
    FTP_IP_ADDRESS = "ftp_ip_address"
    FTP_USERNAME = "ftp_username"
    FTP_PASSWORD = "ftp_password"


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
    ZPLSC_CONNECTED = "zplsc_connected"                                     # Connected to a running ER 60 instance
    ZPLSC_ACTIVE_38K_MODE = "zplsc_active_38k_mode"                         # 38K Transducer transmit mode
    ZPLSC_ACTIVE_38K_POWER = "zplsc_active_38k_power"                       # 38K Transducer transmit power in W
    ZPLSC_ACTIVE_38K_PULSE_LENGTH = "zplsc_active_38k_pulse_length"         # 38K Transducer transmit pulse length in seconds
    ZPLSC_ACTIVE_38K_SAMPLE_INTERVAL = "zplsc_active_38k_sample_interval"   # Sample interval in seconds
    ZPLSC_ACTIVE_120K_MODE = "zplsc_active_120k_mode"                       # 120K Transducer transmit mode
    ZPLSC_ACTIVE_120K_POWER = "zplsc_active_120k_power"                     # 120K Transducer transmit power in W
    ZPLSC_ACTIVE_120K_PULSE_LENGTH = "zplsc_active_120k_pulse_length"       # 120K Transducer Transmit pulse length in seconds
    ZPLSC_ACTIVE_120K_SAMPLE_INTERVAL = "zplsc_active_120k_sample_interval" # 120K Sample Interval
    ZPLSC_ACTIVE_200K_MODE = "zplcs_active_200k_mode"                       # 200K Transducer transmit mode
    ZPLSC_ACTIVE_200K_POWER = "zplsc_active_200k_power"                     # 200K Transducer transmit power in W
    ZPLSC_ACTIVE_200K_PULSE_LENGTH = "zplsc_active_200k_pulse_length"       # 200K Transducer transmit pulse length in seconds
    ZPLSC_ACTIVE_200K_SAMPLE_INTERVAL = "zplsc_active_200k_sample_interval" # 200K Transducer sample interval
    ZPLSC_CURRENT_UTC_TIME = "zplsc_current_utc_time"                       # Current UTC Time
    ZPLSC_EXECUTABLE = "zplsc_executable"                                   # Executable used to launch ER60
    ZPLSC_FS_ROOT = "zplsc_fs_root"                                         # Root directory where data/logs/configs are stored
    ZPLSC_NEXT_SCHEDULED_INTERVAL = "zplsc_next_scheduled_interval"         # UTC time of next scheduled interval
    ZPLSC_HOST = "zplcsc_host"                                               # Host IP Address
    ZPLSC_PID = "zplsc_pid"                                                 # PID of running ER60 process
    ZPLSC_PORT = "zplsc_port"                                               # Host port number
    ZPLSC_CURRENT_RAW_FILENAME = "zplsc_current_raw_filename"               # File name of the current .raw file
    ZPLSC_CURRENT_RAW_FILESIZE = "zplsc_current_raw_filesize"               # File size of current .raw file
    ZPLSC_FILE_PATH = "zplsc_file_path"                                     # File storage path
    ZPLSC_FILE_PREFIX = "zplsc_file_prefix"                                 # Current file prefix
    ZPLSC_MAX_FILE_SIZE = "zplsc_max_file_size"                             # Maximum file size
    ZPLSC_SAMPLE_RANGE = "zplsc_sample_range"                               # Recording range
    ZPLSC_SAVE_BOTTOM = "zplsc_save_bottom"                                 # Save bottom file
    ZPLSC_SAVE_INDEX = "zplsc_save_index"                                   # Save index file
    ZPLSC_SAVE_RAW = "zplsc_save_raw"                                       # Save raw file
    ZPLSC_SCHEDULED_INTERVALS_REMAINING = "zplsc_scheduled_intervals_remaining" # Number of intervals remaining in running schedule
    ZPLSC_GPTS_ENABLED = "zplsc_gpts_enabled"                               # GPTs enabled
    ZPLSC_SCHEDULE_FILENAME = "zplsc_schedule_filename"                     # Filename for .yaml schedule file


class ZPLSCStatusParticle(DataParticle):
    """
    Routines for parsing raw data into a status particle structure. Override
    the building of values, and the rest should come along for free.

    Sample:
    {'connected': True,
     'er60_channels': {'GPT  38 kHz 00907207b7b1 6-1 OOI.38|200': {'frequency': 38000,
                                                                   'mode': 'active',
                                                                   'power': 100.0,
                                                                   'pulse_length': 0.000256,
                                                                   'sample_interval': 6.4e-05},
                       'GPT 120 kHz 00907207b7dc 1-1 ES120-7CD': {'frequency': 120000,
                                                                  'mode': 'active',
                                                                  'power': 100.0,
                                                                  'pulse_length': 6.4e-05,
                                                                  'sample_interval': 1.6e-05},
                       'GPT 200 kHz 00907207b7b1 6-2 OOI38|200': {'frequency': 200000,
                                                                  'mode': 'active',
                                                                  'power': 120.0,
                                                                  'pulse_length': 6.4e-05,
                                                                  'sample_interval': 1.6e-05}},
     'er60_status': {'current_running_interval': None,
                     'current_utc_time': '2014-07-08 22:34:18.667000',
                     'executable': 'c:/users/ooi/desktop/er60.lnk',
                     'fs_root': 'D:/',
                     'host': '157.237.15.100',
                     'next_scheduled_interval': None,
                     'pid': 1864,
                     'port': 56635,
                     'raw_output': {'current_raw_filename': 'OOI-D20140707-T214500.raw',
                                    'current_raw_filesize': None,
                                    'file_path': 'D:\\data\\QCT_1',
                                    'file_prefix': 'OOI',
                                    'max_file_size': 52428800,
                                    'sample_range': 220.0,
                                    'save_bottom': True,
                                    'save_index': True,
                                    'save_raw': True},
                     'scheduled_intervals_remaining': 0},
     'gpts_enabled': False,
     'schedule': {},
     'schedule_filename': 'qct_configuration_example_1.yaml'}

    """
    _data_particle_type = DataParticleType.ZPLSC_STATUS

    @staticmethod
    def regex():
        """
        Regular expression to match a sample pattern
        @return: regex string
        """

        pattern = r"""
            (?x)
            \{\"schedule_filename.*?\s\"connected.*?\}
            """ % common_matches

        pattern_working_with_status_txt = r"""
            (?x)
            \{\'connected.*?\s\'schedule_filename.*?\}
            """ % common_matches
            #\s+\'schedule_filename.*?yaml\'\}

        # pattern_working = r"""
        #     (?x)
        #     \{\'connected\'\:.*$
        #     \s+\'er60_channels.*$
        #     \s+\'mode.*$
        #     \s+\'power.*$
        #     \s+\'pulse_length.*$
        #     \s+\'sample_interval.*$
        #     \s+\'GPT\s120\skHz.*$
        #     \s+\'mode.*$
        #     \s+\'power.*$
        #     \s+\'pulse_length.*$
        #     \s+\'sample_interval.*$
        #     \s+\'GPT\s200\skHz.*$
        #     \s+\'mode.*$
        #     \s+\'power.*$
        #     \s+\'pulse_length.*$
        #     \s+\'sample_interval.*$
        #     \s+\'er60_status.*$
        #     \s+\'current_utc_time.*$
        #     \s+\'executable.*$
        #     \s+\'fs_root.*$
        #     \s+\'host.*$
        #     \s+\'next_scheduled_interval.*$
        #     \s+\'pid.*$
        #     \s+\'port.*$
        #     \s+\'raw_output.*$
        #     \s+\'current_raw_filesize.*$
        #     \s+\'file_path.*$
        #     \s+\'file_prefix.*$
        #     \s+\'max_file_size.*$
        #     \s+\'sample_range.*$
        #     \s+\'save_bottom.*$
        #     \s+\'save_index.*$
        #     \s+\'save_raw.*$
        #     \s+\'scheduled_intervals_remaining.*$
        #     \s+\'gpts_enabled.*$
        #     \s+\'schedule.*$
        #     \s+\'schedule_filename.*?yaml\'\}
        #     """ % common_matches

        return pattern



    @staticmethod
    def regex_compiled():
        """
        get the compiled regex pattern
        @return: compiled re
        """
        log.debug("regex_compiled enter...")
        return re.compile(ZPLSCStatusParticle.regex(), re.MULTILINE | re.DOTALL)

    def _build_parsed_values(self):
        """
        Parse ZPLSC Status response and return the ZPLSC Status particles
        @throws SampleException If there is a problem with sample
        """

        log.debug("_build_parsed_values enter...")
        try:
            log.debug("status raw_data = %s", self.raw_data)

            # match = ZPLSCStatusParticle.regex_compiled().match(self.raw_data)
            #
            # if not match:
            #     raise SampleException("No regex match of ZPLSC status data: [%s]" %
            #                       self.raw_data)

            #config = yaml.load(self.raw_data)
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

            if er60_status[NEXT_SCHEDULED_INTERVAL] is None:
                next_scheduled_interval = 'None'
            else:
                next_scheduled_interval = er60_status[NEXT_SCHEDULED_INTERVAL]

            host = er60_status[HOST]
            if er60_status[PID] is None:
                log.debug('PID is None')
                pid = 0
            else :
                pid = er60_status[PID]
            port = er60_status[PORT]

            raw_output = config[ER60_STATUS][RAW_OUTPUT]
            current_raw_filename = raw_output[CURRENT_RAW_FILENAME]

            if raw_output[CURRENT_RAW_FILESIZE] is None:
                current_raw_filesize = 0
            else:
                current_raw_filesize = raw_output[CURRENT_RAW_FILESIZE]

            file_path = raw_output[FILE_PATH]
            file_prefix = raw_output[FILE_PREFIX]
            max_file_size = raw_output[MAX_FILE_SIZE]
            sample_range = raw_output[SAMPLE_RANGE]
            save_bottom = raw_output[SAVE_BOTTOM]
            save_index = raw_output[SAVE_INDEX]
            save_raw = raw_output[SAVE_RAW]
            scheduled_intervals_remaining = er60_status[SCHEDULED_INTERVALS_REMAINING]
            gpts_enabled = config[GPTS_ENABLED]
            schedule = config[SCHEDULE]
            schedule_filename = config[SCHEDULE_FILENAME]

        except KeyError:
             raise SampleException("ValueError while converting ZPLSC Status: [%s]" %
                                  self.raw_data)

        result = [{DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_CONNECTED,
                   DataParticleKey.VALUE: connected},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_200K_MODE,
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
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_MODE,
                   DataParticleKey.VALUE: active_38k_mode},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_ACTIVE_38K_POWER,
                   DataParticleKey.VALUE: active_38k_power},
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
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_PORT,
                    DataParticleKey.VALUE: port},
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
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SCHEDULED_INTERVALS_REMAINING,
                    DataParticleKey.VALUE: scheduled_intervals_remaining},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_GPTS_ENABLED,
                    DataParticleKey.VALUE: gpts_enabled},
                  {DataParticleKey.VALUE_ID: ZPLSCStatusParticleKey.ZPLSC_SCHEDULE_FILENAME,
                    DataParticleKey.VALUE: schedule_filename}]
        print "build_parsed_value result = %s", result

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

    __metaclass__ = get_logging_metaclass(log_level='debug')

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

        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.ENTER, self._handler_command_enter)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.EXIT, self._handler_command_exit)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.START_DIRECT, self._handler_command_start_direct)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.START_AUTOSAMPLE, self._handler_command_autosample)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.ACQUIRE_STATUS, self._handler_command_acquire_status)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.GET, self._handler_command_get)
        self._protocol_fsm.add_handler(ProtocolState.COMMAND, ProtocolEvent.SET, self._handler_command_set)

        self._protocol_fsm.add_handler(ProtocolState.AUTOSAMPLE, ProtocolEvent.STOP_AUTOSAMPLE, self._handler_autosample_stop)

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

        # Add response handlers for device commands.
        self._add_response_handler(Command.GET, self._parse_get_response)
        self._add_response_handler(Command.SET, self._parse_set_response)
        #self._add_response_handler(Command.STATUS, self._parse_status_response)

        # Add sample handlers.

        # State state machine in UNKNOWN state.
        self._protocol_fsm.start(ProtocolState.UNKNOWN)

        # commands sent sent to device to be filtered in responses for telnet DA
        self._sent_cmds = []

        self._chunker = StringChunker(self.sieve_function)


    @staticmethod
    def sieve_function(raw_data):
        """
        The method that splits samples
        """

        matchers = []
        return_list = []

        log.debug("sieve_function enters...")
        matchers.append(ZPLSCStatusParticle.regex_compiled())

        for matcher in matchers:
            log.debug('matcher: %r raw_data: %r', matcher.pattern, raw_data)
            for match in matcher.finditer(raw_data):
                return_list.append((match.start(), match.end()))

        log.debug("return_list : %s", return_list)
        return return_list

    def _build_param_dict(self):
        """
        Populate the parameter dictionary with parameters.
        For each parameter key, add match string, match lambda function,
        and value formatting function for set commands.
        """

        self._param_dict.add(Parameter.SCHEDULE,
                             r'schedule:\s+(.*)',
                             lambda match : match.group(1),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Schedule",
                             startup_param = True,
                             direct_access = False,
                             default_value = yaml.dump(DEFAULT_CONFIG, default_flow_style=False),
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FTP_IP_ADDRESS,
                             r'ftp address:\s+(\d\d\d\d\.\d\d\d\d\.\d\d\d\d\.\d\d\d)',
                             lambda match : match.group(1),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="FTP IP Address",
                             startup_param = True,
                             direct_access = False,
                             default_value = DEFAULT_HOST,
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FTP_USERNAME,
                             r'username:(.*)',
                             lambda match : match.group(1),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="FTP User Name",
                             startup_param = True,
                             direct_access = False,
                             default_value = USER_NAME,
                             visibility=ParameterDictVisibility.READ_WRITE)

        self._param_dict.add(Parameter.FTP_PASSWORD,
                             r'password:(.*)',
                             lambda match : match.group(1),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="FTP Password",
                             startup_param = True,
                             direct_access = False,
                             default_value = PASSWORD,
                             visibility=ParameterDictVisibility.READ_WRITE)

    def _ftp_schedule_file(self):
        """
        Construct a yaml schedule file and
        ftp the file to the Instrument server
        """

        #  Create a temporary file and write the schedule yaml information
        # to the file
        try:

            config_file = tempfile.TemporaryFile()
            log.debug("temporary file created")

            if ((config_file == None) or (not isinstance(config_file, file))):
                raise InstrumentException("config_file is not a tempfile!")

            config_file.write(self._param_dict.get(Parameter.SCHEDULE))
            config_file.seek(0)
            log.debug("finished writing config file:  %s", self._param_dict.get(Parameter.SCHEDULE))

        except Exception as err:
            log.error("Create schedule yaml file exception :" + str(err))
            raise err

        #  FTP the schedule file to the ZPLSC server
        try:
            log.debug("Create a ftp session")
            host = self._param_dict.get_config_value(Parameter.FTP_IP_ADDRESS)
            log.debug("Got host ip address %s ", host)

            ftp_session = ftplib.FTP()
            ftp_session.connect(host)
            ftp_session.login(USER_NAME, PASSWORD,"")
            log.debug("ftp session was created...")

            ftp_session.set_pasv(0)
            ftp_session.cwd("config")

            ftp_session.storlines('STOR ' + YAML_FILE_NAME, config_file)
            files = ftp_session.dir()

            log.debug("*** Config ymal file sent")

            ftp_session.quit()
            config_file.close()

        except (ftplib.socket.error, ftplib.socket.gaierror), e:
            log.error("ERROR: cannot reach FTP Host %s " % (host))
            raise InstrumentException("ERROR: cannot reach FTP Host %s " % (host))

        log.debug("*** FTP %s to ftp host %s successfully" % (YAML_FILE_NAME, host))


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
           get_cmd = 'get' + NEWLINE
        except KeyError:
           raise InstrumentParameterException('Unknown driver parameter %s' % param)

        return get_cmd

    def _build_set_command(self, cmd, param, val):
        """
        Build handler for set commands.
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

        for line in response.split(NEWLINE):
            self._param_dict.update(line)

        return response


    def _parse_status_response(self, response, prompt):
        """
        Parse handler for status response.
        @param response status command response string.
        @param prompt prompt following command response.
        @throws InstrumentProtocolException if response is invalid.
        """
        return response


    def _got_chunk(self, chunk, timestamp):
        """
        The base class got_data has gotten a chunk from the chunker.  Pass it to extract_sample
        with the appropriate particle objects and REGEXes.
        """
        if not (self._extract_sample(ZPLSCStatusParticle, ZPLSCStatusParticle.regex_compiled(), chunk, timestamp)):
             raise InstrumentProtocolException("Unhandled chunk")


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
        self._cmd_dict.add(Capability.GET, display_name="get")
        self._cmd_dict.add(Capability.SET, display_name="set")
        self._cmd_dict.add(Capability.START_DIRECT, display_name="start direct")
        self._cmd_dict.add(Capability.STOP_DIRECT, display_name="stop direct")
        self._cmd_dict.add(Capability.EXECUTE_DIRECT, display_name="execute direct")
        self._cmd_dict.add(Capability.ACQUIRE_STATUS, display_name="acquire status")

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
        @retval (next_state, next_agent_state)
        """

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

        self._init_params()

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
        #result = None
        result_vals = {}

        # Retrieve required parameter.
        # Raise if no parameter provided, or not a dict.
        try:
            params = args[0]

        except IndexError:
            raise InstrumentParameterException('_handler_command_get requires a parameter dict.')

        if Parameter.ALL in params:
            log.debug("Parameter ALL in params")
            params = Parameter.list()
            params.remove(Parameter.ALL)

        log.debug("_handler_command_get: params = %s", params)

        if ((params == None) or (not isinstance(params, list))):
            raise InstrumentParameterException("GET parameter list not a list!")

        # fill the return values from the update
        for param in params:
            if not Parameter.has(param):
                raise InstrumentParameterException("Invalid parameter!")
            result_vals[param] = self._param_dict.get(param)
            self._param_dict.get_config_value(param)
        result = result_vals

        log.debug("Get finished, next_state: %s, result: %s", next_state, result)
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

        # For each key, val in the params, set the param dictionary.
        old_config = self._param_dict.get_config()
        self._set_params(params, startup)

        new_config = self._param_dict.get_config()
        if old_config != new_config :
            self._driver_event(DriverAsyncEvent.CONFIG_CHANGE)

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
            if (key == Parameter.SCHEDULE):

                self._ftp_schedule_file()

                # Load the schedule file
                host = "https://" + self._param_dict.get(Parameter.FTP_IP_ADDRESS)
                log.debug("stop the current schedule file")
                res = self._stop_schedule(host)
                log.debug("upload driver yaml file to host %s", host)
                res = self.load_schedule(YAML_FILE_NAME, host)
                log.debug(" result from load = %s", res)

        log.debug("set complete, update params")


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

    def _get_status(self, host=DEFAULT_HOST):

        log.debug("")

        url = host + '/status.json'
        req = urllib2.Request(url)
        f = urllib2.urlopen(req)
        res = f.read()
        log.debug(" result of fread = %r", res)
        f.close()
        return res

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


    def _start_schedule(self, host=DEFAULT_HOST):
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

        result = None

        # FTP the driver schedule file to the instrument server
        self._ftp_schedule_file()

        # Stop the current running schedule file just in case one is running and
        # start load the driver schedule file
        host = "https://" + self._param_dict.get(Parameter.FTP_IP_ADDRESS)
        log.debug("stop the current schedule file")
        self._stop_schedule(host)
        log.debug("upload driver yaml file to host %s", host)
        res = self.load_schedule(YAML_FILE_NAME, host)
        log.debug(" result from load = %s", res)
        log.debug(" load result = %s", res['result'])
        if res['result'] != 'OK':
            raise InstrumentException('Load Instrument Schedule File Error.')

        res = self._start_schedule(host)
        log.debug(" result from start_schedule = %s", res)
        if res['result'] != 'OK':
            raise InstrumentException('Start Schedule File Error.')

        next_state = ProtocolState.AUTOSAMPLE
        next_agent_state = ResourceAgentState.STREAMING

        return (next_state, (next_agent_state, result))

    def _handler_command_acquire_status(self, *args, **kwargs):
        """ Acquire status from the instrument"""

        log.debug("_handler_command_acquire_status enter")

        next_state = None
        next_agent_state = None
        result = None

        ip_address = self._param_dict.get_config_value(Parameter.FTP_IP_ADDRESS)
        host = 'https://' + ip_address

        response = self._get_status(host)
        log.debug("response from status begins = %s", response)
        log.debug("response from status ends")

        particle = ZPLSCStatusParticle(response, port_timestamp=self._param_dict.get_current_timestamp())
        self._driver_event(DriverAsyncEvent.SAMPLE, particle.generate())

        return (next_state, (next_agent_state, result))


    def _parse_status_response(self, response):
        """
        Parse ZPLSC Status response and return the ZPLSC Status particles
        @throws SampleException If there is a problem with sample
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

        res = self._stop_schedule(host)
        log.debug("handler_autosample_stop: stop schedule returns %r", res)

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

    # Create functions to read the datagrams contained in the raw file. The
    # code below was developed using example Matlab code produced by Lars Nonboe
    # Andersen of Simrad and provided to us by Dr. Kelly Benoit-Bird and the
    # raw data file format specification in the Simrad EK60 manual, with reference
    # to code in Rick Towler's readEKraw toolbox.

    def read_datagram_header(self, chunk):
        """
        Reads the EK60 raw data file datagram header
        """
        # setup unpack structure and field names
        field_names = ('datagram_type', 'internal_time')
        fmt = '<4sll'

        # read in the values from the byte string chunk
        values = list(unpack(fmt, chunk))

        # the internal date time structure represents the number of 100
        # nanosecond intervals since January 1, 1601. this is known as the
        # Windows NT Time Format.
        internal = values[2] * (2**32) + values[1]

        # create the datagram header dictionary
        datagram_header = dict(zip(field_names, [values[0], internal]))
        return datagram_header

    def read_config_header(self, chunk):
        """
        Reads the EK60 raw data file configuration header information
        from the byte string passed in as a chunk
        """
        # setup unpack structure and field names
        field_names = ('survey_name', 'transect_name', 'sounder_name',
                       'version', 'transducer_count')
        fmt = '<128s128s128s30s98sl'

        # read in the values from the byte string chunk
        values = list(unpack(fmt, chunk))
        values.pop(4)  # drop the spare field

        # strip the trailing zero byte padding from the strings
        for i in [0, 1, 2, 3]:
            values[i] = values[i].strip('\x00')

        # create the configuration header dictionary
        config_header = dict(zip(field_names, values))
        return config_header

    def read_config_transducer(self, chunk):
        """
        Reads the EK60 raw data file configuration transducer information
        from the byte string passed in as a chunk
        """

        # setup unpack structure and field names
        field_names = ('channel_id', 'beam_type', 'frequency', 'gain',
                       'equiv_beam_angle', 'beam_width_alongship', 'beam_width_athwartship',
                       'angle_sensitivity_alongship', 'angle_sensitivity_athwartship',
                       'angle_offset_alongship', 'angle_offset_athwart', 'pos_x', 'pos_y',
                       'pos_z', 'dir_x', 'dir_y', 'dir_z', 'pulse_length_table', 'gain_table',
                       'sa_correction_table', 'gpt_software_version')
        fmt = '<128sl15f5f8s5f8s5f8s16s28s'

        # read in the values from the byte string chunk
        values = list(unpack(fmt, chunk))

        # convert some of the values to arrays
        pulse_length_table = np.array(values[17:22])
        gain_table = np.array(values[23:28])
        sa_correction_table = np.array(values[29:34])

        # strip the trailing zero byte padding from the strings
        for i in [0, 35]:
            values[i] = values[i].strip('\x00')

        # put it back together, dropping the spare strings
        config_transducer = dict(zip(field_names[0:17], values[0:17]))
        config_transducer[field_names[17]] = pulse_length_table
        config_transducer[field_names[18]] = gain_table
        config_transducer[field_names[19]] = sa_correction_table
        config_transducer[field_names[20]] = values[35]
        return config_transducer

    def read_text_data(self, chunk, name, string_length):
        """
        Reads either the NMEA or annotation text strings from the EK60 raw data
        file from the byte string passed in as a chunk
        """
        # setup unpack structure and field names
        field_names = ('text')
        fmt = '<%ds' % string_length

        # read in the values from the byte string chunk
        text = unpack(fmt, chunk)
        text = text.strip('\x00')

        # create the text datagram dictionary
        text_datagram = {field_names, text}
        return text_datagram

    def read_sample_data(self, chunk):
        """
        Reads the EK60 raw sample datagram from the byte string passed in as a chunk
        """
        # setup unpack structure and field names
        field_names = ('channel_number', 'mode', 'transducer_depth', 'frequency',
                       'transmit_power', 'pulse_length', 'bandwidth',
                       'sample_interval', 'sound_velocity', 'absorbtion_coefficient',
                       'heave', 'roll', 'pitch', 'temperature', 'trawl_upper_depth_valid',
                       'trawl_opening_valid', 'trawl_upper_depth', 'trawl_opening',
                       'offset', 'count')
        fmt = '<2h12f2h2f2l'

        # read in the values from the byte string chunk
        values = list(unpack(fmt, chunk[:72]))
        sample_datagram = dict(zip(field_names, values))

        # extract the mode and sample counts
        mode = values[1]
        count = values[-1]

        # extract and uncompress the power measurements
        if mode != 2:
            fmt = '<%dh' % count
            strt = 72
            stop = strt + (count * 2)
            power = np.array(unpack(fmt, chunk[strt:stop]))
            power = power * 10. * np.log10(2) / 256.
            sample_datagram['power'] = power

        # extract the alongship and athwartship angle measurements
        if mode > 1:
            fmt = '<%db' % (count * 2)
            strt = stop
            stop = strt + (count * 2)
            values = list(unpack(fmt, chunk[strt:stop]))
            athwart = np.array(values[0::2])
            along = np.array(values[1::2])
            field_names += ('alongship', 'athwartship')
            sample_datagram['alongship'] = along
            sample_datagram['athwartship'] = athwart

        return sample_datagram

    def generate_echograms(self, filepath, raw_file):
        """
        Reads the EK60 raw sample datagram and generate an echograms
        """

        echogram_gen = ZPLSCEchogram(filepath, raw_file)
        echogram_gen.generate_echograms()

        # LENGTH_SIZE = 4
        # DATAGRAM_HEADER_SIZE = 12
        # CONFIG_HEADER_SIZE = 516
        # CONFIG_TRANSDUCER_SIZE = 320
        #
        # # read in the binary data file and store as an object for further processing
        # #with open('ion_functions/data/matlab_scripts/zplsc/data/Baja_2013-D20131020-T030020.raw', 'rb') as f:
        # with open(raw_file, 'rb') as f:
        # # with open('ion_functions/data/matlab_scripts/zplsc/data/OOI_BT-D20140619-T000000.raw', 'rb') as f:
        #     raw = f.read()
        #
        # # set starting byte count
        # byte_cnt = 0
        #
        # # read the configuration datagram, output at the beginning of the file
        # length1 = unpack('<l', raw[byte_cnt:byte_cnt+4])
        # byte_cnt += LENGTH_SIZE
        # #byte_cnt += 4
        #
        # # configuration datagram header
        # datagram_header = self.read_datagram_header(raw[byte_cnt:byte_cnt+12])
        # byte_cnt += DATAGRAM_HEADER_SIZE
        # #byte_cnt += 12
        #
        # # configuration: header
        # config_header = self.read_config_header(raw[byte_cnt:byte_cnt+516])
        # byte_cnt += CONFIG_HEADER_SIZE
        # #byte_cnt += 516
        #
        # # configuration: transducers (1 to 7 max)
        # config_transducer = defaultdict(dict)
        # for i in range(config_header['transducer_count']):
        #     config_transducer['transducer'][i] = self.read_config_transducer(raw[byte_cnt:byte_cnt+320])
        #     byte_cnt += CONFIG_TRANSDUCER_SIZE
        #     #byte_cnt += 320
        #
        # length2 = unpack('<l', raw[byte_cnt:byte_cnt+4])
        # if not (length1[0] == length2[0] == byte_cnt+4-8):
        #     raise ValueError("length of datagram and bytes read do not match")
        #
        # #pp.pprint(datagram_header.items())
        # #pp.pprint(config_header.items())
        # #pp.pprint(config_transducer.items())
        #
        # #create 3, which is the max # of transducers EA will have, sets of empty lists
        # trans_array_1 = []
        # trans_array_1_time = []
        # trans_array_2 = []
        # trans_array_2_time = []
        # trans_array_3 = []
        # trans_array_3_time = []
        #
        # # index through the sample datagrams, collecting the data needed to create the echograms
        # count = 0
        # for i in re.finditer(SAMPLE_REGEX, raw):
        #     # set the starting byte
        #     strt = i.start() - 4
        #
        #     # extract the length of the datagram
        #     length1 = unpack('<l', raw[strt:strt+4])
        #     strt += 4
        #
        #     # parse the sample datagram header
        #     sample_datagram_header = self.read_datagram_header(raw[strt:strt+12])
        #     strt += 12
        #
        #     # parse the sample datagram contents
        #     sample_datagram = self.read_sample_data(raw[strt:strt+length1[0]])
        #
        #     #if count == 0:
        #     #    pp.pprint(sample_datagram_header.items())
        #     #    pp.pprint(sample_datagram.items())
        #
        #     # populate the various lists with data from each of the transducers
        #     if sample_datagram['channel_number'] == 1:
        #         trans_array_1.append([sample_datagram['power']])
        #         trans_array_1_time.append([sample_datagram_header['internal_time']])
        #         if count <= 2:
        #             # extract various calibration parameters
        #             td_1_f = sample_datagram['frequency']
        #             td_1_c = sample_datagram['sound_velocity']
        #             td_1_t = sample_datagram['sample_interval']
        #             td_1_alpha = sample_datagram['absorbtion_coefficient']
        #             td_1_depth = sample_datagram['transducer_depth']
        #             td_1_transmitpower = sample_datagram['transmit_power']
        #             # calculate sample thickness (in range)
        #             td_1_dR = td_1_c * td_1_t / 2
        #             #Example data that one might need for various calculations later on
        #             #td_1_gain = config_transducer['transducer'][0]['gain']
        #             #td_1_gain_table = config_transducer['transducer'][0]['gain_table']
        #             #td_1_pulse_length_table = config_transducer['transducer'][0]['pulse_length_table']
        #             #td_1_phi_equiv_beam_angle = config_transducer['transducer'][0]['equiv_beam_angle']
        #     elif sample_datagram['channel_number'] == 2:
        #         trans_array_2.append([sample_datagram['power']])
        #         trans_array_2_time.append([sample_datagram_header['internal_time']])
        #         if count <= 2:
        #             # extract various calibration parameters
        #             td_2_f = sample_datagram['frequency']
        #             td_2_c = sample_datagram['sound_velocity']
        #             td_2_t = sample_datagram['sample_interval']
        #             td_2_alpha = sample_datagram['absorbtion_coefficient']
        #             td_2_depth = sample_datagram['transducer_depth']
        #             td_2_transmitpower = sample_datagram['transmit_power']
        #             # calculate sample thickness (in range)
        #             td_2_dR = td_2_c * td_2_t / 2
        #             #Example data that one might need for various calculations later on
        #             #td_2_gain = config_transducer['transducer'][1]['gain']
        #             #td_2_gain_table = config_transducer['transducer'][1]['gain_table']
        #             #td_2_pulse_length_table = config_transducer['transducer'][1]['pulse_length_table']
        #             #td_2_phi_equiv_beam_angle = config_transducer['transducer'][1]['equiv_beam_angle']
        #     elif sample_datagram['channel_number'] == 3:
        #         trans_array_3.append([sample_datagram['power']])
        #         trans_array_3_time.append([sample_datagram_header['internal_time']])
        #         if count <= 2:
        #             # extract various calibration parameters
        #             td_3_f = sample_datagram['frequency']
        #             td_3_c = sample_datagram['sound_velocity']
        #             td_3_t = sample_datagram['sample_interval']
        #             td_3_alpha = sample_datagram['absorbtion_coefficient']
        #             td_3_depth = sample_datagram['transducer_depth']
        #             td_3_transmitpower = sample_datagram['transmit_power']
        #             # calculate sample thickness (in range)
        #             td_3_dR = td_3_c * td_3_t / 2
        #             #Example data that one might need for various calculations later on
        #             #td_3_gain = config_transducer['transducer'][2]['gain']
        #             #td_3_gain_table = config_transducer['transducer'][2]['gain_table']
        #             #td_3_pulse_length_table = config_transducer['transducer'][2]['pulse_length_table']
        #             #td_3_phi_equiv_beam_angle = config_transducer['transducer'][2]['equiv_beam_angle']
        #
        # #Convert lists to np arrays and rotate them
        # trans_array_1 = np.flipud(np.rot90(np.atleast_2d(np.squeeze(trans_array_1))))
        # trans_array_2 = np.flipud(np.rot90(np.atleast_2d(np.squeeze(trans_array_2))))
        # trans_array_3 = np.flipud(np.rot90(np.atleast_2d(np.squeeze(trans_array_3))))
        #
        # # reference time "seconds since 1970-01-01 00:00:00"
        # ref_time = datetime(1970, 1, 1, 0, 0, 0)
        # ref_time = mdates.date2num(ref_time)
        #
        # #subset/decimate the x & y ticks so that we don't plot everyone
        # deci_x = 200
        # deci_y = 1000
        #
        # if np.size(trans_array_1_time) > 0:
        #     self.generate_plots(trans_array_1, trans_array_1_time, ref_time, td_1_f, td_1_dR, 'Transducer # 1: ', '/Users/admin/marine-integrations/td1.png')
        #
        #
        # if np.size(trans_array_2_time) > 0:
        #     self.generate_plots(trans_array_2, trans_array_2_time, ref_time, td_2_f, td_2_dR, 'Transducer # 2: ', '/Users/admin/marine-integrations/td2.png')
        #
        #
        # if np.size(trans_array_3_time) > 0:
        #     self.generate_plots(trans_array_3, trans_array_3_time, ref_time, td_3_f, td_3_dR, 'Transducer # 3: ', '/Users/admin/marine-integrations/td3.png')



    # def generate_plots(self, trans_array, trans_array_time, ref_time, td_f, td_dR, title, filename):
    #     """
    #     Generate plots for an transducer
    #     @param trans_array Transducer data array
    #     @param trans_array_time Transducer internal time array
    #     @param ref_time reference time "seconds since 1970-01-01 00:00:00"
    #     @param td_f Transducer frequency
    #     @param td_dR Transducer's sample thickness (in range)
    #     @param title Transducer title
    #     @param filename png file name to save the figure to
    #     """
    #     #subset/decimate the x & y ticks so that we don't plot everyone
    #     deci_x = 200
    #     deci_y = 1000
    #
    #     #Only generate plots for the transducers that have data
    #     if np.size(trans_array_time) > 0:
    #
    #         # determine size of the data array
    #         pSize = np.shape(trans_array)
    #         # create range vector (in meters)
    #         td_depth = np.arange(0, pSize[0]) * td_dR
    #
    #         # convert time, which represents the number of 100-nanosecond intervals that
    #         # have elapsed since 12:00 A.M. January 1, 1601 Coordinated Universal Time (UTC)
    #         # to unix time, i.e. seconds since 1970-01-01 00:00:00.
    #         # 11644473600 == difference between 1601 and 1970
    #         # 1e7 == divide by 10 million to convert to seconds
    #         trans_array_time = np.array(trans_array_time) / 1e7 - 11644473600
    #         trans_array_time = trans_array_time / 60 / 60 / 24
    #         trans_array_time = trans_array_time + ref_time
    #         trans_array_time = np.squeeze(trans_array_time)
    #
    #         min_depth = 0
    #         max_depth = pSize[0]
    #
    #         min_time = 0
    #         max_time = np.size(trans_array_time)
    #
    #         min_db = -180
    #         max_db = -59
    #
    #         cbar_ticks = np.arange(min_db, max_db)
    #         cbar_ticks = cbar_ticks[::20]
    #
    #         # rotates and right aligns the x labels, and moves the bottom of the
    #         # axes up to make room for them
    #         ax = plt.gca()
    #         cax = imshow(ax, trans_array, interpolation='none', aspect='auto', cmap='jet', vmin=min_db, vmax=max_db)
    #         plt.grid(False)
    #         figure_title = 'Converted Power: ' + title + 'Frequency: ' + str(td_f)
    #         plt.title(figure_title, fontsize=12)
    #         plt.xlabel('time (UTC)', fontsize=10)
    #         plt.ylabel('depth (m)', fontsize=10)
    #
    #         #format trans_array_time array so that it can be used to label the x-axis
    #         xticks = mdates.num2date(trans_array_time[0::200])
    #         xticks_fmted = []
    #         for i in range(0, len(xticks)):
    #             a = xticks[i].strftime('%Y-%m-%d %H:%M:%S')
    #             xticks_fmted.append([a])
    #
    #         x = np.arange(0, pSize[1])
    #         #subset the xticks so that we don't plot everyone
    #         x = x[::deci_x]
    #         y = np.arange(0, pSize[0])
    #         #subset the yticks so that we don't plot everyone
    #         y = y[::deci_y]
    #         yticks = np.round(td_depth[::deci_y], decimals=0)
    #         plt.xticks(x, xticks_fmted, rotation=25, horizontalalignment='right', fontsize=10)
    #         plt.yticks(y, yticks, fontsize=10)
    #         plt.tick_params(axis="y", labelcolor="k", pad=4)
    #         plt.tick_params(axis="x", labelcolor="k", pad=4)
    #
    #         #set the x and y limits
    #         plt.ylim(max_depth, min_depth)
    #         plt.xlim(min_time, max_time)
    #
    #         #plot the colorbar
    #         cb = plt.colorbar(cax, orientation='horizontal', ticks=cbar_ticks, shrink=.6)
    #         cb.ax.set_xticklabels(cbar_ticks, fontsize=8)  # vertically oriented colorbar
    #         cb.set_label('dB', fontsize=10)
    #         cb.ax.set_xlim(-180, -60)
    #
    #         plt.tight_layout()
    #         #adjust the subplot so that the x-tick labels will fit on the canvas
    #         plt.subplots_adjust(bottom=0.1)
    #         #reposition the cbar
    #         cb.ax.set_position([.4, .05, .4, .1])
    #         #save the figure
    #         plt.savefig(filename, dpi=300)
    #         #close the figure
    #         plt.close()
