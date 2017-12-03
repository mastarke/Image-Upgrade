from flask import (Flask, render_template, flash, redirect,
                   url_for, session, logging, request, g)
from flask_pymongo import PyMongo
import pymongo
from collections import OrderedDict
import re
from bson import ObjectId
import os
from celery import Celery
from Flask_celery import make_celery
from celery.result import AsyncResult
from celery.utils.log import get_task_logger
import uuid
import datetime
import sys
sys.path.insert(0, '/ws/mastarke-sjc/my_local_git/image_picker_site/api_files')
from IxNetRest import *
import meritAPI 



app = Flask(__name__)


app.config['MONGO_HOST'] = 'mastarke-lnx-v2'
app.config['MONGO_DBNAME'] = 'meritDB'


# CELERY ARGUMENTS
app.config['CELERY_BROKER_URL'] = 'amqp://localhost//'
app.config['CELERY_RESULT_BACKEND'] = 'mongodb://mastarke-lnx-v1:27017/meritDB'


app.config['CELERY_RESULT_BACKEND'] = 'mongodb'
app.config['CELERY_MONGODB_BACKEND_SETTINGS'] = {
    "host": "mastarke-lnx-v2",
    "port": 27017,
    "database": "meritDB", 
    "taskmeta_collection": "flask_app_job_results",
}

app.config['CELERY_TASK_SERIALIZER'] = 'json'

#Specify mongodb host and datababse to connect to
celery = Celery('task',broker='mongodb://mastarke-lnx-v1:27017/jobs')

#Loads settings for Backend to store results of jobs 
# celery.config_from_object('celeryconfig')
celery = make_celery(app)

# LOGGER IS FOR CELERY TASK LOGGING
logger = get_task_logger(__name__)

app.selected_collection = None


# INIT MONGODB
mongo = PyMongo(app)

def get_chart_data(db_coll, os_type):
    """Used to query data to fill in chart"""

    traffic_score_data = mongo.db[db_coll].find({'os_type':os_type}, {'merit_traffic_score':1,
                                                                      '_id':0}).sort('date',pymongo.ASCENDING)

    date_data = mongo.db[db_coll].find({'os_type':os_type}, {'date':1,
                                                              '_id':0}).sort('date',pymongo.ASCENDING)

    psat_score_data = mongo.db[db_coll].find({'os_type':os_type}, {'psat_score':1,
                                                                    '_id':0}).sort('date',pymongo.ASCENDING)

    final_score_data = mongo.db[db_coll].find({'os_type':os_type}, {'merit_final_score':1,
                                                                     '_id':0}).sort('date',pymongo.ASCENDING)

    upgrade_time_data = mongo.db[db_coll].find({'os_type':os_type}, {'upgrade_time':1,
                                                                      '_id':0}).sort('date',pymongo.ASCENDING)

    image_size_data = mongo.db[db_coll].find({'os_type':os_type}, {'image_size':1,
                                                                      '_id':0}).sort('date',pymongo.ASCENDING)

    traffic_score = []
    for r in traffic_score_data:
        try:
            traffic_score.append(r['merit_traffic_score'])
        except:
            app.logger.info('traffic_score key value not found in mongoDB')

    date = []
    for r in date_data:
        try:
            date.append(r['date'])
        except:
            app.logger.info('date key value not found in mongoDB')

    psat_score = []
    for r in psat_score_data:
        try:
            psat_score.append(r['psat_score'])
        except:
            app.logger.info('psat_score key value not found in mongoDB')

    final_score = []
    for r in final_score_data:
        try:
            final_score.append(r['merit_final_score'])
        except:
            app.logger.info('final_score key value not found in mongoDB')


    upgrade_time = []
    for r in upgrade_time_data:
        try:
            upgrade_time.append(r['upgrade_time'])
        except:
            app.logger.info('upgrade_time key value not found in mongoDB')

    image_size = []
    for r in image_size_data:
        try:
            image_size.append(r['image_size'])
        except:
            app.logger.info('image_size key value not found in mongoDB')


    return traffic_score, date, psat_score, final_score, upgrade_time, image_size


