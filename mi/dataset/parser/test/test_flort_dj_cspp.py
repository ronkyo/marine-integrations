#!/usr/bin/env python

"""
@package mi.dataset.parser.test.test_flort_dj_cspp
@file marine-integrations/mi/dataset/parser/test/test_flort_dj_cspp.py
@author Jeremy Amundson
@brief Test code for a flort_dj_cspp data parser
"""

import os
import numpy
import yaml


from nose.plugins.attrib import attr

from mi.core.log import get_logger
log = get_logger()

from mi.dataset.test.test_parser import ParserUnitTestCase
from mi.dataset.dataset_driver import DataSetDriverConfigKeys
from mi.dataset.driver.flort_dj.cspp.driver import DataTypeKey
from mi.dataset.parser.cspp_base import StateKey, METADATA_PARTICLE_CLASS_KEY, DATA_PARTICLE_CLASS_KEY
from mi.dataset.parser.flort_dj_cspp import FlortDjCsppParser
from mi.dataset.parser.flort_dj_cspp import FlortDjCsppMetadataRecoveredDataParticle, \
    FlortDjCsppInstrumentRecoveredDataParticle, FlortDjCsppMetadataTelemeteredDataParticle, \
    FlortDjCsppInstrumentTelemeteredDataParticle
from mi.core.exceptions import SampleException
from mi.idk.config import Config

RESOURCE_PATH = os.path.join(Config().base_dir(), 'mi', 'dataset', 'driver', 'flort_dj', 'cspp', 'resource')

TEST_RECOVERED = 'first_data_recovered.yml'

