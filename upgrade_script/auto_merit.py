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
from collections import defaultdict
from hltapi import Ixia
import itertools
import meritAPI
import pymongo
from pymongo import MongoClient
import yaml

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


def remove_inactive_pies(rtr, os_type):
    """Used to remove inactive images and pies."""

    # REMOVE INACTIVE IMAGES
    try:
        if os_type == 'cXR':
            output = rtr.mgmt1.execute('admin install remove inactive '
                                       'synchronous prompt-level none')
        else:
            output = rtr.mgmt1.execute('install remove inactive all')
    except:
        log.info('@@@ SENT REMOVE INACTIVE PIE COMMAND @@@')

    time.sleep(5)
    

    install_log_num = re.search(r'Install operation (\d+)', output)
    for i in range(4):
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

def check_pam_status(ip_addr, username, password, result=0):
    """Check if Pam is running on eXR router."""

    import pexpect
    import pprint
    # LOGGING INTO ROUTER
    log.info(banner('Pexpect logging into router.'))
    child = pexpect.spawn('telnet {}'.format(ip_addr))
    child.expect ('Username: ')
    child.sendline ('{}'.format(username))
    child.expect ('Password:', timeout=90)
    child.sendline ('{}'.format(password))
    child.expect ('#')
    log.info('Pexpect going to admin prompt.')
    child.sendline('admin')
    child.expect ('#')
    log.info('Pexpect entering calvados shell.')
    child.sendline('run')
    child.expect ('~')
    log.info('Pexpect checking pam directory for statup script.')
    child.sendline('ls -ltr /harddisk:/pam/install/')
    child.expect ('~')
    output = child.before
    # CONVERT TYPE BYTES TO STRING TYPE
    str_output = output.decode('utf-8')
    # CHECK IF PAM RESTART SCRIPT IS FOUND
    for line in str_output.split('\n'):
        log.info(line)

        if 'calv_install_robot.sh' in line:
            status = True

    if status == True:
        log.info(banner('Pass PAM script found calv_install_robot.sh.'))
    else:
        log.warning('Could not find PAM script calv_install_robot.sh in directory')
        result += 1

    # CLEARING PEXPECT BUFFER
    child.before = ''

    child.sendline('/harddisk:/pam/install/calv_install_robot.sh')
    child.expect ('~', timeout= 120)
    output = child.before

    str_output = output.decode('utf-8')
    # CHECK IF PAM RESTART SCRIPT IS FOUND
    for line in str_output.split('\n'):
        log.info(line)

        if 'SUCCESS - setup completes on Calvados' in line:
            status = True

    if status == True:
        log.info('Pam started successfully on eXR node.')
    else:
        log.warning('Pam did not start successfully on eXR node.')
        result += 1

    child.close()
    return result

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
        load_image = ScriptArgs.load_image
    except:
        load_image = None

    try:
        traffic_compare = ScriptArgs.traffic_compare
    except:
        traffic_compare = None

    global no_image_found
    no_image_found = None

    try:
        image_available_date = ScriptArgs.image_available_date
    except:
        image_available_date = None


    # IMPORT YAML FILE ATTRIBUTES
    testbed = loader.load(ScriptArgs.testbed_file)
    rtr = testbed.devices[ScriptArgs.rtr]
    mgmt_ip = rtr.connections.vty_1['ip']
    ixia = testbed.devices.ixia
    tcl_server = testbed.devices.ixia.connections.a.tcl_server
    user_tftp_dir = ScriptArgs.user_tftp_dir

    # IMAGE PATHS PASSED FROM JOB FILE
    base_path = ScriptArgs.base_image_repo
    user_tftp_dir = ScriptArgs.user_tftp_dir
    tftp_ip = ScriptArgs.tftp_ip

    # DATABASE ARGUMENTS
    db_host = ScriptArgs.db_host
    db_name = ScriptArgs.db_name
    db_collection = ScriptArgs.db_collection

    user = rtr.tacacs.username
    passwd = rtr.passwords['line']

    log.info(banner('@@@ ATTEMPTING TO TELNET TO ROUTER {} @@@'.format(rtr)))
    # CONNECTING TO ROUTER VIA VTY LINE
    rtr.connect(via ='vty_1', alias = 'mgmt1')
    rtr.connect(via ='vty_2', alias = 'mgmt2')

    pre_upgrade_config = rtr.mgmt1.execute('show run')
    
    ixia = Ixia()
    ixia.connect(ixnetwork_tcl_server=tcl_server)
    ixia.traffic_control(action='run')
    log.info('Sleeping 3 min to allow traffic to start '
             'if it has not already been started')
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

    db_insert_data_dict.update(update_data_dict)


    # CHECK PLATFORM TYPE 
    platform = rtr.mgmt1.adminexec('show inventory chassis')
    m = re.search(r'Descr: +(NCS\d+|ASR-\d+|"ASR \d+)', platform, re.IGNORECASE)
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

    # REMOVING INACTIVE PIES
    remove_inactive_pies(rtr, os_type)