def get_query_chart_data(rsp_select, lc_select, os_type, db_coll, startDay, endDay):
    # GET QUERY DATES

    date_data = (mongo.db[db_coll].find({"$and": [{ 'RSP Type':{ "$in":  rsp_select  }},
                                                  { 'LC Type': { "$in":  lc_select  }},
                                                  {'os_type':{ "$in":  os_type  }},
                                                  {'date': {"$gte": startDay, "$lt": endDay}}]}, {'date':1, '_id':0})).sort('date',pymongo.ASCENDING)

    # GET TRAFFIC SCORE FROM DB
    traffic_score_data = (mongo.db[db_coll].find({"$and": [{ 'RSP Type':{ "$in":  rsp_select  }},
                                                   { 'LC Type': { "$in":  lc_select  }},
                                                   {'os_type':{ "$in":  os_type  }} ,
                                                   {'date': {"$gte": startDay, "$lt": endDay}}]}, {'merit_traffic_score':1, '_id':0})).sort('date',pymongo.ASCENDING)

    # GET TRIGGER SCORE FROM DB
    psat_score_data = (mongo.db[db_coll].find({"$and": [{ 'RSP Type':{ "$in":  rsp_select  }},
                                                        { 'LC Type': { "$in": lc_select  }},
                                                        {'os_type':{ "$in":  os_type  }}, 
                                                        {'date': {"$gte": startDay, "$lt": endDay}}]}, {'psat_score':1, '_id':0})).sort('date',pymongo.ASCENDING)

    # GET MERIT SCORE / FINAL SCORE FROM DB
    final_score_data = (mongo.db[db_coll].find({"$and": [{ 'RSP Type':{ "$in":  rsp_select  }},
                                                   { 'LC Type': { "$in":  lc_select  }},
                                                   {'os_type':{ "$in":  os_type  }}, 
                                                   {'date': {"$gte": startDay, "$lt": endDay}}]}, {'merit_final_score':1, '_id':0})).sort('date',pymongo.ASCENDING)

    # GET COUNT OF MATCHES FOUND
    query_result_count = (mongo.db[db_coll].find({"$and": [{ 'RSP Type':{ "$in":  rsp_select  }},
                                                            { 'LC Type': { "$in": lc_select }},
                                                            {'os_type':  { "$in":  os_type  }},
                                                            {'date': {"$gte": startDay, "$lt": endDay}}], 'merit_final_score':{ "$gt":0,"$lt":100}
                                                  })).count()

    score_date = []
    for r in date_data:
        try:
            score_date.append(r['date'])
        except:
            app.logger.info('date key value not found in mongoDB')

    traffic_score = []
    for r in traffic_score_data:
        try:
            traffic_score.append(r['merit_traffic_score'])
        except:
            app.logger.info('traffic_score key value not found in mongoDB')

    psat_score = []
    for r in psat_score_data:
        try:
            psat_score.append(r['psat_score'])
        except:
            app.logger.info('traffic_score key value not found in mongoDB')

    final_score = []
    for r in final_score_data:
        try:
            final_score.append(r['merit_final_score'])
        except:
            app.logger.info('traffic_score key value not found in mongoDB')


    return score_date, traffic_score, psat_score, \
           final_score, query_result_count


def get_db_collection():
    coll_name = mongo.db.collection_names()

    return coll_name

def get_rp_lc_hw_types(db_coll):


    # FIND UNIQUE LC AND RSP MATCHES IN DB
    lc_types = mongo.db[db_coll].find().distinct("LC Type")
    rsp_types = mongo.db[db_coll].find().distinct("RSP Type")
    os_types_in_db = mongo.db[db_coll].find().distinct("os_type")

    return lc_types, rsp_types, os_types_in_db,



def dynamic_yaml(hostname, mgmt_ip, rtr_username, rtr_password):
    yaml_file = {
                    "testbed": {
                        "name": "noname",
                        "servers": {
                            "tftp": {
                                "address": "223.255.254.245",
                                "custom": {
                                    "rootdir": "/auto/tftpboot/mastarke"
                                },
                                "server": "sj20lab-tftp4"
                            }
                        }
                    },
                    "devices": {
                        hostname: {
                            "type": "asr9k-x64",
                            "connections": {
                                "a": {
                                    "ip": "172.27.151.15",
                                    "port": "2016",
                                    "protocol": "telnet"
                                },
                                "vty_1": {
                                    "protocol": "telnet",
                                    "ip": mgmt_ip
                                },
                                "vty_2": {
                                    "protocol": "telnet",
                                    "ip": mgmt_ip
                                }
                            },
                            "tacacs": {
                                "login_prompt": "Username:",
                                "password_prompt": "Password:",
                                "username": rtr_username
                            },
                            "passwords": {
                                "tacacs": rtr_password,
                                "enable": rtr_password,
                                "line": rtr_password
                            }
                        },
                        "ixia": {
                            "type": "ixia",
                            "connections": {
                                "a": {
                                    "protocol": "ixia",
                                    "ip": "172.27.152.13",
                                    "tcl_server": "172.27.211.87:8009",
                                    "username": "ciscoUser"
                                }
                            }
                        }
                    }
                }

    return yaml_file

