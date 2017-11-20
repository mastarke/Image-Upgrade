#!/usr/bin/env python
import os
import re
import time
import logging
import itertools
from ats.log.utils import banner
from IPython import embed
import importlib
from ats.easypy import runtime
from ats import aetest
from IPython import embed
import sys
import pdb
from ats.topology import loader
from pymongo import MongoClient

# IMPORT FILES FROM ANOTHER FOLDER
sys.path.insert(0, '/ws/mastarke-sjc/my_local_git/image_picker_site/api_files')
import meritAPI 
from IxNetRest import *


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

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


def send_install_cmd(ip_addr, username, password, rtr_hostname, install_cmd):

    """Used to send install command via pexpect. This is prefered as Csccon
       does not handle the cXR install add command well."""

    import pexpect
    attempts = 4
    rtr_hostname_result = False

    for i in range(attempts):
        log.info('attempting to connected to rtr attempt {} of {} via ip: {}'
                  .format(i, attempts, ip_addr))

        # ATTEMPTING TELNET CONNECTION
        child = pexpect.spawn('telnet {}'.format(ip_addr), timeout=90)

        if child.isatty() == True and child.isalive() == True:
            log.info(banner('Established connection to {} now sending '
                             'username {} and password {}'.format(ip_addr,
                                                           username, password)))
            log.info('sending pexpect username')
            child.expect ('Username: ', timeout=90)
            child.sendline ('{}'.format(username))
            data = child.before
            str_data = str(data, 'utf-8')
            for line in str_data.split('\n'):
                log.info(line)

            child.expect ('Password:', timeout=90)
            child.sendline ('{}'.format(password))
            child.expect ('#')
            data = child.before
            str_data = str(data, 'utf-8')
            for line in str_data.split('\n'):
                log.info(line)
                if rtr_hostname in line:
                    rtr_hostname_result = True
                    log.info(banner('Pexpect successful found router prompt {} '
                                     'telnet was successful'.format(rtr_hostname)))
            if rtr_hostname_result == True:
                break
            else:
                log.warning('could not find router hostname '
                            'prompt {}'.format(rtr_hostname))
        else:
            log.warning('connection was unsuccessful connection '
                        'status = {}'.format(child.isatty()))
            child.close()

    log.info('@@@ Pexpect logged into router \n'
             'sending command : {} @@@'.format(install_cmd))
    try:
        child.sendline ('{}'.format(install_cmd))
        child.expect ('#')
    except:
        log.info(banner('@@@ SENT INSTALL CMD VIA PEXPECT @@@'))
    child.close()

def remove_inactive_pies(rtr, os_type):
    """Used to remove inactive images and pies."""

    # REMOVE INACTIVE IMAGES
    try:
        if os_type == 'cXR':
            output = rtr.mgmt1.execute('admin install remove inactive '
                                       'asynchronous prompt-level none')
        else:
            output = rtr.mgmt1.execute('install remove inactive all')
    except:
        log.info('@@@ SENT REMOVE INACTIVE PIE COMMAND @@@')

    time.sleep(5)
    

    install_log_num = re.search(r'Install operation (\d+)', output)
    for i in range(10):
        output = rtr.mgmt1.execute('show install log {} detail'.format(install_log_num.group(1)))
        # MATCH OS TYPE EXR AND CXR ASR9K
        if re.search(r'Install operation \d+ completed successfully', output):
            log.info('Install remove inactive completed successfully')
            break
        # MATCH OS TYPE EXR ON FRETTA
        elif re.search(r'install remove action finished successfully', output):
            log.info('Install remove inactive finished successfully')
            break
        # MATCH OS TYPE CXR WHEN THERE IS NO INSTALLED PAKAGES
        elif re.search(r'there are no packages that can be removed', output):
            log.info('Currently no packages to be removed')
            break
        # MATCH OS TYPE EXR WHEN THERE IS NO INSTALLED PAKAGES
        elif re.search(r'No inactive package', output):
            log.info('Currently no packages to be removed')
            break
        else:
            log.info('Install remove inactive not completed')
            time.sleep(60)

