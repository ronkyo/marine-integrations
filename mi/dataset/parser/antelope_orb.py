#!/usr/bin/env python

"""
@package mi.dataset.parser.antelope_orb
@file marine-integrations/mi/dataset/parser/antelope_orb.py
@author Jeff Laughlin <jeff@jefflaughlinconsulting.com>
@brief Parser for the antelope_orb dataset driver
Release notes:

Initial Release
"""

__author__ = 'Jeff Laughlin <jeff@jefflaughlinconsulting.com>'
__license__ = 'Apache 2.0'


import numpy as np

from mi.core.log import get_logger
log = get_logger()
#import logging
#log.setLevel(logging.TRACE)

from mi.core.common import BaseEnum
from mi.core.instrument.data_particle import DataParticle, DataParticleKey
from mi.core.exceptions import SampleException

from mi.dataset.dataset_parser import Parser

from mi.core.kudu.brttpkt import OrbReapThr, Timeout, NoData
from mi.core.kudu import _pkt


# from RSN Sensor Lineup_Summer V2014_06_12-dm_3.xls via Kirk.Decker@jhuapl.edu
SUFFIXES = [s.lower() for s in ['BHE', 'BHN', 'BHZ', 'EHE', 'EHN', 'EHZ', 'HDH', 'HHE',
        'HHN', 'HHZ', 'HNE', 'HNN', 'HNZ', 'LDH', 'LHE', 'LHN', 'LHZ',
        'MHE', 'MHN', 'MHZ', 'XDH', 'YDH',
        'chan' # used for testing
        ]]


class ParserConfigKey(BaseEnum):
    ORBNAME = "orbname"
    SELECT  = "select"
    REJECT  = "reject"


class StateKey(BaseEnum):
    TAFTER = 'tafter' # timestamp of last orb pkt read
    SELECT  = "select"
    REJECT  = "reject"


class DataParticleType(BaseEnum):
    ANTELOPE_ORB_PACKET = 'antelope_orb_packet'


class AntelopeOrbPacketParticleKey(BaseEnum):
    ID = 'id'
    CHANNELS = 'channels'
    DB = 'db'
    DFILE = 'dfile'
    PF = 'pf'
    SRCNAME = 'srcname'
    STRING = 'string'
    TIME = 'packet_time'
    TYPE = 'type'
    VERSION = 'version'


# Packet channel fields
class AntelopeOrbPacketParticleChannelKey(BaseEnum):
    CALIB = 'calib'
    CALPER = 'calper'
    CHAN = 'chan'
    CUSER1 = 'cuser1'
    CUSER2 = 'cuser2'
    DATA = 'data'
    DUSER1 = 'duser1'
    DUSER2 = 'duser2'
    IUSER1 = 'iuser1'
    IUSER2 = 'iuser2'
    IUSER3 = 'iuser3'
    LOC = 'loc'
    NET = 'net'
    SAMPRATE = 'samprate'
    SEGTYPE = 'segtype'
    STA = 'sta'
    TIME = 'channel_time'


class AntelopeOrbPacketParticle(DataParticle):
    """
    Class for parsing data from the antelope_orb data set
    """

    _pkt = None

    def __init__(self, raw_data, *args, **kwargs):
        pktid, srcname, orbtimestamp, raw_packet, pkttype, pkt = raw_data
        self._pkt = pkt
        log.trace("new particle w pkt: %s", pkt)
        super(AntelopeOrbPacketParticle, self).__init__(raw_data, *args, **kwargs)

    def __del__(self):
        log.trace("del pkt: %s", self._pkt)
        if self._pkt is not None:
            _pkt._freePkt(self._pkt)

    def generate(self, sorted=False):
        """NO JSON ALLOWED"""
        return self.generate_dict()

    def _build_parsed_values(self):
        """
        Take something in the data format and turn it into
        an array of dictionaries defining the data in the particle
        with the appropriate tag.
        @throws SampleException If there is a problem with sample creation
        """
        log.trace("_build_parsed_values")
        pktid, srcname, orbtimestamp, raw_packet, pkttype, pkt = self.raw_data

        result = []
        pk = AntelopeOrbPacketParticleKey
        vid = DataParticleKey.VALUE_ID
        v = DataParticleKey.VALUE


        # Calculate sample timestamp
        self.set_internal_timestamp(unix_time=_pkt._Pkt_time_get(pkt))

        result.append({vid: pk.ID, v: pktid})
        result.append({vid: pk.DB, v: _pkt._Pkt_db_get(pkt)})
        result.append({vid: pk.DFILE, v: _pkt._Pkt_dfile_get(pkt)})
        result.append({vid: pk.SRCNAME, v: _pkt._Pkt_srcnameparts_get(pkt)})
        result.append({vid: pk.VERSION, v: _pkt._Pkt_version_get(pkt)})
        result.append({vid: pk.STRING, v: _pkt._Pkt_string_get(pkt)})
        result.append({vid: pk.TIME, v: _pkt._Pkt_time_get(pkt)})
        result.append({vid: pk.TYPE, v: _pkt._Pkt_pkttype_get(pkt)})

        pf = None
        pfptr = _pkt._Pkt_pfptr_get(pkt)
        if pfptr != None:
            try:
                pf = _stock._pfget(pfptr, None)
            finally:
                _stock._pffree(pfptr)
        result.append({vid: pk.PF, v: pf})

        # channels
        channels = []
        ck = AntelopeOrbPacketParticleChannelKey
        for pktchan in _pkt._Pkt_channels_get(pkt):
            channel = {}
            channels.append(channel)
            channel[ck.CALIB] = _pkt._PktChannel_calib_get(pktchan)
            channel[ck.CALPER] = _pkt._PktChannel_calper_get(pktchan)
            channel[ck.CHAN] = _pkt._PktChannel_chan_get(pktchan)
            channel[ck.CUSER1] = _pkt._PktChannel_cuser1_get(pktchan)
            channel[ck.CUSER2] = _pkt._PktChannel_cuser2_get(pktchan)
            channel[ck.DATA] = np.array(_pkt._PktChannel_data_get(pktchan))
            channel[ck.DUSER1] = _pkt._PktChannel_duser1_get(pktchan)
            channel[ck.DUSER2] = _pkt._PktChannel_duser2_get(pktchan)
            channel[ck.IUSER1] = _pkt._PktChannel_iuser1_get(pktchan)
            channel[ck.IUSER2] = _pkt._PktChannel_iuser2_get(pktchan)
            channel[ck.IUSER3] = _pkt._PktChannel_iuser3_get(pktchan)
            channel[ck.LOC] = _pkt._PktChannel_loc_get(pktchan)
            channel[ck.NET] = _pkt._PktChannel_net_get(pktchan)
            channel[ck.SAMPRATE] = _pkt._PktChannel_samprate_get(pktchan)
            channel[ck.SEGTYPE] = _pkt._PktChannel_segtype_get(pktchan)
            channel[ck.STA] = _pkt._PktChannel_sta_get(pktchan)
            channel[ck.TIME] = _pkt._PktChannel_time_get(pktchan)

        result.append({vid: pk.CHANNELS, v: channels})

        return result