def install_image(ip_addr, username, password, get_install_active=True):
    """CHECK INSTALLED ACTIVE IMAGES ON ROUTER."""

    if get_install_active == True:
        cmd = 'show install active summary'
    else:
        cmd = 'show install committed summary'


    import pexpect
    try:
        # LOGGING INTO ROUTER
        print('Pexpect logging into router.')
        child = pexpect.spawn('telnet {}'.format(ip_addr))
        child.expect ('Username: ')
        child.sendline ('{}'.format(username))
        child.expect ('Password:', timeout=90)
        child.sendline ('{}'.format(password))
        child.expect ('#')
        print('Pexpect sending command.')
        child.sendline(cmd)
        child.expect ('#')

        output = child.before
        # CONVERT TYPE BYTES TO STRING TYPE
        str_output = output.decode('utf-8')
        
        for line in str_output.split('\n'):
            print(line)

        child.close()
    except:
        str_output = ('Pexpect failed to telnet to router. Please ensure VTY '
                     'line is enabled on your router')
    
    return str_output

def rtr_os_type(ip_addr, username, password, result=0):
    """CHECK ROUTER OS TYPE."""

    import pexpect
    import pprint
    # LOGGING INTO ROUTER
    print('Pexpect logging into router.')
    child = pexpect.spawn('telnet {}'.format(ip_addr))
    child.expect ('Username: ')
    child.sendline ('{}'.format(username))
    child.expect ('Password:', timeout=90)
    child.sendline ('{}'.format(password))
    child.expect ('#')
    print('Pexpect going to admin prompt.')
    child.sendline('bash -c uname -a')
    child.expect ('#')

    output = child.before
    # CONVERT TYPE BYTES TO STRING TYPE
    str_output = output.decode('utf-8')
    
    for line in str_output.split('\n'):
        print(line)

    child.close()

    if 'Linux' in str_output:
        print('OS TYPE IS eXR')
        os_type = 'eXR'
    else:
        print('OS TYPE IS cXR')
        os_type = 'cXR'
    
    return os_type
        
# INDEX
@app.route('/', methods=['GET', 'POST'])
def index():
    
    return render_template('index.html', image=image)


# ABOUT
@app.route('/about', methods=['GET', 'POST'])
def about():

    return render_template('about.html')

# UPGRADE WITH SCORE
@app.route('/image_with_score', methods=['GET', 'POST'])
def image_with_score():

    session['get_score'] = True

    command = ('ls /auto/prod_weekly_archive1/bin/  '
               '/auto/prod_weekly_archive2/bin/  '
               '/auto/prod_weekly_archive3/bin/')

    command_output = os.popen(command).read()

    matchObj = re.findall(r'\d+.\d+.\d+.\d+I.*', command_output)
    cur_releases = list(set(matchObj))

    return render_template('image_with_score.html', cur_releases=cur_releases)


# IMAGE
@app.route('/image', methods=['GET', 'POST'])
def image():

    session['get_score'] = False

    command = ('ls /auto/prod_weekly_archive1/bin/  '
               '/auto/prod_weekly_archive2/bin/  '
               '/auto/prod_weekly_archive3/bin/')

    command_output = os.popen(command).read()

    matchObj = re.findall(r'\d+.\d+.\d+.\d+I.*', command_output)
    cur_releases = list(set(matchObj))

    return render_template('image.html', cur_releases=cur_releases)


