"""
@package mi.dataset.driver.sio_eng.sio_mule.driver
@file marine-integrations/mi/dataset/driver/sio_eng/sio_mule/driver.py
@author Mike Nicoletti
@brief Driver for the sio_eng_sio_mule
Release notes:

Starting SIO Engineering Driver
"""

__author__ = 'Mike Nicoletti'
__license__ = 'Apache 2.0'

from mi.core.common import BaseEnum
from mi.core.exceptions import ConfigurationException
from mi.core.log import get_logger
log = get_logger()

from mi.dataset.harvester import \
    SingleFileHarvester, \
    SingleDirectoryHarvester

from mi.dataset.dataset_driver import \
    HarvesterType, \
    DataSetDriverConfigKeys

from mi.dataset.driver.sio_mule.sio_mule_driver import SioMuleDataSetDriver

from mi.dataset.parser.sio_eng_sio_mule import \
    SioEngSioMuleParser, \
    SioEngSioRecoveredParser, \
    SioEngSioMuleDataParticle, \
    SioEngSioRecoveredDataParticle


class DataSourceKey(BaseEnum):
    """
    These are the possible harvester/parser pairs for this driver
    """
    SIO_ENG_SIO_MULE_TELEMETERED = 'sio_eng_sio_telemetered'
    SIO_ENG_SIO_MULE_RECOVERED = 'sio_eng_sio_recovered'


class SioEngSioMuleDataSetDriver(SioMuleDataSetDriver):

    @classmethod
    def stream_config(cls):
        return [SioEngSioMuleDataParticle.type(),
                SioEngSioRecoveredDataParticle.type()]

    def __init__(self,
                 config,
                 memento,
                 data_callback,
                 state_callback,
                 event_callback,
                 exception_callback):

        # link the data keys to the harvester type, multiple or single file harvester
        harvester_type = {DataSourceKey.SIO_ENG_SIO_MULE_TELEMETERED: HarvesterType.SINGLE_FILE,
                          DataSourceKey.SIO_ENG_SIO_MULE_RECOVERED: HarvesterType.SINGLE_DIRECTORY}

        super(SioEngSioMuleDataSetDriver, self).__init__(config,
                                                         memento,
                                                         data_callback,
                                                         state_callback,
                                                         event_callback,
                                                         exception_callback,
                                                         DataSourceKey.list(),
                                                         harvester_type=harvester_type)

    def _build_parser(self, parser_state, stream_in, data_key):
        """
        Build the telemetered or the recovered parser according to
        which data source is appropriate
        """
        parser = None

        if data_key == DataSourceKey.SIO_ENG_SIO_MULE_TELEMETERED:
            parser = self._build_telemetered_parser(parser_state, stream_in)
            log.debug("_build_parser::::  BUILT TELEMETERED PARSER, %s", type(parser))

        elif data_key == DataSourceKey.SIO_ENG_SIO_MULE_RECOVERED:
            parser = self._build_recovered_parser(parser_state, stream_in)
            log.debug("_build_parser::::  BUILDING RECOVERED PARSER, %s", type(parser))
        else:
            raise ConfigurationException("Bad data key: %s" % data_key)

        return parser

    def _build_telemetered_parser(self, parser_state, stream_in):
        """
        Build and return the telemetered parser
        @param parser_state starting parser state to pass to parser
        @param stream_in Handle of open file to pass to parser
        """

        config = self._parser_config[DataSourceKey.SIO_ENG_SIO_MULE_TELEMETERED]
        config.update({
            DataSetDriverConfigKeys.PARTICLE_MODULE: 'mi.dataset.parser.sio_eng_sio_mule',
            DataSetDriverConfigKeys.PARTICLE_CLASS: 'SioEngSioMuleDataParticle'
        })
        log.debug("My Config in _build_telemetered_parser: %s", config)

        parser = SioEngSioMuleParser(
            config,
            parser_state,
            stream_in,
            lambda state: self._save_parser_state(state, DataSourceKey.SIO_ENG_SIO_MULE_TELEMETERED),
            self._data_callback,
            self._sample_exception_callback
        )

        return parser

    def _build_recovered_parser(self, parser_state, stream_in):
        """
        Build and return the recovered parser
        @param parser_state starting parser state to pass to parser
        @param stream_in Handle of open file to pass to parser
        """
        config = self._parser_config[DataSourceKey.SIO_ENG_SIO_MULE_RECOVERED]
        config.update({
            DataSetDriverConfigKeys.PARTICLE_MODULE: 'mi.dataset.parser.sio_eng_sio_mule',
            DataSetDriverConfigKeys.PARTICLE_CLASS: 'SioEngSioRecoveredDataParticle'
        })
        log.debug("My Config: %s", config)

        parser = SioEngSioRecoveredParser(
            config,
            parser_state,
            stream_in,
            lambda state, ingested: self._save_parser_state(state, DataSourceKey.SIO_ENG_SIO_MULE_RECOVERED, ingested),
            self._data_callback,
            self._sample_exception_callback
        )
        return parser

    def _build_harvester(self, driver_state):
        """
        Build and return the harvesters
        """
        harvesters = []
        if DataSourceKey.SIO_ENG_SIO_MULE_TELEMETERED in self._harvester_config:

            telemetered_harvester = SingleFileHarvester(
                self._harvester_config.get(DataSourceKey.SIO_ENG_SIO_MULE_TELEMETERED),
                driver_state[DataSourceKey.SIO_ENG_SIO_MULE_TELEMETERED],
                lambda file_state: self._file_changed_callback(file_state,
                                                               DataSourceKey.SIO_ENG_SIO_MULE_TELEMETERED),
                self._exception_callback
            )

            harvesters.append(telemetered_harvester)
        else:
            log.warn('No configuration for telemetered harvester, not building')

        if DataSourceKey.SIO_ENG_SIO_MULE_RECOVERED in self._harvester_config:
            recov_harvester = SingleDirectoryHarvester(
                self._harvester_config.get(DataSourceKey.SIO_ENG_SIO_MULE_RECOVERED),
                driver_state[DataSourceKey.SIO_ENG_SIO_MULE_RECOVERED],
                lambda filename: self._new_file_callback(filename, DataSourceKey.SIO_ENG_SIO_MULE_RECOVERED),
                lambda modified: self._modified_file_callback(modified, DataSourceKey.SIO_ENG_SIO_MULE_RECOVERED),
                self._exception_callback
            )
            harvesters.append(recov_harvester)
        else:
            log.warn('No configuration for %s harvester, not building', DataSourceKey.SIO_ENG_SIO_MULE_RECOVERED)

        return harvesters