def get_total_image_size(file_dir, pies):
    """Function to return toatal of list of pies."""

    file_size_list = []
    for images in pies.split():
        file_data = os.popen('ls -lh --block-size=M {}{}'.format(file_dir,images)).read()

        # REGEX WILL MATCH:
        # mastarke eng 462M Jun  9 13:42 /tftpboot/mastarke/asr9k-mini-px.pie-6.2.2.13I
        file_size = re.search(r'eng +(\d+)', file_data)

        file_size_list.append(int(file_size.group(1)))

        total_image_size = sum(file_size_list)

    return total_image_size


def get_all_linecards(os_type, rtr):
    """Used to return list of all linecards in testbed."""

    if os_type == 'eXR':
        output = rtr.mgmt1.execute('show platform vm')
    else:
        output = rtr.mgmt1.execute('show platform')

    linecards = []
    for line in output.split('\n'):

        if re.match(r'\d+\/\w+\/\w+', line) is not None:
            m = re.search(r'\d+\/\w+\/\w+', line)

            linecards.append(m.group(0))

    return linecards


def poll_lc_is_up(linecard, os_type, rtr, result=0):
    """Used to poll when linecards in testbed are back online."""

    import itertools
    count = 1
    end_count = 30

    while count <= end_count:

        num_cards_up = 0
        if os_type == 'eXR':
            output = rtr.mgmt1.execute('show platform vm')
            card_state = re.findall(r'(FINAL Band)',output)
        else:
            output = rtr.mgmt1.execute('show platform')
            # GET ALL LINECARD STATES FOR CXR
            card_state = []
            for line in output.split('\n'):
                if re.match(r'\d+\/\w+\/\w+', line) is not None:
                    # MATCH INTAL SHOW PLATFORM OUTPUT: 0/RSP0/CPU0
                    m = re.search(r'\w+\/\w+\/\w+ +'
                                    # MATCH CARD TYPE: A9K-MOD160-SE
                                   '(\w+-\w+-\w+-\w+\(\w+\)|\w+-\w+-\w+-\w+|\w+-\w+-\w+\(\w+\)|\w+-\w+-\w+|\w+-\w+\(\w+\)|\w+-\w+) +'
                                   # MATCH CARD SATE: IOS XR RUN
                                   '(\w+ \w+ \w+|\w+ \w+|\w+)', line)

                    card_state.append(m.group(2))

        for card, state in itertools.zip_longest(linecard, card_state):


            if state == 'FINAL Band' or state == 'IOS XR RUN' or state == 'OK':
                log.info('PASS...Linecard {} state is in {}'.format(card, state))
                num_cards_up += 1
                continue

            elif state == 'ADMIN DOWN':
                log.info('SKIPING...Linecard {} state is in {}'.format(card, state))
                num_cards_up += 1
                continue

            elif state == 'UNPOWERED':
                log.info('SKIPING...Linecard {} state is in {}'.format(card, state))
                num_cards_up += 1
                continue

            elif count == end_count:
                self.failed('FAIL...Linecard {} state is in {}'.format(card, state))
                result = 1
            else:
                log.info('Polling...Linecard {} state is in {}'.format(card, state))

                time.sleep(60)

        if len(linecard) == num_cards_up:
            log.info('{} of {} linecards are up'.format(len(linecard), num_cards_up))
            break
        else:
            log.info('{} of {} linecards are up'.format(len(linecard), num_cards_up))

        count += 1

    return result

def running_config_checker(original_cfg, new_cfg):

    '''Used to compare configs before and after image upgrade'''

    import difflib
    original_cfg=original_cfg.splitlines(1)
    new_cfg=new_cfg.splitlines(1)

    diff=difflib.unified_diff(original_cfg, new_cfg)

    return ''.join(diff)