@app.route('/packages', methods=['GET', 'POST'])
def packages():

    try:

        get_score = session.get('get_score', None)

        ixia_connection = None
        ixia_chassis_ip = None
        install_active_output = None
        install_commited_output = None
        os_type = None

        if request.method == 'POST':
            image = request.form['image']
            platform = request.form['platform']
            tftp_dir = request.form['tftp_dir']
            tftp_server_ip = request.form['tftp_server_ip']
            rtr_mgmt_ip = request.form['rtr_mgmt_ip']
            rtr_hostname = request.form['rtr_hostname']
            rtr_username = request.form['rtr_username']
            rtr_password = request.form['rtr_password']
        
            session['platform'] = platform
            session['tftp_dir'] = tftp_dir
            session['tftp_server_ip'] = tftp_server_ip
            session['rtr_mgmt_ip'] = rtr_mgmt_ip
            session['rtr_hostname'] = rtr_hostname
            session['rtr_username'] = rtr_username
            session['rtr_password'] = rtr_password

            # ATTEMPT TO PING DEVICE 
            ping_output = os.popen('ping {} -c 5'.format(rtr_mgmt_ip)).read()
            ping_success_num = re.search(r'\d+ packets transmitted, +\d+ received, +(\d+)% packet loss', ping_output)
            if int(ping_success_num.group(1)) <= 21:
                ping_result = True
            else:
                app.logger.info('Matthew ping result was not good it was {}'.format(ping_success_num.group(1)))
                ping_result = False

            session['ping_result'] = ping_result

            app.logger.info('Matthew ping result is {}'.format(ping_result))

            if ping_result == True:
                
                # GET THE INSTALLED ACTIVE IMAGE ON THE ROUTER
                install_active_output = install_image(rtr_mgmt_ip, rtr_username, rtr_password)
                # GET THE INSALLED COMMITED IMAGE ON THE ROUTER
                install_commited_output = install_image(rtr_mgmt_ip, rtr_username, rtr_password, False)
               
                command = ('ls /auto/prod_weekly_archive1/bin/{image}/{platform}  '
                             '/auto/prod_weekly_archive2/bin/{image}/{platform}  '
                             '/auto/prod_weekly_archive3/bin/{image}/{platform}'.format(image=image, platform=platform))
                
                command_output = os.popen(command).read()

                dir_found = re.search(r'\/\w+\/\w+\/\w+\/.*', command_output)
                path = re.sub(r':', '', dir_found.group(0))
                image_repo = path
                
                session['image_repo'] = image_repo

                packages = re.sub(r'\/\w+\/\w+\/\w+\/.*', '', command_output)
                pies = re.findall(r'\w+.*', packages)
                
                # GETTING OS TYPE ON ROUTER
                os_type = rtr_os_type(rtr_mgmt_ip, rtr_username, rtr_password)
                app.logger.info('Matthe pexpect found router os_type as {}'.format(os_type))

                if request.method == 'POST' and get_score == True:
                    app.logger.info('upgrade with score')
                    ixia_chassis_ip = request.form['ixia_chassis_ip']
                    db_collection = request.form['db_collection']
                    psat_job_file = request.form['psat_job_file']
                    psat_unzip_output_folder = request.form['psat_unzip_output_folder']

                    session['ixia_chassis_ip'] = ixia_chassis_ip
                    session['db_collection'] = db_collection
                    session['psat_job_file'] = psat_job_file
                    session['psat_unzip_output_folder'] = psat_unzip_output_folder

                    app.logger.info('Matthew ixia_chassis_ip is {} db_collection is {} psat_job_file is {} psat_unzip_output_folder is {} '.format(ixia_chassis_ip, db_collection, psat_job_file, psat_unzip_output_folder))

                    try:
                        ixia = IxNetRestMain(ixia_chassis_ip, '11009')
                        ixia_connection = True
                    except:
                        ixia_connection = False

        return render_template('packages.html',  ping_result=ping_result, rtr_mgmt_ip=rtr_mgmt_ip, 
                                                 install_active_output=install_active_output, 
                                                 install_commited_output=install_commited_output,
                                                 ixia_connection=ixia_connection, 
                                                 ixia_chassis_ip=ixia_chassis_ip, os_type=os_type, 
                                                 image=image, platform=platform)
    except:
        return render_template('404.html'), 404


@app.route('/copycmd', methods=['GET', 'POST'])
def copycmd():

    
    ping_result = session.get('ping_result', None)
    rtr_mgmt_ip = session.get('rtr_mgmt_ip', None)
    
    
    return render_template('copycmd.html',  ping_result=ping_result, rtr_mgmt_ip=rtr_mgmt_ip)


@app.route('/install_on_rtr', methods=['GET', 'POST'])
def install_on_rtr():

    get_score = session.get('get_score', None)

    rtr_mgmt_ip = session.get('rtr_mgmt_ip', None)
    ping_result = session.get('ping_result', None)
    rtr_username = session.get('rtr_username', None)
    rtr_password = session.get('rtr_password', None)
    rtr_hostname = session.get('rtr_hostname', None)
    platform = session.get('platform', None)
    image_repo = session.get('image_repo', None)
    tftp_dir = session.get('tftp_dir', None)
    tftp_server_ip = session.get('tftp_server_ip', None)


    ixia_chassis_ip = session.get('ixia_chassis_ip', None)
    db_collection = session.get('db_collection', None)
    psat_job_file = session.get('psat_job_file', None)
    psat_unzip_output_folder = session.get('psat_unzip_output_folder', None)
    

    if request.method == 'POST':
        install_on_rtr = request.form['install_on_rtr']
        
        result = script_runner.delay(rtr_hostname, rtr_mgmt_ip, rtr_username, 
                                     rtr_password, platform, image_repo, tftp_dir, 
                                     tftp_server_ip, db_collection, psat_unzip_output_folder,
                                     psat_job_file, ixia_chassis_ip, get_score)

        job_taskid = AsyncResult(result.task_id)
        mongo.db.job_task_id.insert({'taskid': str(job_taskid), 
                                     'jobname':'Upgrade host ' + rtr_hostname + ' Mgmt ' + rtr_mgmt_ip + ' Chassis ' + platform, 
                                     'date':datetime.datetime.now().strftime("%m-%d-%y")})


    return render_template('install_on_rtr.html', ping_result=0, job_taskid=str(job_taskid))