@attr('UNIT', group='mi')
class FlortDjCsppParserUnitTestCase(ParserUnitTestCase):
    """
    flort_dj_cspp Parser unit test suite
    """

    def state_callback(self, state, file_ingested):
        """ Call back method to watch what comes in via the position callback """
        self.state_callback_value = state
        self.file_ingested_value = file_ingested

    def pub_callback(self, pub):
        """ Call back method to watch what comes in via the publish callback """
        self.publish_callback_value = pub

    def exception_callback(self, exception):
        """ Callback method to watch what comes in via the exception callback """
        self.exception_callback_value = exception

    def setUp(self):
        ParserUnitTestCase.setUp(self)
        self.config = {
            DataTypeKey.FLORT_DJ_CSPP_RECOVERED: {
                DataSetDriverConfigKeys.PARTICLE_MODULE: 'mi.dataset.parser.flort_dj_cspp.py',
                DataSetDriverConfigKeys.PARTICLE_CLASS: None,
                DataSetDriverConfigKeys.PARTICLE_CLASSES_DICT: {
                    METADATA_PARTICLE_CLASS_KEY: FlortDjCsppMetadataRecoveredDataParticle,
                    DATA_PARTICLE_CLASS_KEY: FlortDjCsppInstrumentRecoveredDataParticle,
                    }
            },
            DataTypeKey.FLORT_DJ_CSPP_TELEMETERED: {
                DataSetDriverConfigKeys.PARTICLE_MODULE: 'mi.dataset.parser.flort_dj_cspp.py',
                DataSetDriverConfigKeys.PARTICLE_CLASS: None,
                DataSetDriverConfigKeys.PARTICLE_CLASSES_DICT: {
                    METADATA_PARTICLE_CLASS_KEY: FlortDjCsppMetadataTelemeteredDataParticle,
                    DATA_PARTICLE_CLASS_KEY: FlortDjCsppInstrumentTelemeteredDataParticle,
                    }
            },
            }
        # Define test data particles and their associated timestamps which will be
        # compared with returned results

        self.file_ingested_value = None
        self.state_callback_value = None
        self.publish_callback_value = None
        self.exception_callback_value = None
        #creates the yaml file, commented out to save time when the file already exists
        #self.create_yml()

    def particle_to_yml(self, particles, filename, mode='w'):
        """
        This is added as a testing helper, not actually as part of the parser tests. Since the same particles
        will be used for the driver test it is helpful to write them to .yml in the same form they need in the
        results.yml fids here.
        """
        # open write append, if you want to start from scratch manually delete this fid
        fid = open(os.path.join(RESOURCE_PATH, filename), mode)

        fid.write('header:\n')
        fid.write("    particle_object: 'MULTIPLE'\n")
        fid.write("    particle_type: 'MULTIPLE'\n")
        fid.write('data:\n')
        for i in range(0, len(particles)):
            particle_dict = particles[i].generate_dict()
            fid.write('  - _index: %d\n' % (i+1))

            fid.write('    particle_object: %s\n' % particles[i].__class__.__name__)
            fid.write('    particle_type: %s\n' % particle_dict.get('stream_name'))
            fid.write('    internal_timestamp: %f\n' % particle_dict.get('internal_timestamp'))

            for val in particle_dict.get('values'):
                if isinstance(val.get('value'), float):
                    fid.write('    %s: %16.16f\n' % (val.get('value_id'), val.get('value')))
                elif isinstance(val.get('value'), str):
                    fid.write("    %s: '%s'\n" % (val.get('value_id'), val.get('value')))
                else:
                    fid.write('    %s: %s\n' % (val.get('value_id'), val.get('value')))
        fid.close()

    def get_dict_from_yml(self, filename):
        """
        This utility routine loads the contents of a yml file
        into a dictionary
        """

        fid = open(os.path.join(RESOURCE_PATH, filename), 'r')
        result = yaml.load(fid)
        fid.close()

        if result is None:
            raise SampleException('dict is None')

        return result

    def create_yml(self):
        """
        This utility creates a yml file
        """

        fid = open(os.path.join(RESOURCE_PATH, 'BAD.txt'), 'r')

        self.stream_handle = fid
        self.parser = FlortDjCsppParser(self.config.get(DataTypeKey.FLORT_DJ_CSPP_RECOVERED), None, self.stream_handle,
                                        self.state_callback, self.pub_callback, self.exception_callback)

        particles = self.parser.get_records(4)

        self.particle_to_yml(particles, 'BAD_telemetered.yml')
        fid.close()

    def test_simple(self):
        """
        retrieves and verifies the first 6 particles
        """
        file_path = os.path.join(RESOURCE_PATH, 'first_data.txt')
        stream_handle = open(file_path, 'r')


        parser = FlortDjCsppParser(self.config.get(DataTypeKey.FLORT_DJ_CSPP_RECOVERED),
                                   None, stream_handle,
                                   self.state_callback, self.pub_callback,
                                   self.exception_callback)

        particles = parser.get_records(6)

        for particle in particles:
            particle.generate_dict()

        test_data = self.get_dict_from_yml(TEST_RECOVERED)
        for n in range(6):
            self.assert_result(test_data['data'][n], particles[n])

        stream_handle.close()

    def test_get_many(self):
        """
        get 10 particles, verify results, get 10 more particles, verify results
        """
        file_path = os.path.join(RESOURCE_PATH, 'first_data.txt')
        stream_handle = open(file_path, 'rb')

        parser = FlortDjCsppParser(self.config.get(DataTypeKey.FLORT_DJ_CSPP_TELEMETERED),
                                   None, stream_handle,
                                   self.state_callback, self.pub_callback,
                                   self.exception_callback)

        particles = parser.get_records(10)

        log.info("Num particles %s", len(particles))

        for particle in particles:
            particle.generate_dict()

        test_data = self.get_dict_from_yml('first_data_telemetered.yml')
        for n in range(10):
            self.assert_result(test_data['data'][n], particles[n])

        particles = parser.get_records(10)

        for particle in particles:
            particle.generate_dict()

        for n in range(10):
            self.assert_result(test_data['data'][n+10], particles[n])

        stream_handle.close()

    def test_long_stream(self):
        """
        retrieve all of particles, verify the expected number, confirm results
        """
        file_path = os.path.join(RESOURCE_PATH, 'first_data.txt')
        stream_handle = open(file_path, 'r')

        parser = FlortDjCsppParser(self.config.get(DataTypeKey.FLORT_DJ_CSPP_RECOVERED),
                                   None, stream_handle,
                                   self.state_callback, self.pub_callback,
                                   self.exception_callback)

        #take in
        particles = parser.get_records(1000)

        self.assertTrue(len(particles) == 193)

        test_data = self.get_dict_from_yml(TEST_RECOVERED)

        for n in range(193):
            self.assert_result(test_data['data'][n], particles[n])

        stream_handle.close()
        
     
    def test_mid_state_start(self):
        """
        This test makes sure that we retrieve the correct particles upon starting with an offset state.
        """

        file_path = os.path.join(RESOURCE_PATH, 'first_data.txt')
        stream_handle = open(file_path, 'rb')

        #the beginning of the 114th data particle, with metatdata read
        initial_state = {StateKey.POSITION: 8173, StateKey.METADATA_EXTRACTED: True}

        parser = FlortDjCsppParser(self.config.get(DataTypeKey.FLORT_DJ_CSPP_RECOVERED),
                                   initial_state, stream_handle,
                                   self.state_callback, self.pub_callback,
                                   self.exception_callback)

        #expect to get the 2nd and 3rd instrument particles next
        particles = parser.get_records(2)

        log.debug("Num particles: %s", len(particles))

        self.assertTrue(len(particles) == 2)

        expected_results = self.get_dict_from_yml(TEST_RECOVERED)

        for i in range(len(particles)):

            self.assert_result(expected_results['data'][i+113], particles[i])

        # now expect the state to be the end of the 114th data records and metadata sent
        the_new_state = {StateKey.POSITION: 8311, StateKey.METADATA_EXTRACTED: True}
        log.debug("********** expected state: %s", the_new_state)
        log.debug("******** new parser state: %s", parser._state)
        self.assertTrue(parser._state == the_new_state)

        stream_handle.close()   

    def test_set_state(self):
        """
        Test changing to a new state after initializing the parser and
        reading data, as if new data has been found and the state has
        changed
        """


        file_path = os.path.join(RESOURCE_PATH, 'first_data.txt')
        stream_handle = open(file_path, 'r')

        expected_results = self.get_dict_from_yml(TEST_RECOVERED)

        parser = FlortDjCsppParser(self.config.get(DataTypeKey.FLORT_DJ_CSPP_RECOVERED),
                None, stream_handle,
                self.state_callback, self.pub_callback,
                self.exception_callback)

        particles = parser.get_records(2)

        log.debug("Num particles: %s", len(particles))

        self.assertTrue(len(particles) == 2)

        for i in range(len(particles)):
            self.assert_result(expected_results['data'][i], particles[i])

        # position 2730 is the byte at the start of the 37th data record
        new_state = {StateKey.POSITION: 2730, StateKey.METADATA_EXTRACTED: True}

        parser.set_state(new_state)

        particles = parser.get_records(2)

        self.assertTrue(len(particles) == 2)

        for i in range(len(particles)):
            self.assert_result(expected_results['data'][i + 36], particles[i])

    def test_bad_data(self):
        """
        Ensure that bad data is skipped when it exists. A variety of malformed
        records are used in order to verify this
        """

        file_path = os.path.join(RESOURCE_PATH, 'BAD.txt')
        stream_handle = open(file_path, 'rb')

        log.info(self.exception_callback_value)

        parser = FlortDjCsppParser(self.config.get(DataTypeKey.FLORT_DJ_CSPP_RECOVERED),
                                   None, stream_handle,
                                   self.state_callback, self.pub_callback,
                                   self.exception_callback)

        particles = parser.get_records(2)

        expected_results = self.get_dict_from_yml('BAD_recovered.yml')

        self.assertTrue(len(particles) == 2)

        for i in range(len(particles)):
            self.assert_result(expected_results['data'][i], particles[i])

        stream_handle.close()

    def assert_result(self, test, particle):
        """
        Suite of tests to run against each returned particle and expected
        results of the same.  The test parameter should be a dictionary
        that contains the keys to be tested in the particle
        the 'internal_timestamp' and 'position' keys are
        treated differently than others but can be verified if supplied
        """

        particle_dict = particle.generate_dict()

        #for efficiency turn the particle values list of dictionaries into a dictionary
        particle_values = {}
        for param in particle_dict.get('values'):
            particle_values[param['value_id']] = param['value']

        # compare each key in the test to the data in the particle
        for key in test:
            test_data = test[key]

            #get the correct data to compare to the test
            if key == 'internal_timestamp':
                particle_data = particle.get_value('internal_timestamp')
                #the timestamp is in the header part of the particle
            elif key == 'position':
                particle_data = self.state_callback_value['position']
                #position corresponds to the position in the file
            else:
                particle_data = particle_values.get(key)
                #others are all part of the parsed values part of the particle

            # log.debug('*** assert result: test data key = %s', key)
            # log.debug('*** assert result: test data val = %s', test_data)
            # log.debug('*** assert result: part data val = %s', particle_data)

            if particle_data is None:
                #generally OK to ignore index keys in the test data, verify others

                log.warning("\nWarning: assert_result ignoring test key %s, does not exist in particle", key)
            else:
                if isinstance(test_data, float):

                    # slightly different test for these values as they are floats.
                    compare = numpy.abs(test_data - particle_data) <= 1e-5
                    # log.debug('*** assert result: compare = %s', compare)
                    self.assertTrue(compare)
                else:
                    # otherwise they are all ints and should be exactly equal
                    self.assertEqual(test_data, particle_data)