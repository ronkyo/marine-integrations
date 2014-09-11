"""
@package mi.instrument.teledyne.workhorse.adcp.driver
@file marine-integrations/mi/instrument/teledyne/workhorse/adcp/driver.py
@author Sung Ahn
@brief Driver for the ADCP
Release notes:

Generic Driver for ADCPS-K, ADCPS-I, ADCPT-B and ADCPT-DE
"""
from mi.core.common import Units, Prefixes
from mi.core.common import BaseEnum
from mi.instrument.teledyne.workhorse.driver import WorkhorseInstrumentDriver
from mi.instrument.teledyne.workhorse.driver import WorkhorseProtocol

from mi.instrument.teledyne.driver import TeledyneScheduledJob
from mi.instrument.teledyne.driver import TeledyneCapability
from mi.instrument.teledyne.driver import TeledyneInstrumentCmds
from mi.instrument.teledyne.driver import TeledyneProtocolState
from mi.instrument.teledyne.driver import TeledynePrompt

from mi.instrument.teledyne.workhorse.driver import NEWLINE
from mi.core.log import get_logger

log = get_logger()

from mi.core.instrument.protocol_param_dict import ParameterDictVisibility
from mi.core.instrument.protocol_param_dict import ParameterDictType
from mi.instrument.teledyne.workhorse.driver import WorkhorseParameter
from mi.instrument.teledyne.driver import TeledyneProtocolEvent


class Prompt(TeledynePrompt):
    """
    Device i/o prompts..
    """


class Parameter(WorkhorseParameter):
    """
    Device parameters
    """
    #
    # set-able parameters
    #


class ProtocolEvent(TeledyneProtocolEvent):
    """
    Protocol events
    """


class Capability(TeledyneCapability):
    """
    Protocol events that should be exposed to users (subset of above).
    """


class ScheduledJob(TeledyneScheduledJob):
    """
    Create ScheduledJob from TeledyneScheduledJob
    """


class InstrumentCmds(TeledyneInstrumentCmds):
    """
    Device specific commands
    Represents the commands the driver implements and the string that
    must be sent to the instrument to execute the command.
    """


class ProtocolState(TeledyneProtocolState):
    """
    Instrument protocol states
    """


class InstrumentDriver(WorkhorseInstrumentDriver):
    """
    Specialization for this version of the workhorse ADCP driver
    """

    def __init__(self, evt_callback):
        """
        InstrumentDriver constructor.
        @param evt_callback Driver process event callback.
        """
        # Construct superclass.
        WorkhorseInstrumentDriver.__init__(self, evt_callback)

    def _build_protocol(self):
        """
        Construct the driver protocol state machine.
        """
        self._protocol = Protocol(Prompt, NEWLINE, self._driver_event)
        log.debug("self._protocol = " + repr(self._protocol))


class ADCPUnits(Units):
    CDEGREE = '1/100 degree'
    DM = Prefixes.DECI + Units.METER
    MPERS = 'm/s'
    PPTHOUSAND = 'ppt'
    ENSEMBLEPERBURST = 'Ensembles Per Burst'
    CMPERSRADIAL = 'cm/s radial'
    TENTHMILLISECOND = '1/10 msec'


class ADCPDescription(BaseEnum):
    INTERVALTIME = 'hh:mm:ss'
    INTERVALTIMEHundredth = 'hh:mm:ss.ss/100'
    DATETIME = 'CCYY/MM/DD,hh:mm:ss'
    PINGTIME = "mm:ss.ss/100"
    SETTIME = 'CCYY/MM/DD,hh:mm:ss'
    SERIALDATAOUT = 'Vel Cor Amp'
    FLOWCONTROL = 'BITS: EnsCyc PngCyc Binry Ser Rec'
    SLEEP = '0 = Disable, 1 = Enable, 2 See Manual'
    XMTPOWER = 'XMT Power 0-255'
    TRUEON = 'False=OFF,True=ON'
    TRUEOFF = "False=ON,True=OFF"