@app.route('/upgrade_jobs_AsyncResult', methods=['GET', 'POST'])
def upgrade_jobs_AsyncResult():


    # GET ALL TASK ID'S 
    taskid_list_data = mongo.db.job_task_id.find({}, {'taskid':1,'_id':0}).sort('date',pymongo.DESCENDING)
    taskdate_list_data = mongo.db.job_task_id.find({}, {'date':1,'_id':0}).sort('date',pymongo.DESCENDING)
    jobname_list_data = mongo.db.job_task_id.find({}, {'jobname':1,'_id':0}).sort('date',pymongo.DESCENDING)

    # UNPACK TASKID CURSOR OBJECT
    taskid_list = []
    for r in taskid_list_data:
        try:
            taskid_list.append(r['taskid'])
        except:
            app.logger.info('taskid key value not found in mongoDB')

    app.logger.info('matthew taskid_list is {}'.format(taskid_list))

    
    # PASS TASK ID TO ASYNC RESULT TO GET TASK RESULT FOR THAT SPECIFIC TASK
    task_state_list = []
    for item in taskid_list:
        try:
            task_state_list.append(script_runner.AsyncResult(item).state)
        except:
            task_state_list.append('UNKNOWN')
        
    # UNPACK DATE CURSOR OBJECT
    date_list = []
    for r in taskdate_list_data:
        try:
            date_list.append(r['date'])
        except:
            app.logger.info('date key value not found in mongoDB')


    # UNPACK jobname CURSOR OBJECT
    jobname_list = []
    for r in jobname_list_data:
        try:
            jobname_list.append(r['jobname'])
        except:
            app.logger.info('date key value not found in mongoDB')

    return render_template('upgrade_jobs_AsyncResult.html', data_list=zip(taskid_list, 
                                                                          task_state_list, 
                                                                          date_list, jobname_list))


@app.route('/job_file_builder', methods=['GET', 'POST'])
def job_file_builder():

    copy_error = None

    if request.method == 'POST':

        yaml_file_loc = request.form['yaml_file_loc']
        host_name = request.form['host_name']
        tftp_dir = request.form['tftp_dir']
        tftp_ip = request.form['tftp_ip']
        load_image = request.form['load_image']
        db_name = request.form['db_name']
        psat_unzip_loc = request.form['psat_unzip_loc']
        psat_job_file_loc = request.form['psat_job_file_loc']
        job_file_name = request.form['job_file_name']

        app.logger.info('Matthew the yaml file location is {}'.format(yaml_file_loc))
        
        job_file = '''
from ats.easypy import run

class ScriptArgs(object):
    """script related arguments"""
    testbed_file = ('/ws/mastarke-sjc/my_local_git/merit/my_yaml.yaml')
    rtr = '{}'
    base_image_repo = '/auto/prod_weekly_archive1/bin/'
    user_tftp_dir = '{}'
    tftp_ip = '{}'
    load_image = '{}'
    image_available_date = 'Oct  5' # 632 13I IMAGE AVAILABLE DATE

    ### DATABASE ARGS ###
    db_host = 'mastarke-lnx-v2'
    db_name = 'meritDB'
    db_collection = '{}'

    ### PSAT ARGS ###
    psat_unzip_output_folder = '{}'
    psat_job_file = '{}'

def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/merit/auto_merit.py'))
    '''.format(yaml_file_loc, host_name, tftp_dir, tftp_ip, 
              load_image, db_name, psat_unzip_loc, psat_job_file_loc)
        
        try:
            with open("{}{}".format(tftp_dir,job_file_name), "w") as fh:
                fh.write(job_file)
                fh.close()
        except:
            copy_error = True

    return render_template('job_file_builder.html', copy_error=copy_error)


