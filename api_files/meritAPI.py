from collections import defaultdict
from collections import OrderedDict
from ats import aetest
import logging
from ats.log.utils import banner
import yaml
import datetime as dt
from tzlocal import get_localzone
import time
import re
import pymongo
from pymongo import MongoClient
import datetime
import uuid
from xml.dom import minidom
import os


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


import sys
import pdb

class ForkedPdb(pdb.Pdb):
    '''A Pdb subclass that may be used
    from a forked multiprocessing child
    '''

    def interaction(self, *args, **kwargs):
        _stdin = sys.stdin
        try:
            sys.stdin = open('/dev/stdin')
            pdb.Pdb.interaction(self, *args, **kwargs)
        finally:
            sys.stdin = _stdin

class Hw_data():
    """Used to get various hw information on a testbed."""

    def get_rp_lc_types(rtr):
        """Use to collect the RSP and LC types on chassis."""

        output = rtr.mgmt1.execute('show platform')
        # GET ALL LINECARD STATES FOR CXR
        card_state = []
        for line in output.split('\n'):
            if re.match(r'\d+\/\w+\/\w+', line) is not None:
                # MATCH INTAL SHOW PLATFORM OUTPUT: 0/RSP0/CPU0
                m = re.search(r'\w+\/\w+\/\w+ +'
                                # MATCH CARD TYPE: A9K-MOD160-SE
                               '(\w+-\w+-\w+-\w+\(\w+\)|\w+-\w+-\w+-\w+|\w+-\w+-\w+\(\w+\)|\w+-\w+-\w+|\w+-\w+\(\w+\)|\w+-\w+|Slice) +'
                               # MATCH CARD SATE: IOS XR RUN
                               '(\w+ \w+ \w+|\w+ \w+|\w+)', line)

                card_state.append(m.group(1))

        # CREATE LIST OF RP AND LC TYPES
        lc_list = []
        for cards in card_state:
            if '(Active)' in cards or '(Standby)' in cards:
                rp_type = re.sub(r'\(Active\)|\(Standby\)', '', cards)
            else:
                lc_list.append(cards)


        return rp_type, lc_list