class Common_setup(aetest.CommonSetup):
    """Common Setup section."""




    # IMPORT THE JOBFILE INTO NAMESPACE
    jobfile = runtime.job.name  # GET JOB FILE NAME
    a = importlib.import_module(jobfile)  # IMPORT THE JOB FILE INTO NAMESPACE
    ScriptArgs = a.ScriptArgs()  # INSTANCE OF SRSCRIPTARGS

    
    # OPTINAL ARGS FROM JOB FILE
    try:
        get_score = ScriptArgs.get_score
    except:
        get_score = None
        print('Setting get_score to {}'.format(get_score))


    # IMPORT YAML FILE ATTRIBUTES
    testbed = loader.load(ScriptArgs.testbed_file)
    rtr = testbed.devices[ScriptArgs.rtr]
    mgmt_ip = rtr.connections.vty_1['ip']
    user_tftp_dir = ScriptArgs.user_tftp_dir
    platform = ScriptArgs.platform
    image_repo = ScriptArgs.image_repo
    tftp_ip = ScriptArgs.tftp_ip
    user = rtr.tacacs.username
    passwd = rtr.passwords['line']


    if platform == 'asr9k-px':
        os_type = 'cXR'
    else:
        os_type = 'eXR'

    log.info('OS TYPE IS {}'.format(os_type))

   
    log.info(banner('@@@ ATTEMPTING TO TELNET TO ROUTER {} @@@'.format(rtr)))
    # CONNECTING TO ROUTER VIA VTY LINE
    rtr.connect(via ='vty_1', alias = 'mgmt1')
    rtr.connect(via ='vty_2', alias = 'mgmt2')

    # CHECK PLATFORM TYPE 
    platform = rtr.mgmt1.adminexec('show inventory chassis')
    m = re.search(r'Descr: +(NCS\d+|ASR-\d+|"ASR \d+|ASR +\d+)', platform, re.IGNORECASE)
    log.info('Matthew m.group is {}'.format(m.group(0)))
    platform = m.group(0)
    
    if 'NCS' in platform or 'ncs' in platform:
        log.info('ncs platform type  {}'.format(platform))
        platform_type = 'ncs'
    else:
        log.info('asr9k platform type  {}'.format(platform))
        platform_type = 'asr9k'


    global os_type_list
    os_type_list = []
    os_type_list.append(os_type)


    # GET ALL THE LINECARDS THAT ARE UP IN TESTBED
    testbed_lc = get_all_linecards(os_type, rtr)
    lc_result = poll_lc_is_up(testbed_lc, os_type, rtr)

    if lc_result != 0:
        self.failed('LC did not return to up state.')

    if get_score == True:

        # DATABASE ARGUMENTS
        db_host = ScriptArgs.db_host
        db_name = ScriptArgs.db_name
        db_collection = ScriptArgs.db_collection

        log.info('ATTEMPTING TO CONNECT TO IXIA VIA REST API')
        ixia = IxNetRestMain(ScriptArgs.ixia_chassis_ip, '11009')
        sessionId = ixia.sessionId
        log.info('sessionId = {}'.format(sessionId))
        
        # CHECK IF IXIA CONNECTED
        try:
            if re.match('http:\/\/\d+.\d+.\d+.\d+:11009', sessionId):
                log.info('IXIA REST API connected via {}'.format(sessionId))
        except:
            log.info('Ixia not connected')

        log.info('STARTING IXIA TRAFFIC...PLEASE WAIT')
        ixia.startTraffic()
        time.sleep(180)

        # CALLING RTR LOGGING FUNCTION
        os_type, chassis, cur_image, db_insert_data_dict = \
            meritAPI.Report.rtr_log(rtr, traffic_state='pre_traffic')

        # SETTING RELEASE VERSION
        release = cur_image.group(1)

        # CALLING PRE TRAFFIC CHECK METHOD
        pre_traffic_stream_data = \
            meritAPI.Traffic_data.traffic_check(ixia, traffic_state='pre_traffic')
        
        
        # SEND DATA TO LOG
        update_data_dict = meritAPI.Report.traffic_log(traffic_state='pre_traffic', 
                                                       traffic_dict=pre_traffic_stream_data)

        pre_upgrade_config = rtr.mgmt1.execute('show run')

        db_insert_data_dict.update(update_data_dict)

    # REMOVING INACTIVE PIES
    remove_inactive_pies(rtr, os_type)

