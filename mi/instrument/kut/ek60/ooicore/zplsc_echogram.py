"""
@package mi.instrument.kut.ek60.ooicore.driver
@file marine-integrations/mi/instrument/kut/ek60/ooicore/driver.py
@author Craig Risien
@brief ZPLSC Echogram generation for the ooicore

Release notes:

This Class supports the generation of ZPLSC echograms. It needs matplotlib version 1.3.1 for the code to display the
colorbar at the bottom of the figure. If matplotlib version 1.1.1 is used, the colorbar would be plotted over the
 figure instead of at the bottom of i.
"""

__author__ = 'Craig Risien from OSU'
__license__ = 'Apache 2.0'

from collections import defaultdict
from modest_image import ModestImage, imshow

# Need to install matplotlib version 1.3.1 for the colorbar to work correctly
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


import re
import numpy as np
import pprint as pp

from struct import unpack


from mi.core.log import get_logger
from mi.core.log import get_logging_metaclass

log = get_logger()

LENGTH_SIZE = 4
DATAGRAM_HEADER_SIZE = 12
CONFIG_HEADER_SIZE = 516
CONFIG_TRANSDUCER_SIZE = 320
TRANSDUCER_1 = 'Transducer # 1: '
TRANSDUCER_2 = 'Transducer # 2: '
TRANSDUCER_3 = 'Transducer # 3: '


# set global regex expressions to find all sample, annotation and NMEA sentences
SAMPLE_REGEX = r'RAW\d{1}'
SAMPLE_MATCHER = re.compile(SAMPLE_REGEX, re.DOTALL)

ANNOTATE_REGEX = r'TAG\d{1}'
ANNOTATE_MATCHER = re.compile(ANNOTATE_REGEX, re.DOTALL)

NMEA_REGEX = r'NME\d{1}'
NMEA_MATCHER = re.compile(NMEA_REGEX, re.DOTALL)


###########################################################################
# ZPLSCEchogram
###########################################################################

