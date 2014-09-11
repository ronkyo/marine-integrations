#!/usr/bin/env python

"""
@package mi.dataset.parser.wc_sbe_cspp
@file marine-integrations/mi/dataset/parser/wc_sbe_cspp.py
@author Jeff Roy
@brief wc_sbe Parser for the cspp_eng_cspp dataset driver
Release notes: This is one of 4 parsers that make up that driver

initial release
"""

__author__ = 'Jeff Roy'
__license__ = 'Apache 2.0'

import numpy

from mi.core.log import get_logger
log = get_logger()

from mi.core.common import BaseEnum
from mi.core.exceptions import RecoverableSampleException
from mi.core.instrument.data_particle import DataParticle

from mi.dataset.parser.cspp_base import \
    CsppParser, \
    FLOAT_REGEX, \
    Y_OR_N_REGEX, \
    MULTIPLE_TAB_REGEX, \
    END_OF_LINE_REGEX, \
    CsppMetadataDataParticle, \
    MetadataRawDataKey, \
    encode_y_or_n

# Input Records are formatted as follows
# FORMAT    DATA Type       Field               Units       Notes
#
# string 	float64 	Profiler Timestamp 	    seconds 	Seconds since 1/1/70 with millisecond resolution
# string 	string 	    Suspect Timestamp 	    1 	        "y" or "n"
# string 	float32 	Pressure 	            decibars
# string 	float32 	Velocity 	            m/s

DATA_REGEX = '(' + FLOAT_REGEX + ')' + MULTIPLE_TAB_REGEX  # Profiler Timestamp
DATA_REGEX += '(' + Y_OR_N_REGEX + ')' + MULTIPLE_TAB_REGEX  # Suspect Timestamp
DATA_REGEX += '(' + FLOAT_REGEX + ')' + MULTIPLE_TAB_REGEX  # Pressure
DATA_REGEX += '(' + FLOAT_REGEX + ')' + END_OF_LINE_REGEX  # Velocity


class WcSbeDataTypeKey(BaseEnum):
    WC_SBE_CSPP_TELEMETERED = 'wc_sbe_cspp_telemetered'
    WC_SBE_CSPP_RECOVERED = 'wc_sbe_cspp_recovered'


class DataMatchesGroupNumber(BaseEnum):
    """
    An enum for group match indices for a data record chunk.
    Used to access the match groups in the particle raw data
    """
    PROFILER_TIMESTAMP = 1
    SUSPECT_TIMESTAMP = 2
    PRESSURE = 3
    VELOCITY = 4


class WcSbeDataParticleType(BaseEnum):
    ENGINEERING_TELEMETERED = 'cspp_eng_cspp_wc_sbe_eng'
    ENGINEERING_RECOVERED = 'cspp_eng_cspp_wc_sbe_eng_recovered'
    METADATA_TELEMETERED = 'cspp_eng_cspp_wc_sbe_metadata'
    METADATA_RECOVERED = 'cspp_eng_cspp_wc_sbe_metadata_recovered'


class WcSbeEngDataParticleKey(BaseEnum):
    """
    The data particle keys associated with wc_sbe engineering data particle parameters
    """
    PROFILER_TIMESTAMP = 'profiler_timestamp'
    PRESSURE = 'pressure_depth'
    SUSPECT_TIMESTAMP = 'suspect_timestamp'
    VELOCITY = 'velocity_flt32'

# A group of instrument data particle encoding rules used to simplify encoding using a loop
ENGINEERING_PARTICLE_ENCODING_RULES = [
    (WcSbeEngDataParticleKey.PROFILER_TIMESTAMP, DataMatchesGroupNumber.PROFILER_TIMESTAMP, numpy.float),
    (WcSbeEngDataParticleKey.PRESSURE, DataMatchesGroupNumber.PRESSURE, float),
    (WcSbeEngDataParticleKey.SUSPECT_TIMESTAMP, DataMatchesGroupNumber.SUSPECT_TIMESTAMP, encode_y_or_n),
    (WcSbeEngDataParticleKey.VELOCITY, DataMatchesGroupNumber.VELOCITY, float),
]