@aetest.loop(os_type=os_type_list)
class ImageUpgrade(aetest.Testcase):
    """Upgrade image."""

    @aetest.setup
    def setup(self):
        """Testcase setup"""
        # GETTING COMMON_SETUP ATTRIBUTES TO PASS TO TC
        log.info('Matthew your in setup')

    @aetest.test
    def test(self):
        cs = Common_setup()



        # GETTING ACTIVE IMAGE ON TESTBED
        current_image = cs.rtr.mgmt1.execute('show install active summary | ex CSC')
        # GETTING RELEASE NUMBER EXAMPLE : 6.2.1.34I
        cur_image = re.search(r'(\d+\.\d+\.\d+).(\d+)(\w+)', current_image)
        if cs.os_type == 'cXR':
            # STORING ALL ACTIVE PIES INTO LIST FOR cXR
            current_image_pies = re.findall(r'asr9k-(\w+-\w+)', str(current_image))
        else:
            # CHECKING PLATFORM TYPE
            if cs.platform_type =='ncs':
                platform_match = 'ncs5500'
            else:
                platform_match = 'asr9k'
            
            # STORING ALL ACTIVE PIES INTO LIST FOR eXR
            current_image_pies = re.findall(r'{}-(mpls-te-rsvp|\w+)'.format(platform_match), str(current_image))
            if len(current_image_pies) == 1 and 'xr' in current_image_pies:
                for item in current_image_pies:
                    # CHANGE XR TO FULL AS THERE IS NO IMAGE CALLED XR IN REPO
                    for list_index,list_value in enumerate(current_image_pies):
                         if list_value == 'xr':
                            current_image_pies.pop(list_index)
                            current_image_pies.insert(list_index, 'full')
            else:
                # CHANGE XR TO MINI AS THERE IS NO IMAGE CALLED XR IN REPO
                for list_index,list_value in enumerate(current_image_pies):
                     if list_value == 'xr':
                        current_image_pies.pop(list_index)
                        current_image_pies.insert(list_index, 'mini')

        log.info(banner('images active on router = {}'.format(current_image_pies)))

        output = os.popen('ls {}'.format(cs.image_repo)).read()
        log.info(output)

        if cs.os_type == 'cXR':
            images = re.findall(r'asr9k-\w+-px.pie-\d+\.\d+\.\d+.\d+\w+.*|'
                     'asr9k-asr\w+-\w+-\w+\.\w+-\d+\.\d+\.\d+\.\d+\w+|'
                     'asr9k-\w+-infra-\w+.\w+-\d+.\d+.\d+.\d+\w+|'
                     'asr9k-\w+-nV-\w+.\w+-\d+.\d+.\d+.\d+\w+',str(output))
        else:
            images = re.findall(r'{}-\w+.*'.format(platform_match), str(output))

        all_images = ''
        global all_images_list
        all_images_list = []
        for item in images:
            for cur_pie in current_image_pies:
                # ONLY GETTING THE PIES THAT ARE ACTIVE ON TESTBED
                if cur_pie in item and 'V2' not in item and '99' not in item:
                    copy_cmd =  'cp' + ' ' + cs.image_repo + '/' + item + ' ' + '{}'.format(cs.user_tftp_dir)
                    all_images += str(item) + ' '
                    all_images_list.append(item)
                    log.info(copy_cmd)
                    output = os.popen(copy_cmd).read()

        # REMOVING ANY POSSIBLE DUPLICATES THAT WERE COPIED
        pie_num = len(all_images_list)
        log.info('copied images :\n'
                 '{}\n\n :the number of copied images was {} checking for '
                 'possible duplicate pies that were copied:\n'
                 .format(all_images_list, pie_num))
        # FUNCTION TO REMOVE DUPLICATES
        all_images_list = list(set(all_images_list))
        log.info('Before checking for duplicates pies there were {} pies.'
                 'After scrubbing for duplicates there is now {} pies:\n\n'
                 '{}'.format(pie_num, len(all_images_list), all_images_list))


        # CHECKING CURRENT IMAGES AND COPIED UPGRADE IMAGES IS SYMMETRICAL
        if len(all_images_list) == len(current_image_pies):
            log.info(banner('Pass there is currently {} images active on the\n'
                      'testbed. Copied {} images to tftp directory.'
                      .format(len(all_images_list),len(current_image_pies))))
        else:
            self.failed('Fail there is currently {} images active on the '
                       'testbed. Copied {} images to tftp directory.'
                       .format(len(all_images_list),len(current_image_pies)))

        # CHANGE PERMISSIONS ON K9SEC PIE TO ENSURE IT CAN LOAD
        os.popen('chmod 777 {}*k9sec*'.format(cs.ScriptArgs.user_tftp_dir)).read()
        # USE VARIABLE THAT WAS CHECKED FOR DUPLICATES.
        all_images = ' '.join(all_images_list)

        
        if cs.os_type == 'cXR':
            cmd = ('admin install add source tftp://{}{} {} '
                   'asynchronous activate prompt-level none'
                   .format(cs.tftp_ip, cs.user_tftp_dir, all_images))
        else:
            cmd = ('install add source tftp://{}{} {} '
                   .format(cs.tftp_ip, cs.user_tftp_dir, all_images))

        log.info('Matthew install command is {}'.format(cmd))

        # SEND INSTALL COMMAND ON ROUTER
        try:
            if cs.os_type == 'cXR':
                # SENDING cXR INSTALL CMD VIA PEXPECT
                send_install_cmd(cs.mgmt_ip, cs.user, cs.passwd,
                                 cs.rtr.device.name, cmd)
            else:
                # SENDING cXR INSTALL CMD VIA Csccon
                cs.rtr.mgmt1.execute(cmd)
        except:
            log.info('@@@  SENT INSTALL COMMAND  @@@')

        start_time=time.time() # TAKING CURRENT TIME AS STARTING TIME
        
        time.sleep(30)
        #VERIFY INSTALL COMMAND WAS SUCCESSFUL
        install_request = cs.rtr.mgmt2.execute('show install request')
        if cs.os_type == 'cXR':
            # GETTING INSTALL OPERATION NUMBER
            log_match = re.search(r'Install operation (\d+)', str(install_request))
            install_log_num = log_match.group(1)
        else:
            # GETTING INSTALL OPERATION NUMBER
            log_match = re.search(r'The install add operation (\d+)', str(install_request))
            install_log_num = log_match.group(1)
            install_log_status = cs.rtr.mgmt2.execute('show install log {}'
            .format(str(install_log_num)))


        # VERIFY INSTALL IS STARTED
        if cs.os_type == 'cXR':
            if 'Download in progress' not in install_request:
                self.failed('Fail cXR image did not start to download:\n\n'
                      '@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n'
                      '{}'.format(install_request))
            else:
                log.info('Pass cXR image is downloading:\n\n'
                      '@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n'
                      '{}'.format(install_request))
        else:
            if 'install add action started' in install_log_status:
                log.info('Pass eXR image started successfully')
            else:
                self.failed('eXR image did not stat successfully')


        # POLLING SYSTEM FOR TESTBED TO RELOAD
        count = 1
        end_count = 120
        while count <= end_count:
            if cs.os_type == 'cXR':
                # START A PING TO SYSTEM TO KNOW WHEN CONNECTION WILL BE LOST
                ping_output = os.popen('ping {} -c5'.format(cs.mgmt_ip)).read()
                if '100% packet loss' in ping_output:
                    log.info(banner('@@ Testbed reload has begun @@'))
                    time.sleep(60)
                    break
                elif count == end_count:
                    self.failed('Upgrade did not happen in expected amount'
                                ' of time. {} of {}'.format(count, end_count))

                else:
                    install_request = cs.rtr.mgmt2.execute('show install request')
                    log.info(install_request)
                    log.info('@@@ testbed is still installing image {} '
                             'attempt {} of {} @@@\n'.format(install_request,
                                                             count, end_count))
            else:
                # POLLING EXR INSTALLATION
                install_log_status = cs.rtr.mgmt2.execute('show install log {}'
                .format(str(install_log_num)))

                if ('Install operation {} finished successfully'
                    .format(install_log_num) in install_log_status):
                    log.info('Pass adding eXR image completed successfully\n'
                             'starting to activate eXR image.')
                    break
                elif 'ERROR!' in install_log_status:
                    self.failed('Install add failed to add image')
                    break
                elif count == end_count:
                    self.failed('Upgrade did not happen in expected amount'
                                ' of time. {} of {}'.format(count, end_count))
                else:
                    log.info('@@@ eXR image is still downloading {} of {} @@@'.format(
                                                                     count, end_count))

            time.sleep(60)
            count += 1

        # ACTIVATE EXR IMAGE THAT WAS JUST ADDED
        if cs.os_type == 'eXR':
            install_inactivate = cs.rtr.mgmt2.execute('show install inactive')
            clean_str = re.sub(r'\r', '', install_inactivate)

            exr_inactive_image = re.findall(r'{}-\w+.*'.format(platform_match), clean_str)
            cmd = 'install activate'
            for item in exr_inactive_image:
                cmd = cmd + ' ' + item

            cmd = cmd + ' noprompt'

            # SENDING EXR ACTIVATION COMMAND
            activate_output = cs.rtr.mgmt2.execute(cmd)

            # STARTING PING TO POLL WHEN TESTBED IS RESTARTING
            count = 1
            end_count = 130
            while count <= end_count:
                ping_output = os.popen('ping {} -c5'.format(cs.mgmt_ip)).read()
                if '100% packet loss' in ping_output:
                    log.info(banner('@@ Testbed reload has begun @@'))
                    time.sleep(60)
                    break

                elif count == end_count:
                    self.failed('Install failed did not see image get '
                                'activated')
                else:
                    cs.rtr.mgmt2.execute('show install request')
                    log.info('@@@ testbed is still online attempt {} of {} @@@'
                             .format(count, end_count))
                    # DISPLAY PING OUTPUT
                    if count == 1 or count >= 60:
                        log.info(str(ping_output))

                count += 1
                time.sleep(60)

        # POLLING SYSTEM FOR TESTBED TO COME BACK ONLINE
        count = 1
        end_count = 30
        while count <= end_count:

            # START A PING TO SYSTEM TO KNOW WHEN TESTBED IS BACK ONLINE
            log.info('@@@  SENDING PING TO CHASSIS TO SEE WHEN ITS '
                     'BACK ONLINE  @@@')
            ping_output = os.popen('ping {} -c5'.format(cs.mgmt_ip)).read()
            rtr_status = False
            log.info(ping_output)

            if '0% packet loss' in ping_output and '100% packet loss' not in ping_output:
                log.info(banner('Testbed is back online'))
                time.sleep(30)

                # RE-ESTABLISH CONNECTIONS TO TESTBED
                log.info(banner('@@@  disconnecting telnet session  @@@'))
                cs.rtr.mgmt1.disconnect()
                cs.rtr.mgmt2.disconnect()
                log.info(banner('@@@  connecting telnet session  @@@'))
                cs.rtr.connect(via ='vty_1', alias = 'mgmt1')
                cs.rtr.connect(via ='vty_2', alias = 'mgmt2')

                rtr_status = True
                if cs.os_type == 'eXR':
                    install_log_num = int(install_log_num) + 1

                cmd = 'show install log {}'.format(install_log_num)
                install_req = cs.rtr.mgmt1.execute(cmd)
                log.info(install_req)

                # CHECKING IF INSTALL WAS SUCCESSFUL
                if cs.os_type == 'cXR':
                    if ('completed successfully' in install_req and rtr_status == True):
                        log.info('@@@  Pass cXR install was successful  @@@')
                        break
                    else:
                        self.failed('@@@  Fail cXR install was unsuccessful  @@@')
                else:
                    if('activate action finished successfully' in install_req
                       and 'Install operation {} finished successfully'.format(install_log_num)
                       in install_req):
                       log.info('@@@ Pass eXR image upgrade was '
                                '@@@ successful')
                       break
                    else:
                       self.failed('@@@ Fail eXR image upgrade was not '
                                    'successful  @@@')
            else:
                log.info('@@@  Testbed still not online attempt {} of {}  @@@'
                         .format(count, end_count))

                count += 1
                time.sleep(60)

        # POLL LC'S FOR WHEN THEY COME BACK ONLINE
        lc_result = poll_lc_is_up(cs.testbed_lc, cs.os_type, cs.rtr)
        
        if lc_result != 0:
            self.failed('LC did not return to up state.')

        # COMMIT NEWLY INSTALLED IMAGE
        if cs.os_type == 'cXR':
            install_commit = cs.rtr.mgmt1.execute('admin install commit')
        else:
            install_commit = cs.rtr.mgmt1.execute('install commit')

            # REMOVE INACTIVE IMAGES
            remove_inactive_pies(cs.rtr, cs.os_type)

            if cs.get_score == True:

                # TAKING CURRENT TIME - STARTING TIME
                elapsed_time=time.time()-start_time
                total_upgrade_time = int(elapsed_time/60)

                # GETTING ACTIVE IMAGE ON TESTBED
                current_image = cs.rtr.mgmt1.execute('show install active summary | ex CSC')
                # GETTING RELEASE NUMBER EXAMPLE : 6.2.1.34I
                cur_image = re.search(r'(\d+\.\d+\.\d+).(\d+)(\w+)', current_image)

                # GET PIES THAT WERE LOADED ON TESTBED
                upgrade_pies = re.findall(r'\w+-(\w+)-', all_images)

                # GET TOTAL SIZE OF PIES INSTALLED
                image_size = get_total_image_size(cs.user_tftp_dir,all_images)

                meritData = {}
                meritData['post_upgrade_image'] = cur_image.group(0)
                meritData['upgrade_time'] = total_upgrade_time
                meritData['upgrade_pies'] = upgrade_pies
                meritData['image_size'] = image_size

                cs.db_insert_data_dict.update(meritData)
                
                log.info('allowing some time for protocols to converge '
                         'before checking ixia traffic stream data')
                time.sleep(120) 

                log.info(banner('Starting Post Traffic Check'))
                
                # CALLING RTR LOGGING FUNCTION
                cur_image, post_upgrade_data_dict = \
                    meritAPI.Report.rtr_log(cs.rtr, traffic_state='post_traffic')

                # SETTING RELEASE VERSION
                release = cur_image.group(1)

                # CALLING PRE TRAFFIC CHECK METHOD
                post_traffic_stream_data = \
                    meritAPI.Traffic_data.traffic_check(cs.ixia, traffic_state='post_traffic')
                    
                # SEND DATA TO LOG
                update_data_dict = \
                    meritAPI.Report.traffic_log(traffic_state='post_traffic', 
                                                traffic_dict=post_traffic_stream_data)

                traffic_score = meritAPI.Report.traffic_score(release, 
                                                              cs.pre_traffic_stream_data, 
                                                              post_traffic_stream_data)

                # GETTING CONFIG AFTER IMAGE UPGRADE AND CHECKING DIFF
                post_upgrade_config = cs.rtr.mgmt1.execute('show run')
                diff_config_output = running_config_checker(cs.pre_upgrade_config, post_upgrade_config)
                diff_config_dict = {}
                diff_config_dict['Config Comparison Diff'] = diff_config_output

                cs.db_insert_data_dict.update(diff_config_dict)
                cs.db_insert_data_dict.update(post_upgrade_data_dict)
                cs.db_insert_data_dict.update(update_data_dict)
                cs.db_insert_data_dict.update(traffic_score)

                log.info('Stopping ixia PSAT will restart')
                cs.ixia.stopTraffic()
                time.sleep(180)

                log.info(banner('Starting PSAT portion of sript'))
            
                # CHECKING PSAT DIRCTORY IF EXISTING PSAT REPORT FILE EXIST
                psat_files_exist = os.popen('ls {}/'.format(cs.ScriptArgs.psat_unzip_output_folder)).read()

                log.info('PSAT Folder {}/ has the following content \n\n{}'.format(cs.ScriptArgs.psat_unzip_output_folder, 
                                                                                   psat_files_exist))

                # CLEANING PSAT DIECTORY
                try:
                    log.info('Cleaning folder {}/ before running psat'.format(cs.ScriptArgs.psat_unzip_output_folder))
                    os.system('rm {}/*'.format(cs.ScriptArgs.psat_unzip_output_folder))
                except:
                    log.info('No file found')

                log.info(banner('Starting PSAT'))
                psat_cmd = 'autoeasy {} -archive_dir {}/'.format(cs.ScriptArgs.psat_job_file, 
                                                                cs.ScriptArgs.psat_unzip_output_folder)

                log.info('running cmd {}'.format(psat_cmd))
                os.system(psat_cmd)

                log.info(banner('Unzipping psat file'))
                os.system('unzip {}/* -d {}/'.format(cs.ScriptArgs.psat_unzip_output_folder, 
                                                   cs.ScriptArgs.psat_unzip_output_folder))

                log.info(banner('calling score function'))
                # CALLING MERIT PSAT SCORE CALU FUNCTION
                psat_data_dict = \
                    meritAPI.Psat_logging.psat_results_to_db(cs.db_insert_data_dict['merit_traffic_score'],
                                                             cs.ScriptArgs.psat_unzip_output_folder)

                # APPEND TO DICT
                cs.db_insert_data_dict.update(psat_data_dict)

                log.info(banner('Clearing PSAT Folder {}/'.format(cs.ScriptArgs.psat_unzip_output_folder)))
                try:
                    os.system('rm {}/*'.format(cs.ScriptArgs.psat_unzip_output_folder))
                except:
                    log.info('No file found')


                # CONNECT TO DB
                db = MongoClient(cs.db_host)
                # CREATE DB CALLED meritDB
                dbName = db[cs.db_name]
                # CREATE A COLLECTION CALLED meritData
                collection_name = dbName[cs.db_collection]

                # PUSH DATA INTO DATABASE
                db_id = collection_name.insert_one(cs.db_insert_data_dict).inserted_id

                log.info('db entry is {}'.format(db_id))

                db.close()
                

    @aetest.cleanup
    def cleanup(self):
        """Testcase cleanup."""
        cs = Common_setup()
        log.info('Matthew your in cleanup')

        log.info(banner('@@@  disconnecting telnet session  @@@'))
        cs.rtr.mgmt1.disconnect()
        cs.rtr.mgmt2.disconnect()


class Common_cleanup(aetest.CommonCleanup):
    """Common Cleanup for Sample Test."""