class Traffic_data(object):
    """Various traffic related methods."""

    def traffic_stream_data(ixia):
        """Used to gather traffic stream data. Will return directory"""

        traffic_dict = {}

        stats = ixia.getStats(viewName='Flow Statistics')
        for key,value in stats.items():
            try:
                stream_name = value['Traffic Item']
                loss = value['Loss %'] 
                print('Matthew {} {}'.format(stream_name, loss))

                traffic_dict[stream_name] = loss
            except:
                log.info('stream {} error handling caught'.format(stream_name))

        return traffic_dict

    def pre_post_traffic(d1, d2):
        """Used to compare pre and post state traffic dict."""
        d1_keys = set(d1.keys())
        d2_keys = set(d2.keys())
        intersect_keys = d1_keys.intersection(d2_keys)
        added = d1_keys - d2_keys
        removed = d2_keys - d1_keys
        modified = {o : (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
        same = set(o for o in intersect_keys if d1[o] == d2[o])

        return added, removed, modified, same

    def traffic_check(ixia, traffic_state, ):
        """collect the traffic stream data and send to yaml file"""

        log.info('CLEARING IXIA STATS PLEASE WAIT...')
        # CLEAR IXIA COUNTERS
        ixia.clearStats()
        time.sleep(180)

        traffic_stream_data = Traffic_data.traffic_stream_data(ixia)
        log.info('Matthew traffic_stream_data = {}'.format(traffic_stream_data))
        
        return traffic_stream_data


class Report(object):
    """Used to write data into report log."""

    def traffic_score(release, pre_traffic_dict, post_traffic_dict):
        """Used to come up with a traffic score."""


        score_dict = {}

        # GETTING TOTAL NUMBER OF STREAMS IN DICTIONARY
        total_streams = len(post_traffic_dict.keys())

        # COMPARE PRE AND POST TRAFFIC DICTS
        added, removed, modified, same = \
            Traffic_data.pre_post_traffic(pre_traffic_dict, post_traffic_dict)

        num_loss_stream = 0
        # TRAFFIC STREAMS THAT STARTED WITH NO LOSS AND ENDED WITH LOSS
        for key, value in modified.items():
            try:
                if float(value[1]) >= 5.00:
                    num_loss_stream += 1
            except ValueError:
                log.info('Stream {} being ommited as it has ValueError of {}'.format(key, value))

        # CALCULATE SCORE
        bad_steams =  total_streams - num_loss_stream
        log.info('Matthew total_streams = {} and num_loss_stream = {}'.format(total_streams, num_loss_stream))
        score = bad_steams/total_streams
        log.info('Matthew bad_steams = {} total_streams = {} score = {}'.format(bad_steams, total_streams, score))
        traffic_score = score * 100
        log.info('Matthew traffic_score = {}'.format(traffic_score))

        score_dict['merit_traffic_score'] = int(traffic_score)
        log.info('Traffic score = {}'.format(score_dict['merit_traffic_score']))

        return score_dict


    def rtr_log(rtr, traffic_state):
        """Used to get some basic testbed related information.
           function gets the following information.

           1. date and time.
           2. image testbed is on.
           3. finds testbed os type (eXR or cXR).
           4. chassis type.

           ARGS:
           rtr - router handle.
        """

        meritData = {}
        
        # 1. GETTING TIME
        local_tz = get_localzone()
        now = dt.datetime.now(local_tz)
        timestamp = now.strftime('%m-%d-%Y')

        # 2. CHECK WHAT IMAGE TESTBED IS ON
        current_image = rtr.mgmt1.execute('show install active summary | ex CSC')
        # GETTING RELEASE NUMBER EXAMPLE : 6.2.1.34I
        cur_image = re.search(r'(\d+\.\d+\.\d+).(\d+)(\w+)', current_image)
        
        # 3. CHECK OS TYPE
        if traffic_state == 'pre_traffic':
            try:
                # CHECK IF OS IS CLASSIC XR OR EXR
                cxr_exr = rtr.mgmt1.execute('bash -c uname -a')
                if 'Linux' in cxr_exr:
                    log.info(banner('OS TYPE IS eXR'))
                    os_type = 'eXR'
            except:
                log.info(banner('OS TYPE IS cXR'))
                os_type = 'cXR'

            hostname_output = rtr.mgmt1.execute('show run hostname')
            hostname = re.search(r'hostname +(.*)', hostname_output)
            hostname = re.sub(r'\r', '' , hostname.group(1))
            


        # 4. CHECK CHASSIS TYPE
        output = rtr.mgmt1.adminexec('show inventory chassis')
        mo = re.search(r'PID: +(\w+-\w+-\w+|\w+-\w+)', output)
        chassis = mo.group(1)

        if traffic_state == 'pre_traffic':
            upgrade_key = 'pre_upgrade_image'
        else:
            upgrade_key = 'post_upgrade_image'

        # ADD ALL KEY VALUE PAIRS TO DICTIONARY
        if traffic_state == 'pre_traffic':
            # GET RP AND LC TYPES ON CHASSIS
            rp_type, lc_types, = Hw_data.get_rp_lc_types(rtr)

            meritData['date'] = timestamp
            meritData['chassis'] = chassis
            meritData['RSP Type'] = rp_type
            meritData['LC Type'] = lc_types
            meritData['hostname'] = hostname
            meritData['os_type'] = os_type


        # VALUES WILL GET ADDED TO DB
        meritData[upgrade_key] = str(cur_image.group(0))

        if traffic_state == 'pre_traffic':
            return os_type, chassis, cur_image, meritData
        else:
            return cur_image, meritData


    def traffic_log(traffic_state, traffic_dict):
        """Used to send traffic stream data into a log file.

           ARGS:
           rtr - router handle.
           traffic_state - either pre_traffic or post_traffic.

           DESCRIPTION:
           """

        
        update_dict = {}
        no_traffic_loss_dict = {}
        traffic_loss_dict = {}
    
        
        for key, value in traffic_dict.items():
            log.info('matthew traffic_dict key is {} and value is {}'.format(key, value))
            traffic_dict.update({key:value})

        for key, value in traffic_dict.items():
            try:
                if float(value) <= 5.00:
                    no_traffic_loss_dict[key] = value
            except ValueError:
                log.info('Stream {} has a ValueError of {}'.format(key, value))

        
        for key, value in traffic_dict.items():
            try:
                if float(value) >= 5.00:
                    traffic_loss_dict[key] = value
            except ValueError:
                log.info('Stream {} has a ValueError of {}'.format(key, value))

        # GET NUMBER OF STREAMS WITH LOSS, NO LOSS AND TOTAL NUM OF STREAMS
        streams_no_loss = len(no_traffic_loss_dict.keys())
        streams_with_loss = len(traffic_loss_dict.keys())
        total_streams = streams_no_loss + streams_with_loss


        update_dict[traffic_state + '_streams_with_no_loss'] = no_traffic_loss_dict
        update_dict[traffic_state + '_streams_with_loss'] = traffic_loss_dict
        update_dict[traffic_state + '_num_streams_without_loss'] = streams_no_loss
        update_dict[traffic_state + '_num_streams_with_loss'] = streams_with_loss
        update_dict[traffic_state + '_total_streams'] = total_streams

        log.info('Matthew the update_dict is {}'.format(update_dict))

        return update_dict

class Psat_logging():
    """Various psat logging utilities"""

    def xml_parse(xml_tag, psat_unzip_output_folder):
        """Used to parse XML file to find various tags."""

        from xml.dom import minidom
        xmldoc = minidom.parse('{}/ResultsSummary.xml'.format(psat_unzip_output_folder))
        itemlist = xmldoc.getElementsByTagName(xml_tag)

        for s in itemlist:
            xml_tag_result = s.childNodes[0].nodeValue

        return xml_tag_result

    def get_psat_web_link(psat_unzip_output_folder):
        """Used to get PSAT URL from PSAT Report file."""
        command = 'ls {}/*.report*'.format(psat_unzip_output_folder)
        path = os.popen(command).read()
        path = path.replace('\n', '')

        with open(path) as f:
            for line in f:
                if re.match(r'(Web +Link: +)(http:\/\/.*)',line) :
                    psat_url = re.search(r'Web +Link: +(http:\/\/.*)', line)

        return psat_url.group(1)

    def psat_results_to_db(traffic_score, psat_unzip_output_folder):

        meritData = {}

        # PARSE XML OF PSAT RESULT SUMMARY
        passed_tc = Psat_logging.xml_parse('passed', psat_unzip_output_folder)
        failed_tc = Psat_logging.xml_parse('failed', psat_unzip_output_folder)
        blocked_tc = Psat_logging.xml_parse('blocked', psat_unzip_output_folder)
        skipped_tc = Psat_logging.xml_parse('skipped', psat_unzip_output_folder)

        # ADD RESULTS TO DICT
        meritData['psat_passed_tc'] = passed_tc
        meritData['psat_failed_tc'] = failed_tc
        meritData['psat_blocked_tc'] = blocked_tc
        meritData['psat_skipped_tc'] = skipped_tc

        # GET TOTAL NUMBER OF TC'S RUN
        total_tcs_num = (int(meritData['psat_passed_tc']) + int(meritData['psat_failed_tc']) +
                         int(meritData['psat_blocked_tc']) + int(meritData['psat_skipped_tc']))

        # GET TOTAL NUMBER OF FAILED TC'S
        total_fail_tc_num = (int(meritData['psat_failed_tc']) +
                             int(meritData['psat_blocked_tc']) +
                             int(meritData['psat_skipped_tc']))


        # CALCULATE PSAT SCORE
        bad_steams =  total_tcs_num - total_fail_tc_num
        score = bad_steams/total_tcs_num
        final_psat_score = score * 100

        # GETTING PSAT URL FROM FUNCTION
        psat_url = Psat_logging.get_psat_web_link(psat_unzip_output_folder)

        # ADD TO DICT
        meritData['psat_score'] = int(final_psat_score)
        meritData['psat_url'] = psat_url

        # CALULATE MERIT FINAL SCORE
        combo_score = int(traffic_score) + int(final_psat_score)
        merit_final_score = int(combo_score/2)

        # ADD FINAL SCORE TO DICT
        meritData['merit_final_score'] = merit_final_score

        log.info('Matthew psat meritData dict = {}'.format(meritData))

        return meritData