class Protocol(WorkhorseProtocol):
    """
    Specialization for this version of the workhorse driver
    """

    def __init__(self, prompts, newline, driver_event):
        log.debug("IN Protocol.__init__")
        WorkhorseProtocol.__init__(self, prompts, newline, driver_event)
        self.initialize_scheduler()

    def _build_param_dict(self):
        """
        Populate the parameter dictionary with ADCP parameters.
        For each parameter key, add match stirng, match lambda function,
        and value formatting function for set commands.
        """

        self._param_dict.add(Parameter.SERIAL_DATA_OUT,
                             r'CD = (\d\d\d \d\d\d \d\d\d) \-+ Serial Data Out ',
                             lambda match: str(match.group(1)),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Serial Data Out",
                             value_description=ADCPDescription.SERIALDATAOUT,
                             startup_param=True,
                             direct_access=True,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             default_value='000 000 000')

        self._param_dict.add(Parameter.SERIAL_FLOW_CONTROL,
                             r'CF = (\d+) \-+ Flow Ctrl ',
                             lambda match: str(match.group(1)),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Serial Flow Control",
                             value_description=ADCPDescription.FLOWCONTROL,
                             startup_param=True,
                             direct_access=True,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             default_value='11110')

        self._param_dict.add(Parameter.BANNER,
                             r'CH = (\d) \-+ Suppress Banner',
                             lambda match: bool(int(match.group(1))),
                             int,
                             type=ParameterDictType.BOOL,
                             display_name="Banner",
                             value_description=ADCPDescription.TRUEON,
                             startup_param=True,
                             direct_access=True,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             default_value=False)

        self._param_dict.add(Parameter.INSTRUMENT_ID,
                             r'CI = (\d+) \-+ Instrument ID ',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Instrument id",
                             direct_access=True,
                             startup_param=True,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             default_value=0)

        self._param_dict.add(Parameter.SLEEP_ENABLE,
                             r'CL = (\d) \-+ Sleep Enable',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Sleep enable",
                             value_description=ADCPDescription.SLEEP,
                             startup_param=True,
                             direct_access=True,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             default_value=False)

        self._param_dict.add(Parameter.SAVE_NVRAM_TO_RECORDER,
                             r'CN = (\d) \-+ Save NVRAM to recorder',
                             lambda match: bool(int(match.group(1))),
                             int,
                             type=ParameterDictType.BOOL,
                             display_name="Save nvram to recorder",
                             value_description=ADCPDescription.TRUEOFF,
                             startup_param=True,
                             default_value=True,
                             direct_access=True,
                             visibility=ParameterDictVisibility.IMMUTABLE)

        self._param_dict.add(Parameter.POLLED_MODE,
                             r'CP = (\d) \-+ PolledMode ',
                             lambda match: bool(int(match.group(1))),
                             int,
                             type=ParameterDictType.BOOL,
                             display_name="Polled Mode",
                             value_description=ADCPDescription.TRUEON,
                             startup_param=True,
                             direct_access=True,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             default_value=False)

        self._param_dict.add(Parameter.XMIT_POWER,
                             r'CQ = (\d+) \-+ Xmt Power ',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Xmit Power",
                             startup_param=True,
                             value_description=ADCPDescription.XMTPOWER,
                             direct_access=True,
                             default_value=255)

        self._param_dict.add(Parameter.LATENCY_TRIGGER,
                             r'CX = (\d) \-+ Trigger Enable ',
                             lambda match: bool(int(match.group(1))),
                             int,
                             type=ParameterDictType.BOOL,
                             display_name="Latency trigger",
                             value_description=ADCPDescription.TRUEON,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             startup_param=True,
                             direct_access=True,
                             default_value=False)

        self._param_dict.add(Parameter.HEADING_ALIGNMENT,
                             r'EA = ([+-]\d+) \-+ Heading Alignment',
                             lambda match: int(match.group(1)),
                             lambda value: '%+06d' % value,
                             type=ParameterDictType.INT,
                             display_name="Heading alignment",
                             units=ADCPUnits.CDEGREE,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             direct_access=True,
                             startup_param=True,
                             default_value=+00000)

        self._param_dict.add(Parameter.HEADING_BIAS,
                             r'EB = ([+-]\d+) \-+ Heading Bias',
                             lambda match: int(match.group(1)),
                             lambda value: '%+06d' % value,
                             type=ParameterDictType.INT,
                             display_name="Heading Bias",
                             units=ADCPUnits.CDEGREE,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             startup_param=True,
                             direct_access=True,
                             default_value=+00000)

        self._param_dict.add(Parameter.SPEED_OF_SOUND,
                             r'EC = (\d+) \-+ Speed Of Sound',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Speed of Sound",
                             units=ADCPUnits.MPERS,
                             startup_param=True,
                             direct_access=True,
                             default_value=1485)

        self._param_dict.add(Parameter.TRANSDUCER_DEPTH,
                             r'ED = (\d+) \-+ Transducer Depth ',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Transducer Depth",
                             units=ADCPUnits.DM,
                             startup_param=True,
                             direct_access=True,
                             default_value=8000)

        self._param_dict.add(Parameter.PITCH,
                             r'EP = ([\+\-\d]+) \-+ Tilt 1 Sensor ',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Pitch",
                             units=ADCPUnits.CDEGREE,
                             startup_param=True,
                             direct_access=True,
                             default_value=0)

        self._param_dict.add(Parameter.ROLL,
                             r'ER = ([\+\-\d]+) \-+ Tilt 2 Sensor ',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Roll",
                             units=ADCPUnits.CDEGREE,
                             startup_param=True,
                             direct_access=True,
                             default_value=0)

        self._param_dict.add(Parameter.SALINITY,
                             r'ES = (\d+) \-+ Salinity ',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Salinity",
                             units=ADCPUnits.PPTHOUSAND,
                             startup_param=True,
                             direct_access=True,
                             default_value=35)

        self._param_dict.add(Parameter.COORDINATE_TRANSFORMATION,
                             r'EX = (\d+) \-+ Coord Transform ',
                             lambda match: str(match.group(1)),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Coordinate transformation",
                             startup_param=True,
                             direct_access=True,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             default_value='00111')

        self._param_dict.add(Parameter.SENSOR_SOURCE,
                             r'EZ = (\d+) \-+ Sensor Source ',
                             lambda match: str(match.group(1)),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Sensor source",
                             startup_param=True,
                             direct_access=True,
                             default_value='1111101')

        self._param_dict.add(Parameter.DATA_STREAM_SELECTION,
                             r'PD = (\d+) \-+ Data Stream Select',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Data Stream Selection",
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             startup_param=True,
                             direct_access=True,
                             default_value=0)

        self._param_dict.add(Parameter.ENSEMBLE_PER_BURST,
                             r'TC (\d+) \-+ Ensembles Per Burst',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Ensemble per burst",
                             units=ADCPUnits.ENSEMBLEPERBURST,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             startup_param=True,
                             direct_access=True,
                             default_value=0)

        self._param_dict.add(Parameter.TIME_PER_ENSEMBLE,
                             r'TE (\d\d:\d\d:\d\d.\d\d) \-+ Time per Ensemble ',
                             lambda match: str(match.group(1)),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Time per ensemble",
                             value_description=ADCPDescription.INTERVALTIMEHundredth,
                             startup_param=True,
                             direct_access=True,
                             default_value='00:00:00.00')

        self._param_dict.add(Parameter.TIME_OF_FIRST_PING,
                             r'TG (..../../..,..:..:..) - Time of First Ping ',
                             lambda match: str(match.group(1)),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Time of first ping",
                             value_description=ADCPDescription.DATETIME,
                             startup_param=False,
                             direct_access=False,
                             visibility=ParameterDictVisibility.READ_ONLY)

        self._param_dict.add(Parameter.TIME_PER_PING,
                             r'TP (\d\d:\d\d.\d\d) \-+ Time per Ping',
                             lambda match: str(match.group(1)),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Time per ping",
                             value_description=ADCPDescription.PINGTIME,
                             startup_param=True,
                             direct_access=True,
                             default_value='00:01.00')

        self._param_dict.add(Parameter.TIME,
                             r'TT (\d\d\d\d/\d\d/\d\d,\d\d:\d\d:\d\d) \- Time Set ',
                             lambda match: str(match.group(1) + " UTC"),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Time",
                             value_description=ADCPDescription.SETTIME,
                             expiration=86400)  # expire once per day 60 * 60 * 24

        self._param_dict.add(Parameter.BUFFERED_OUTPUT_PERIOD,
                             r'TX (\d\d:\d\d:\d\d) \-+ Buffer Output Period:',
                             lambda match: str(match.group(1)),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Buffered output period",
                             value_description=ADCPDescription.INTERVALTIME,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             startup_param=True,
                             direct_access=True,
                             default_value='00:00:00')

        self._param_dict.add(Parameter.FALSE_TARGET_THRESHOLD,
                             r'WA (\d+,\d+) \-+ False Target Threshold ',
                             lambda match: str(match.group(1)),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="False Target Threshold",
                             startup_param=True,
                             direct_access=True,
                             default_value='050,001')

        self._param_dict.add(Parameter.BANDWIDTH_CONTROL,
                             r'WB (\d) \-+ Bandwidth Control ',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Bandwidth Control",
                             value_description="0=Wid,1=Nar",
                             startup_param=True,
                             direct_access=True,
                             default_value=0)

        self._param_dict.add(Parameter.CORRELATION_THRESHOLD,
                             r'WC (\d+) \-+ Correlation Threshold',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Correlation threshold",
                             startup_param=True,
                             direct_access=True,
                             default_value=64)

        self._param_dict.add(Parameter.SERIAL_OUT_FW_SWITCHES,
                             r'WD ([\d ]+) \-+ Data Out ',
                             lambda match: str(match.group(1)),
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Serial Out fw Switches",
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             startup_param=True,
                             direct_access=True,
                             default_value='111100000')

        self._param_dict.add(Parameter.ERROR_VELOCITY_THRESHOLD,
                             r'WE (\d+) \-+ Error Velocity Threshold',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Error Velocity Threshold",
                             units=ADCPUnits.MPERS,
                             startup_param=True,
                             direct_access=True,
                             default_value=2000)

        self._param_dict.add(Parameter.BLANK_AFTER_TRANSMIT,
                             r'WF (\d+) \-+ Blank After Transmit',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Blank After Transmit",
                             units=ADCPUnits.CENTIMETER,
                             startup_param=True,
                             direct_access=True,
                             default_value=704)

        self._param_dict.add(Parameter.CLIP_DATA_PAST_BOTTOM,
                             r'WI (\d) \-+ Clip Data Past Bottom',
                             lambda match: bool(int(match.group(1))),
                             int,
                             type=ParameterDictType.BOOL,
                             display_name="Clip Data Past Bottom",
                             value_description=ADCPDescription.TRUEON,
                             startup_param=True,
                             direct_access=True,
                             default_value=False)

        self._param_dict.add(Parameter.RECEIVER_GAIN_SELECT,
                             r'WJ (\d) \-+ Rcvr Gain Select \(0=Low,1=High\)',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Receiver Gain Select",
                             value_description="0=Low,1=High",
                             startup_param=True,
                             direct_access=True,
                             default_value=1)

        self._param_dict.add(Parameter.NUMBER_OF_DEPTH_CELLS,
                             r'WN (\d+) \-+ Number of depth cells',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Number of Depth Cells",
                             startup_param=True,
                             direct_access=True,
                             default_value=100)

        self._param_dict.add(Parameter.PINGS_PER_ENSEMBLE,
                             r'WP (\d+) \-+ Pings per Ensemble ',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Pings Per Ensemble",
                             startup_param=True,
                             direct_access=True,
                             default_value=1)

        self._param_dict.add(Parameter.SAMPLE_AMBIENT_SOUND,
                             r'WQ (\d) \-+ Sample Ambient Sound',
                             lambda match: bool(int(match.group(1))),
                             int,
                             type=ParameterDictType.BOOL,
                             display_name="Sample Ambient Sound",
                             value_description=ADCPDescription.TRUEON,
                             visibility=ParameterDictVisibility.IMMUTABLE,
                             startup_param=True,
                             direct_access=True,
                             default_value=False)

        self._param_dict.add(Parameter.DEPTH_CELL_SIZE,
                             r'WS (\d+) \-+ Depth Cell Size \(cm\)',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Depth Cell Size",
                             units=ADCPUnits.CENTIMETER,
                             startup_param=True,
                             direct_access=True,
                             default_value=800)

        self._param_dict.add(Parameter.TRANSMIT_LENGTH,
                             r'WT (\d+) \-+ Transmit Length ',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Transmit Length",
                             units=ADCPUnits.CENTIMETER,
                             startup_param=True,
                             direct_access=True,
                             default_value=0)

        self._param_dict.add(Parameter.PING_WEIGHT,
                             r'WU (\d) \-+ Ping Weighting ',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Ping Weight",
                             value_description="0=Box,1=Triangle",
                             startup_param=True,
                             direct_access=True,
                             default_value=0)

        self._param_dict.add(Parameter.AMBIGUITY_VELOCITY,
                             r'WV (\d+) \-+ Mode 1 Ambiguity Vel ',
                             lambda match: int(match.group(1)),
                             self._int_to_string,
                             type=ParameterDictType.INT,
                             display_name="Ambiguity Velocity",
                             units=ADCPUnits.CMPERSRADIAL,
                             startup_param=True,
                             direct_access=True,
                             default_value=175)

        # Engineering parameters
        self._param_dict.add(Parameter.CLOCK_SYNCH_INTERVAL,
                             r'BOGUS',
                             None,
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Clock synch interval",
                             value_description=ADCPDescription.INTERVALTIME,
                             startup_param=True,
                             direct_access=False,
                             default_value="00:00:00")

        self._param_dict.add(Parameter.GET_STATUS_INTERVAL,
                             r'BOGUS',
                             None,
                             str,
                             type=ParameterDictType.STRING,
                             display_name="Get status interval",
                             value_description=ADCPDescription.INTERVALTIME,
                             startup_param=True,
                             direct_access=False,
                             default_value="00:00:00")

        self._param_dict.set_default(Parameter.CLOCK_SYNCH_INTERVAL)
        self._param_dict.set_default(Parameter.GET_STATUS_INTERVAL)