@app.route('/yaml_file_builder', methods=['GET', 'POST'])
def yaml_file_builder():

    copy_error = None

    if request.method == 'POST':

        rtr_name = request.form['rtr_name']
        console_ip = request.form['console_ip']
        console_port = request.form['console_port']
        mgmt_ip = request.form['mgmt_ip']
        rtr_username = request.form['rtr_username']
        rtr_password = request.form['rtr_password']
        ixia_chassis_ip = request.form['ixia_chassis_ip']
        ixia_vm_tcl_server_ip = request.form['ixia_vm_tcl_server_ip']
        yaml_file_name = request.form['yaml_file_name']
        tftp_loc = request.form['tftp_loc']

        yaml_file = '''
testbed:
    name: noname
    servers:
        tftp:
            address: 223.255.254.245
            custom:
                rootdir: /auto/tftpboot/mastarke
            server: sj20lab-tftp4
devices:
    {rtr_name}:
        type: 'asr9k-x64'
        connections:
            a:
                ip: {console_ip}
                port: {console_port}
                protocol: telnet
            vty_1:
                protocol : telnet
                ip : "{mgmt_ip}"
            vty_2:
                protocol : telnet
                ip : "{mgmt_ip}"
        tacacs:
            login_prompt: "Username:"
            password_prompt: "Password:"
            username: "{rtr_username}"
        passwords:
            tacacs: {rtr_password}
            enable: {rtr_password}
            line: {rtr_password}
    ixia:
        type: ixia
        connections:
            a:
                protocol: ixia
                ip: {ixia_chassis_ip}
                tcl_server: {ixia_vm_tcl_server_ip}:8009
                username: ciscoUser
    '''.format(rtr_name=rtr_name,console_ip=console_ip, console_port=console_port,
               mgmt_ip=mgmt_ip, rtr_username=rtr_username, rtr_password=rtr_password,
               ixia_chassis_ip=ixia_chassis_ip, ixia_vm_tcl_server_ip=ixia_vm_tcl_server_ip)
        try:
            with open("{}{}".format(tftp_loc,yaml_file_name), "w") as fh:
                fh.write(yaml_file)
                fh.close()
        except:
            copy_error = True


    return render_template('yaml_file_builder.html', copy_error=copy_error)


# DB_SELECTED
@app.route('/db_selected', methods=['GET', 'POST'])
def db_selected():

    coll_name = get_db_collection()

    if request.method == 'POST':
        selected_collection = request.form['Item_4']
        app.selected_collection = selected_collection

    return render_template('db_selected.html', 
                           coll_name=coll_name,
                           selected_collection=app.selected_collection)


@app.route('/cxr_image_upgrade/', methods=['GET', 'POST'])
def cxr_image_upgrade():

    if app.selected_collection == None:
        return redirect(url_for('db_selected'))
    else:
        lc_types, rsp_types, os_types_in_db = \
            get_rp_lc_hw_types(app.selected_collection)
        
        # CALLING DATABASE TO GET DATA FROM MONGODB
        traffic_score, score_date, psat_score, final_score, \
            upgrade_time, image_size = get_chart_data(app.selected_collection, 
                                                      os_type='cXR')

        return render_template("image_upgrade_score.html",
                                traffic_score=traffic_score,
                                score_date=score_date,
                                psat_score=psat_score,
                                final_score=final_score,
                                upgrade_time=upgrade_time,
                                os_type='cXR',
                                image_size=image_size,
                                lc_types=lc_types,
                                rsp_types=rsp_types,
                                os_types_in_db=os_types_in_db,
                                db_coll=app.selected_collection)


@app.route('/exr_image_upgrade/', methods=['GET', 'POST'])
def exr_image_upgrade():

    if app.selected_collection == None:
        return redirect(url_for('db_selected'))

    # coll_name = get_db_collection()
    lc_types, rsp_types, os_types_in_db = get_rp_lc_hw_types(app.selected_collection)
    
    # CALLING DATABASE TO GET DATA FROM MONGODB
    traffic_score, score_date, psat_score, final_score, \
        upgrade_time, image_size = get_chart_data(app.selected_collection, os_type='eXR')

    return render_template("image_upgrade_score.html",
                            traffic_score=traffic_score,
                            score_date=score_date,
                            psat_score=psat_score,
                            final_score=final_score,
                            upgrade_time=upgrade_time,
                            os_type='eXR',
                            image_size=image_size,
                            lc_types=lc_types,
                            rsp_types=rsp_types,
                            os_types_in_db=os_types_in_db)

@app.route('/result/', methods=['POST'])
def result():

   
    if request.method == 'POST':

        rsp_select = request.form.getlist('Item_1')
        lc_select = request.form.getlist('Item_2')
        os_type = request.form.getlist('Item_3')
        date_input = request.form['daterange']
        db_coll = app.selected_collection

        # 06-10-2017 - 06-29-2017
        match = re.findall(r'\d+-\d+-\d+',date_input)
        startDay = match[0]
        endDay = match[1]

        # GETTING DB QUERY INFO
        score_date, traffic_score, psat_score, final_score, \
            query_result_count = get_query_chart_data(rsp_select, lc_select, os_type,
                                                      db_coll, startDay, endDay)

        return render_template("result.html", rsp_select=rsp_select,
                                              lc_select=lc_select,
                                              query_result_count=query_result_count,
                                              score_date=score_date,
                                              traffic_score=traffic_score,
                                              psat_score=psat_score,
                                              final_score=final_score,
                                              os_type=os_type,
                                              db_coll=db_coll,
                                              startDay=startDay,
                                              endDay=endDay)