class ZPLSCEchogram():
    """
    ZPLSC Echograms generation class
    """

    __metaclass__ = get_logging_metaclass(log_level='debug')

    def __init__(self, filepath, raw_file):
        """
        ZPLSCEchogram constructor
        @param filepath directory path where generated echograms are stored
        @param raw_file ZPLSC raw binary file whose data is used to generate echograms
        """
        self.filepath = filepath
        self.raw_file = raw_file
        if not self.raw_file.endswith('.raw'):
            log.debug("ZPLSC raw file does not end with dot raw ")

        # tuple contains the string before the '.', the '.' and the 'raw' string
        tuple = self.raw_file.rpartition('.')
        self.outfile = tuple[0]


    ####################################################################################
    # Create functions to read the datagrams contained in the raw file. The
    # code below was developed using example Matlab code produced by Lars Nonboe
    # Andersen of Simrad and provided to us by Dr. Kelly Benoit-Bird and the
    # raw data file format specification in the Simrad EK60 manual, with reference
    # to code in Rick Towler's readEKraw toolbox.

    def _read_datagram_header(self, chunk):
        """
        Reads the EK60 raw data file datagram header
        @param chunk data chunk to read the datagram header from
        @return: datagram header
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

    def _read_config_header(self, chunk):
        """
        Reads the EK60 raw data file configuration header information
        from the byte string passed in as a chunk
        @param chunk data chunk to read the config header from
        @return: configuration header
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

    def _read_config_transducer(self, chunk):
        """
        Reads the EK60 raw data file configuration transducer information
        from the byte string passed in as a chunk
        @param chunk data chunk to read the configuration transducer information from
        @return: configuration transducer information
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

    def _read_text_data(self, chunk, string_length):
        """
        Reads either the NMEA or annotation text strings from the EK60 raw data
        file from the byte string passed in as a chunk
        @param chunk data chunk to read the text data from
        @param string_length length of string
        @return: text data
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

    def _read_sample_data(self, chunk):
        """
        Reads the EK60 raw sample datagram from the byte string passed in as a chunk
        @param chunk data chunk to read sample data from
        @return: sample datagram dictionary
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

    def _generate_plots(self, trans_array, trans_array_time, ref_time, td_f, td_dR, title, filename):
        """
        Generate plots for an transducer
        @param trans_array Transducer data array
        @param trans_array_time Transducer internal time array
        @param ref_time reference time "seconds since 1970-01-01 00:00:00"
        @param td_f Transducer frequency
        @param td_dR Transducer's sample thickness (in range)
        @param title Transducer title
        @param filename png file name to save the figure to
        """
        #subset/decimate the x & y ticks so that we don't plot everyone
        deci_x = 200
        deci_y = 1000

        #Only generate plots for the transducers that have data
        if np.size(trans_array_time) > 0:

            # determine size of the data array
            pSize = np.shape(trans_array)
            # create range vector (in meters)
            td_depth = np.arange(0, pSize[0]) * td_dR

            # convert time, which represents the number of 100-nanosecond intervals that
            # have elapsed since 12:00 A.M. January 1, 1601 Coordinated Universal Time (UTC)
            # to unix time, i.e. seconds since 1970-01-01 00:00:00.
            # 11644473600 == difference between 1601 and 1970
            # 1e7 == divide by 10 million to convert to seconds
            trans_array_time = np.array(trans_array_time) / 1e7 - 11644473600
            trans_array_time = trans_array_time / 60 / 60 / 24
            trans_array_time = trans_array_time + ref_time
            trans_array_time = np.squeeze(trans_array_time)

            min_depth = 0
            max_depth = pSize[0]

            min_time = 0
            max_time = np.size(trans_array_time)

            min_db = -180
            max_db = -59

            cbar_ticks = np.arange(min_db, max_db)
            cbar_ticks = cbar_ticks[::20]

            # rotates and right aligns the x labels, and moves the bottom of the
            # axes up to make room for them
            ax = plt.gca()
            cax = imshow(ax, trans_array, interpolation='none', aspect='auto', cmap='jet', vmin=min_db, vmax=max_db)
            plt.grid(False)
            figure_title = 'Converted Power: ' + title + 'Frequency: ' + str(td_f)
            plt.title(figure_title, fontsize=12)
            plt.xlabel('time (UTC)', fontsize=10)
            plt.ylabel('depth (m)', fontsize=10)

            #format trans_array_time array so that it can be used to label the x-axis
            xticks = mdates.num2date(trans_array_time[0::200])
            xticks_fmted = []
            for i in range(0, len(xticks)):
                a = xticks[i].strftime('%Y-%m-%d %H:%M:%S')
                xticks_fmted.append([a])

            x = np.arange(0, pSize[1])
            #subset the xticks so that we don't plot everyone
            x = x[::deci_x]
            y = np.arange(0, pSize[0])
            #subset the yticks so that we don't plot everyone
            y = y[::deci_y]
            yticks = np.round(td_depth[::deci_y], decimals=0)
            plt.xticks(x, xticks_fmted, rotation=25, horizontalalignment='right', fontsize=10)
            plt.yticks(y, yticks, fontsize=10)
            plt.tick_params(axis="y", labelcolor="k", pad=4)
            plt.tick_params(axis="x", labelcolor="k", pad=4)

            #set the x and y limits
            plt.ylim(max_depth, min_depth)
            plt.xlim(min_time, max_time)

            #plot the colorbar
            cb = plt.colorbar(cax, orientation='horizontal', ticks=cbar_ticks, shrink=.6)
            cb.ax.set_xticklabels(cbar_ticks, fontsize=8)  # horizontally oriented colorbar
            cb.set_label('dB', fontsize=10)
            cb.ax.set_xlim(-180, -60)

            plt.tight_layout()
            #adjust the subplot so that the x-tick labels will fit on the canvas
            plt.subplots_adjust(bottom=0.1)

            #reposition the cbar
            cb.ax.set_position([.4, .05, .4, .1])

            #save the figure
            plt.savefig(filename, dpi=300)

            #close the figure
            plt.close()

    def generate_echograms(self):
        """
        Reads the EK60 raw sample datagram and generate echograms
        """

        # read in the binary data file and store as an object for further processing
        #with open('ion_functions/data/matlab_scripts/zplsc/data/Baja_2013-D20131020-T030020.raw', 'rb') as f:
        # with open('ion_functions/data/matlab_scripts/zplsc/data/OOI_BT-D20140619-T000000.raw', 'rb') as f:
        with open(self.raw_file, 'rb') as f:
            raw = f.read()

        # set starting byte count
        byte_cnt = 0

        # read the configuration datagram, output at the beginning of the file
        length1 = unpack('<l', raw[byte_cnt:byte_cnt+4])
        byte_cnt += LENGTH_SIZE
        #byte_cnt += 4

        # configuration datagram header
        datagram_header = self._read_datagram_header(raw[byte_cnt:byte_cnt+12])
        byte_cnt += DATAGRAM_HEADER_SIZE
        #byte_cnt += 12

        # configuration: header
        config_header = self._read_config_header(raw[byte_cnt:byte_cnt+516])
        byte_cnt += CONFIG_HEADER_SIZE
        #byte_cnt += 516

        # configuration: transducers (1 to 7 max)
        config_transducer = defaultdict(dict)
        for i in range(config_header['transducer_count']):
            config_transducer['transducer'][i] = self._read_config_transducer(raw[byte_cnt:byte_cnt+320])
            byte_cnt += CONFIG_TRANSDUCER_SIZE
            #byte_cnt += 320

        length2 = unpack('<l', raw[byte_cnt:byte_cnt+4])
        if not (length1[0] == length2[0] == byte_cnt+4-8):
            raise ValueError("length of datagram and bytes read do not match")

        #pp.pprint(datagram_header.items())
        #pp.pprint(config_header.items())
        #pp.pprint(config_transducer.items())

        #create 3, which is the max # of transducers EA will have, sets of empty lists
        trans_array_1 = []
        trans_array_1_time = []
        trans_array_2 = []
        trans_array_2_time = []
        trans_array_3 = []
        trans_array_3_time = []

        # index through the sample datagrams, collecting the data needed to create the echograms
        count = 0
        for i in re.finditer(SAMPLE_REGEX, raw):
            # set the starting byte
            strt = i.start() - 4

            # extract the length of the datagram
            length1 = unpack('<l', raw[strt:strt+4])
            strt += 4

            # parse the sample datagram header
            sample_datagram_header = self._read_datagram_header(raw[strt:strt+12])
            strt += 12

            # parse the sample datagram contents
            sample_datagram = self._read_sample_data(raw[strt:strt+length1[0]])

            #if count == 0:
            #    pp.pprint(sample_datagram_header.items())
            #    pp.pprint(sample_datagram.items())

            # populate the various lists with data from each of the transducers
            if sample_datagram['channel_number'] == 1:
                trans_array_1.append([sample_datagram['power']])
                trans_array_1_time.append([sample_datagram_header['internal_time']])
                if count <= 2:
                    # extract various calibration parameters
                    td_1_f = sample_datagram['frequency']
                    td_1_c = sample_datagram['sound_velocity']
                    td_1_t = sample_datagram['sample_interval']
                    td_1_alpha = sample_datagram['absorbtion_coefficient']
                    td_1_depth = sample_datagram['transducer_depth']
                    td_1_transmitpower = sample_datagram['transmit_power']
                    # calculate sample thickness (in range)
                    td_1_dR = td_1_c * td_1_t / 2
                    #Example data that one might need for various calculations later on
                    #td_1_gain = config_transducer['transducer'][0]['gain']
                    #td_1_gain_table = config_transducer['transducer'][0]['gain_table']
                    #td_1_pulse_length_table = config_transducer['transducer'][0]['pulse_length_table']
                    #td_1_phi_equiv_beam_angle = config_transducer['transducer'][0]['equiv_beam_angle']
            elif sample_datagram['channel_number'] == 2:
                trans_array_2.append([sample_datagram['power']])
                trans_array_2_time.append([sample_datagram_header['internal_time']])
                if count <= 2:
                    # extract various calibration parameters
                    td_2_f = sample_datagram['frequency']
                    td_2_c = sample_datagram['sound_velocity']
                    td_2_t = sample_datagram['sample_interval']
                    td_2_alpha = sample_datagram['absorbtion_coefficient']
                    td_2_depth = sample_datagram['transducer_depth']
                    td_2_transmitpower = sample_datagram['transmit_power']
                    # calculate sample thickness (in range)
                    td_2_dR = td_2_c * td_2_t / 2
                    #Example data that one might need for various calculations later on
                    #td_2_gain = config_transducer['transducer'][1]['gain']
                    #td_2_gain_table = config_transducer['transducer'][1]['gain_table']
                    #td_2_pulse_length_table = config_transducer['transducer'][1]['pulse_length_table']
                    #td_2_phi_equiv_beam_angle = config_transducer['transducer'][1]['equiv_beam_angle']
            elif sample_datagram['channel_number'] == 3:
                trans_array_3.append([sample_datagram['power']])
                trans_array_3_time.append([sample_datagram_header['internal_time']])
                if count <= 2:
                    # extract various calibration parameters
                    td_3_f = sample_datagram['frequency']
                    td_3_c = sample_datagram['sound_velocity']
                    td_3_t = sample_datagram['sample_interval']
                    td_3_alpha = sample_datagram['absorbtion_coefficient']
                    td_3_depth = sample_datagram['transducer_depth']
                    td_3_transmitpower = sample_datagram['transmit_power']
                    # calculate sample thickness (in range)
                    td_3_dR = td_3_c * td_3_t / 2
                    #Example data that one might need for various calculations later on
                    #td_3_gain = config_transducer['transducer'][2]['gain']
                    #td_3_gain_table = config_transducer['transducer'][2]['gain_table']
                    #td_3_pulse_length_table = config_transducer['transducer'][2]['pulse_length_table']
                    #td_3_phi_equiv_beam_angle = config_transducer['transducer'][2]['equiv_beam_angle']

        #Convert lists to np arrays and rotate them
        trans_array_1 = np.flipud(np.rot90(np.atleast_2d(np.squeeze(trans_array_1))))
        trans_array_2 = np.flipud(np.rot90(np.atleast_2d(np.squeeze(trans_array_2))))
        trans_array_3 = np.flipud(np.rot90(np.atleast_2d(np.squeeze(trans_array_3))))

        # reference time "seconds since 1970-01-01 00:00:00"
        ref_time = datetime(1970, 1, 1, 0, 0, 0)
        ref_time = mdates.date2num(ref_time)

        filename = self.filepath + self.outfile
        if np.size(trans_array_1_time) > 0:
            self._generate_plots(trans_array_1, trans_array_1_time, ref_time, td_1_f, td_1_dR, TRANSDUCER_1, filename + '_38k.png')

        if np.size(trans_array_2_time) > 0:
            self._generate_plots(trans_array_2, trans_array_2_time, ref_time, td_2_f, td_2_dR, TRANSDUCER_2, filename + '_120k.png')

        if np.size(trans_array_3_time) > 0:
            self._generate_plots(trans_array_3, trans_array_3_time, ref_time, td_3_f, td_3_dR, TRANSDUCER_3, filename + '_200k.png')