@aetest.loop(os_type=os_type_list)
class ImageUpgrade(aetest.Testcase):
    """Upgrade image."""

    @aetest.setup
    def setup(self):
        """Testcase setup"""
        # GETTING COMMON_SETUP ATTRIBUTES TO PASS TO TC
        cs = Common_setup()

    @aetest.test
    def upgrade_image(self):

        # GETTING COMMON_SETUP ATTRIBUTES TO PASS TO TC
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

        # GETTING TODAYS DATE
        if cs.image_available_date == None:
            # date = os.popen('date +"%b %d"').read()
            # date = date.strip('\n')
            date = 'Sep 24' # 632 12i
            # date = 'Oct  5' # 632 13i
            # date = 'Oct 12' # 632 14i
        else:
            date = cs.image_available_date

        
        # MAKING LIST OF KNOWN IMAGE REPOS
        repo_archive_list = []
        for num in range(1,4):
            repo_archive = re.sub(r'archive1'.format(num), 'archive{}'.format(num), cs.base_path)
            repo_archive_list.append(repo_archive)

        log.info('checking the following archive repos for '
                 'image {}'.format(repo_archive_list))
        
        # SEARCHING ARCHIVE REPOS FOR EXPECTED IMAGE
        for repo in repo_archive_list:
            command = 'find {} -type d -name "{}*" -ls | grep "{}"'.format(repo, cs.load_image, date)
            command_output = os.popen(command).read()
            log.info(command)
            log.info(command_output + '\n\n')
            
            if cs.load_image != None:
                if cs.load_image in str(command_output):
                    log.info(banner('pass {} image found in archive : {}'.format(cs.load_image, repo)))
                    cmd = '''ls -ltr {} | grep "{}"'''.format(repo, date)
                    output = os.popen(cmd).read()
                    log.info('cmd output for date {}: \n{}'.format(date, output))
                    # CHANGE BASE PATH TO REPO WHERE IMAGE WAS FOUND
                    cs.base_path = repo
                    break
                else:
                    log.warning('image not found in : {}'.format(repo))
            else:
                log.info('As user did not specify what image to upgrade \n'
                         'image will upgrade to the following release {} as that is \n'
                         'the current active image installed on the router.\n'
                         .format(cur_image.group(1)))

                if cur_image.group(1) in str(command_output):
                    log.info(banner('pass {} image found in archive : {}'.format(cur_image.group(1), repo)))
                    cmd = '''ls -ltr {} | grep "{}"'''.format(repo, date)
                    output = os.popen(cmd).read()
                    log.info('cmd output for date {}: \n{}'.format(date, output))
                    # CHANGE BASE PATH TO REPO WHERE IMAGE WAS FOUND
                    cs.base_path = repo
                    break
                else:
                    log.warning('image not found in : {}'.format(repo))

        # MATCHING FOLDER IN BASE PATH : EXAMPLE 6.2.1.34I.SIT_IMAGE
        num_of_folders = re.findall(r'\d+\.\d+\.\d+\.\d+I\.\w+', str(output))
        num_tftp_folders = len(num_of_folders)
        
        try:
            # SELECT IMAGE PASSED FROM JOB FILE FROM USER
            if cs.load_image is not None:
                log.info('NOTICE: User has selected to upgrade from {} '
                         'to {}'.format(cur_image.group(0), cs.load_image))

                for item in num_of_folders:
                    if re.search(r'{}'.format(cs.load_image), item) is not None:
                        upgrade_folder = item
                        log.info('image upgrade_folder: {}'.format(upgrade_folder))
            else:
                # WILL CONTINUE TO LOAD CURRENTLY ACTIVE RELEASE
                # 6.2.1 34I -> 6.2.1 35I
                if num_tftp_folders > 1:
                    log.info('NOTICE: There is currently more than one image availabe for {} '
                             'the images are {} checking testbed for current installed image '
                             'testbed is current loaded with {}'
                           .format(date,num_of_folders, cur_image.group(0)))

                    for item in num_of_folders:
                        if cur_image.group(1) in item:
                            log.info('found image {}'.format(item))
                            upgrade_folder = item
                else:
                    mo = re.search(r'\d+\.\d+\.\d+\.\d+I\.\w+', str(output))
                    upgrade_folder = mo.group(0)

            output = os.popen('ls -ltr {}{}'.format(cs.base_path, upgrade_folder)).read()
            path = '{}{}'.format(cs.base_path, upgrade_folder)
            log.info('image path found: {}'.format(path))
        except:
            output = 'None'
            log.info('Today: {} no image is seen in repo.'.format(date))


        # CHECKING IF ASR9K OR NCS5500 IMAGE IS AVAILABE IN FOLDER
        if 'asr9k-px' in output or 'asr9k-x64' in output or 'ncs5500' in output:
            log.info(banner('{} image found'.format(cs.platform_type)))
            start_time=time.time() # TAKING CURRENT TIME AS STARTING TIME
            if cs.os_type == 'cXR':
                os_type_image = path + '/asr9k-px'
            elif cs.os_type == 'eXR' and cs.platform_type == 'asr9k':
                os_type_image = path + '/asr9k-x64'
            elif cs.os_type == 'eXR' and cs.platform_type == 'ncs':
                os_type_image = path + '/ncs5500'


            output = os.popen('ls {}'.format(os_type_image)).read()
            log.info(output)

            if cs.os_type == 'cXR':
                images = re.findall(r'asr9k-\w+-px.pie-\d+\.\d+\.\d+.\d+\w+.*|'
                         'asr9k-asr\w+-\w+-\w+\.\w+-\d+\.\d+\.\d+\.\d+\w+|'
                         'asr9k-\w+-infra-\w+.\w+-\d+.\d+.\d+.\d+\w+|'
                         'asr9k-\w+-nV-\w+.\w+-\d+.\d+.\d+.\d+\w+',str(output))
            else:
                images = re.findall(r'{}-\w+.*'.format(platform_match), str(output))

            log.info(banner('images active on router = {}'.format(current_image_pies)))

            all_images = ''
            global all_images_list
            all_images_list = []
            for item in images:
                for cur_pie in current_image_pies:
                    # ONLY GETTING THE PIES THAT ARE ACTIVE ON TESTBED
                    if cur_pie in item and 'V2' not in item and '99' not in item:
                        copy_cmd =  'cp' + ' ' + os_type_image + '/' + item + ' ' + '{}'.format(cs.user_tftp_dir)
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
                       'synchronous activate prompt-level none'
                       .format(cs.tftp_ip, cs.user_tftp_dir, all_images))
            else:
                cmd = ('install add source tftp://{}{} {} '
                       .format(cs.tftp_ip, cs.user_tftp_dir, all_images))

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
            ixia2 = Ixia()
            ixia2.connect(ixnetwork_tcl_server=cs.tcl_server)
            
            # CALLING RTR LOGGING FUNCTION
            cur_image, post_upgrade_data_dict = \
                meritAPI.Report.rtr_log(cs.rtr, traffic_state='post_traffic')

            # SETTING RELEASE VERSION
            release = cur_image.group(1)

            # CALLING PRE TRAFFIC CHECK METHOD
            post_traffic_stream_data = \
                meritAPI.Traffic_data.traffic_check(ixia2, traffic_state='post_traffic')
                
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

            ixia2.traffic_control(action='stop')
            log.info('Stopping ixia PSAT will restart')
            time.sleep(180)
            
            # CLEANING COPIED IMAGES OUT OF USER TFTP DIRECTORY
            log.info(banner('Cleaning images out of users tftp folder: {}'.format(cs.user_tftp_dir)))
            for images in all_images.split():
                command = 'rm {}{}'.format(cs.user_tftp_dir, images)
                log.info('Removing the following: {}'.format(command))
                try:
                    os.system(command)
                except:
                    log.info('Image not found {}'.format(command))

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

        else:
            global no_image_found
            no_image_found = True
            log.info('@@@ NO IMAGE FOUND FOR TODAY {} SETTING FLAG TO {} @@@'
                     .format(date, no_image_found))

    @aetest.cleanup
    def cleanup(self):
        """Testcase cleanup."""
        # GETTING COMMON_SETUP ATTRIBUTES TO PASS TO TC
        cs = Common_setup()