@app.route('/merit_table/<string:tableDate>/<string:os_type>/<int:pageNum>', methods=['GET', 'POST'])
def merit_table(tableDate, os_type, pageNum=0):

    ids_list = []
    for itm in mongo.db[app.selected_collection].find({"date":tableDate, 'os_type':os_type}):
        ids_list.append(itm.get('_id'))
    
    singleId = ids_list[pageNum]
    tbl_data = mongo.db[app.selected_collection].find_one({'_id':ids_list[pageNum]})
    itemCount = mongo.db[app.selected_collection].find({'date':tableDate, 'os_type':os_type}).count()
    
    tableData = OrderedDict([])

    # DATE OF TABLE CREATION
    try:
        tableData['Run Date'] = tbl_data['date']
    except:
        app.logger.info('Run Date not found')

    # DATE OF TABLE CREATION
    try:
        tableData['Hostname'] = tbl_data['hostname']
    except:
        app.logger.info('hostname not found')

    # TESTBED DATA
    try:
        tableData['Chassis'] = tbl_data['chassis']
    except:
        app.logger.info('Chassis not found')

    try:
        tableData['RSP Type'] = tbl_data['RSP Type']
    except:
        app.logger.info('RSP not found')

    try:
        tableData['LC Type'] = tbl_data['LC Type']
    except:
        app.logger.info('LC Type not found')

    try:
        tableData['OS Type'] = tbl_data['os_type']
    except:
        app.logger.info('OS Type not found')

    try:
        tableData['Pre Upgrade Image'] = tbl_data['pre_upgrade_image']
    except:
        app.logger.info('Pre Upgrade Image not found')

    try:
        tableData['Post Upgrade Image'] = tbl_data['post_upgrade_image']
    except:
        app.logger.info('Post Upgrade Image not found')

    try:
        tableData['Minutes Upgrading'] = tbl_data['upgrade_time']
    except:
        app.logger.info('Minutes Upgrading not found')

    try:
        tableData['Pies Installed'] = tbl_data['upgrade_pies']
    except:
        app.logger.info('Pies Installed not found')

    try:
        if ' ' in tbl_data['Config Comparison Diff']:
            tableData['Config Comparison Diff'] = 'Diff Output'

    except:
        app.logger.info('Config Comparison Diff not found')

    # TRAFFIC SCORE
    try:
        tableData['Traffic Score'] = tbl_data['merit_traffic_score']
    except:
        app.logger.info('Traffic Score not found')

    # PRE STREAM DATA
    try:
        tableData['Pre Streams with Loss'] = tbl_data['pre_traffic_num_streams_with_loss']
    except:
        app.logger.info('Pre Streams with Loss not found')

    try:
        tableData['Pre Stream without Loss'] = tbl_data['pre_traffic_num_streams_without_loss']
    except:
        app.logger.info('Pre Stream without Loss not found')

    try:
        tableData['Total Pre Streams'] = tbl_data['pre_traffic_total_streams']
    except:
        app.logger.info('Total Pre Streams not found')

    # POST STREAM DATA
    try:
        tableData['Post Streams with Loss'] = tbl_data['post_traffic_num_streams_with_loss']
    except:
        app.logger.info('Post Streams with Loss not found')

    try:
        tableData['Post Stream without Loss'] = tbl_data['post_traffic_num_streams_without_loss']
    except:
        app.logger.info('Post Stream without Loss not found')

    try:
        tableData['Total Post Streams'] = tbl_data['post_traffic_total_streams']
    except:
        app.logger.info('Total Post Streams not found')

    # PSAT TRIGGER DATA
    try:
        tableData['Trigger Score'] = tbl_data['psat_score']
    except:
        app.logger.info('Trigger Score not found')

    try:
        tableData['''Passed TC's'''] = tbl_data['psat_passed_tc']
    except:
        app.logger.info('Passed TC not found')

    try:
        tableData['''Failed TC's'''] = tbl_data['psat_failed_tc']
    except:
        app.logger.info('Failed TC not found')

    try:
        tableData['''Skipped TC's'''] = tbl_data['psat_skipped_tc']
    except:
        app.logger.info('Skipped TC not found')

    try:
        tableData['''Blocked TC's'''] = tbl_data['psat_blocked_tc']
    except:
        app.logger.info('Blocked TC not found')

    # MERIT FINAL SCORE
    try:
        tableData['Merit Score'] = tbl_data['merit_final_score']
    except:
        app.logger.info('Merit Score not found')

    try:
        tableData['Psat Url'] = tbl_data['psat_url']
    except:
        app.logger.info('Psat Url not found')


    return render_template("merit_table.html",
                           tableData=tableData,
                           itemCount=itemCount,
                           ids_list=ids_list,
                           os_type=os_type,
                           tableDate=tableDate,
                           singleId=singleId)