class WcSbeMetadataDataParticle(CsppMetadataDataParticle):
    """
    Class for building a wc sbe metadata particle
    """

    def _build_parsed_values(self):
        """
        Take something in the data format and turn it into
        an array of dictionaries defining the data in the particle
        with the appropriate tag.
        @throws RecoverableSampleException If there is a problem with sample creation
        """

        results = []

        try:

            # Append the base metadata parsed values to the results to return
            results += self._build_metadata_parsed_values()

            data_match = self.raw_data[MetadataRawDataKey.DATA_MATCH]

            # Set the internal timestamp
            internal_timestamp_unix = numpy.float(data_match.group(
                DataMatchesGroupNumber.PROFILER_TIMESTAMP))
            self.set_internal_timestamp(unix_time=internal_timestamp_unix)

        except (ValueError, TypeError, IndexError) as ex:
            log.warn("Exception when building parsed values")
            raise RecoverableSampleException("Error (%s) while decoding parameters in data: [%s]"
                                             % (ex, self.raw_data))

        return results


class WcSbeMetadataRecoveredDataParticle(WcSbeMetadataDataParticle):
    """
    Class for building a wc sbe recovered metadata particle
    """

    _data_particle_type = WcSbeDataParticleType.METADATA_RECOVERED


class WcSbeMetadataTelemeteredDataParticle(WcSbeMetadataDataParticle):
    """
    Class for building a wc sbe telemetered metadata particle
    """

    _data_particle_type = WcSbeDataParticleType.METADATA_TELEMETERED


class WcSbeEngDataParticle(DataParticle):
    """
    Class for parsing data from the wc sbe engineering data set
    """

    def _build_parsed_values(self):
        """
        Take something in the data format and turn it into
        an array of dictionaries defining the data in the particle
        with the appropriate tag.
        @throws RecoverableSampleException If there is a problem with sample creation
        """
        results = []

        try:

            # Process each of the instrument particle parameters
            for name, group, function in ENGINEERING_PARTICLE_ENCODING_RULES:
                results.append(self._encode_value(name, self.raw_data.group(group), function))

            # # Set the internal timestamp
            internal_timestamp_unix = numpy.float(self.raw_data.group(
                DataMatchesGroupNumber.PROFILER_TIMESTAMP))
            self.set_internal_timestamp(unix_time=internal_timestamp_unix)

        # We shouldn't end up with an exception due to the strongly specified regex, but we
        # will ensure we catch any potential errors just in case
        except (ValueError, TypeError, IndexError) as ex:
            log.warn("Exception when building parsed values")
            raise RecoverableSampleException("Error (%s) while decoding parameters in data: [%s]"
                                             % (ex, self.raw_data))

        return results


class WcSbeEngRecoveredDataParticle(WcSbeEngDataParticle):
    """
    Class for building a wc sbe recovered engineering data particle
    """

    _data_particle_type = WcSbeDataParticleType.ENGINEERING_RECOVERED


class WcSbeEngTelemeteredDataParticle(WcSbeEngDataParticle):
    """
    Class for building a wc sbe telemetered engineering data particle
    """

    _data_particle_type = WcSbeDataParticleType.ENGINEERING_TELEMETERED


class WcSbeCsppParser(CsppParser):

    def __init__(self,
                 config,
                 state,
                 stream_handle,
                 state_callback,
                 publish_callback,
                 exception_callback,
                 *args, **kwargs):
        """
        This method is a constructor that will instantiate an WcSbeCsppParser object.
        @param config The configuration for this WcSbeCsppParser parser
        @param state The state the WcSbeCsppParser should use to initialize itself
        @param stream_handle The handle to the data stream containing the cspp_eng_cspp data
        @param state_callback The function to call upon detecting state changes
        @param publish_callback The function to call to provide particles
        @param exception_callback The function to call to report exceptions
        """

        # Call the superclass constructor
        super(WcSbeCsppParser, self).__init__(config,
                                              state,
                                              stream_handle,
                                              state_callback,
                                              publish_callback,
                                              exception_callback,
                                              DATA_REGEX,
                                              ignore_matcher=None,
                                              *args, **kwargs)