class Common_cleanup(aetest.CommonCleanup):
    """Common Cleanup for Sample Test."""

    cs = Common_setup()

    @aetest.skipIf(cs.os_type == 'cXR', reason = 'OS type cXR not supported '
                                                 'currently.')
    @aetest.subsection
    def start_pam(self):
        """USED TO CHECK IF PAM IS INSTALLED AND RE-ENABLE AFTER IMAGE UPGRADE."""

        cs = Common_setup()
        if no_image_found  == True:
            log.info('Not running PAM setup as there is no new image.')
        else:
            log.info(banner('inside: os type = {} and no_image_found = {}'.format(cs.os_type, no_image_found)))

            pam_status = check_pam_status(cs.mgmt_ip, cs.user, cs.passwd)

            if pam_status != 0:
                self.failed('PAM did not start successful.')

    @aetest.subsection
    def clean_user_repo(self):
        """Used to delete images that were just installed on router."""
        log.info(banner('Clearing copied images out of user repo.'))
        cs = Common_setup()

        if no_image_found != None:
            for item in all_images_list:
                cmd = 'rm {}{}'.format(cs.user_tftp_dir, item)
                output = os.popen(cmd).read()
                log.info(cmd)

    @aetest.subsection
    def disconnect_telnet_sessions(self):
        """Used to check if PAM is installed and re-enable after image upgrade."""
        cs = Common_setup()
        log.info(banner('@@@  disconnecting telnet session  @@@'))
        cs.rtr.mgmt1.disconnect()
        cs.rtr.mgmt2.disconnect()