@app.route('/stream_table/<string:runDate>/<string:queryKey>/<string:singleId>')
def stream_table(runDate, queryKey, singleId):

    stream_table_data = mongo.db[app.selected_collection].find({'_id': ObjectId(singleId), 
                                                                'date':runDate}, {queryKey:1, '_id':0})

    # PUT QUERY INTO LIST OF DICT
    streamDict  = []
    for i in stream_table_data:
        streamDict.append(i)

    return render_template("stream_table.html", runDate=runDate,
                                                queryKey=queryKey,
                                                streamDict=streamDict)

@app.route('/diff_config_checker/<string:runDate>/<string:queryKey>/<string:singleId>')
def diff_config_checker(runDate, queryKey, singleId):

    app.logger.info('Matthew queryKey is {}'.format(queryKey))

    config = mongo.db[app.selected_collection].find({'_id': ObjectId(singleId), 
                                                     'date':runDate}, {queryKey:1, '_id':0})

    # PUT QUERY INTO LIST OF DICT
    configDict  = []
    for i in config:
        configDict.append(i)

    for key, value in configDict[0].items():
        if key == 'Config Comparison Diff':
            diff_config = value
            app.logger.info('Matthew diff_config is {}'.format(diff_config))


    return render_template("diff_config.html", runDate=runDate,
                                                queryKey=queryKey,
                                                diff_config=diff_config)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404



@celery.task(name='app.script_runner')
def script_runner(rtr_hostname, rtr_mgmt_ip, rtr_username, 
                  rtr_password, platform, image_repo, tftp_dir, tftp_server_ip,
                  db_collection='meritData', psat_unzip_output_folder=None, 
                  psat_job_file=None, ixia_chassis_ip=None, get_score=None):

    unique_id = str(uuid.uuid4())

    # CREATE UNIQUE YAML FILE
    yamfilename = 'testbed-' + unique_id + '.yaml'
    
    yaml_file = '''
testbed:
    name: noname
    servers:
        tftp:
            address: 223.255.254.245
            custom:
                rootdir: /auto/tftpboot/mastarke
            server: sj20lab-tftp4
devices:
    {rtr_hostname}:
        type: 'asr9k-x64'
        connections:
            a:
                ip: 172.100.100.100
                port: 2016
                protocol: telnet
            vty_1:
                protocol : telnet
                ip : "{rtr_mgmt_ip}"
            vty_2:
                protocol : telnet
                ip : "{rtr_mgmt_ip}"
        tacacs:
            login_prompt: "Username:"
            password_prompt: "Password:"
            username: "{rtr_username}"
        passwords:
            tacacs: {rtr_password}
            enable: {rtr_password}
            line: {rtr_password}
    '''.format(rtr_hostname=rtr_hostname, rtr_mgmt_ip=rtr_mgmt_ip, rtr_username=rtr_username, rtr_password=rtr_password,)
    try:
        with open("{}".format(yamfilename), "w") as fh:
            fh.write(yaml_file)
            fh.close()
    except:
        copy_error = True


    jobfile = '''
from ats.easypy import run
import os

class ScriptArgs(object):
    """script related arguments"""
    # CELERY JOB FILE

    get_score = {get_score}

    testbed_file = ('{yamfilename}')
    rtr = '{rtr_hostname}'
    image_repo = '{image_repo}'
    user_tftp_dir = '{tftp_dir}'
    tftp_ip = '{tftp_server_ip}'
    platform = '{platform}'

    ### DATABASE ARGS ###
    db_host = 'mastarke-lnx-v2'
    db_name = 'meritDB'
    db_collection = '{db_collection}'

    ### PSAT ARGS ###
    psat_unzip_output_folder = '{psat_unzip_output_folder}'
    psat_job_file = '{psat_job_file}'

    # IXIA_CHASSIS
    ixia_chassis_ip = '{ixia_chassis_ip}'


def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/image_picker_site/basic_telnet_script.py'))
'''.format(yamfilename=yamfilename, rtr_hostname=rtr_hostname, platform=platform, 
           image_repo=image_repo, tftp_dir=tftp_dir, tftp_server_ip=tftp_server_ip,
           db_collection=db_collection, psat_unzip_output_folder=psat_unzip_output_folder,
           psat_job_file=psat_job_file, ixia_chassis_ip=ixia_chassis_ip, get_score=get_score)


    # CREATE UNIQUIE JOBFILE NAME
    jobfilename = 'jobfile-' + unique_id + '.py'


    with open(jobfilename, mode='w', encoding='utf-8') as a_file:
        a_file.write(jobfile)   
    
    logger.info('###  Matthew in script_runner celery task  ###')
    os.system('easypy {}'.format(jobfilename))
    logger.info('###  !!!  Matthew in script_runner celery has now completed  !!!  ###')

    logger.info('###  Matthew in script_runner removing jobfile {}  ###'.format(jobfilename))
    os.system('rm {} {}'.format(jobfilename, yamfilename))


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.run(debug=True, port=1111, host='mastarke-lnx-v2')