types = ['_'.join((DataParticleType.ANTELOPE_ORB_PACKET, sfx)) for sfx in SUFFIXES]

PARTICLE_CLASSES = {
    sfx: type('AntelopeOrbPacketParticle' + sfx.upper(), (AntelopeOrbPacketParticle,), dict(_data_particle_type=typ))
    for (sfx, typ) in zip(SUFFIXES, types)
}

def make_antelope_particle(get_r, *args, **kwargs):
    """Inspects packet channel, returns instance of appropriate antelope data particle class."""
    pktid, srcname, orbtimestamp, raw_packet = get_r
    pkt = None
    pkttype, pkt = _pkt._unstuffPkt(srcname, orbtimestamp, raw_packet)
    if pkttype < 0:
        raise SampleException("Failed to unstuff ORB packet")
    try:
        srcnameparts = _pkt._Pkt_srcnameparts_get(pkt)
        net, sta, chan, loc, dtype, subcode = srcnameparts
        ParticleClass = PARTICLE_CLASSES[chan.lower()]
        raw_data = pktid, srcname, orbtimestamp, raw_packet, pkttype, pkt
    except Exception:
        _pkt._freePkt(pkt)
        raise
    return ParticleClass(raw_data, *args, **kwargs)


class AntelopeOrbParser(Parser):
    """
    Pseudo-parser for Antelope ORB data.

    This class doesn't really parse anything, but it fits into the DSA
    architecture in the same place as the other parsers, so leaving it named
    parser for consistency.

    What this class does do is connect to an Antelope ORB and get packets from
    it.
    """

    def __init__(self, config, state,
                 state_callback, publish_callback, exception_callback = None):
        super(AntelopeOrbParser, self).__init__(config,
                                           None,
                                           state,
                                           None,
                                           state_callback,
                                           publish_callback,
                                           exception_callback)

        # NOTE Still need this?
        self.stop = False

        if state is None:
            state = {}
        self._state = state

        orbname = config[ParserConfigKey.ORBNAME]
        select = config[ParserConfigKey.SELECT]
        reject = config[ParserConfigKey.REJECT]

        keys = (ParserConfigKey.SELECT, ParserConfigKey.REJECT)
        if [select, reject] != [state.get(k) for k in keys]:
            log.warning("select/reject changed; resetting tafter to 0")
            state.update({k: config[k] for k in keys})
            state[StateKey.TAFTER] = 0.0

        tafter = state[StateKey.TAFTER]

        self._orbreapthr = OrbReapThr(orbname, select, reject, float(tafter), timeout=0, queuesize=100)
        log.info("Connected to ORB %s %s %s %s" % (orbname, select, reject, tafter))

    def kill_threads(self):
        self._orbreapthr.stop_and_wait()
        self._orbreapthr.destroy()

    def get_records(self):
        """
        Go ahead and execute the data parsing loop up to a point. This involves
        getting data from the file, stuffing it in to the chunker, then parsing
        it and publishing.
        @param num_records The number of records to gather
        @retval Return the list of particles requested, [] if none available
        """
        log.trace("GET RECORDS")
        try:
            if self.stop:
                return
            get_r = self._orbreapthr.get()
            pktid, srcname, orbtimestamp, raw_packet = get_r
            log.trace("get_r: %s %s %s %s", pktid, srcname, orbtimestamp, len(raw_packet))
            particle = make_antelope_particle(
                get_r,
                preferred_timestamp = DataParticleKey.INTERNAL_TIMESTAMP,
                new_sequence=False,
            )
            self._publish_sample(particle)
            # TODO rate limit state updates?
            self._state[StateKey.TAFTER] = orbtimestamp
            log.debug("State: ", self._state)
            self._state_callback(self._state, False) # push new state to driver
        except (Timeout, NoData), e:
            log.debug("orbreapthr.get exception %r" % type(e))
            return None
        return get_r


