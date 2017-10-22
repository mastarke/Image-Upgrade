from flask import (Flask, render_template, flash, redirect,
                   url_for, session, logging, request, g)
# from wtforms import (Form, StringField, TextAreaField, TextField, PasswordField)
from logging.handlers import RotatingFileHandler
from flask_pymongo import PyMongo
import pymongo
from functools import wraps
import json
from flask import jsonify
from flask_mail import Mail, Message
from collections import OrderedDict
import re
from bson import ObjectId
import os


app = Flask(__name__)


app.config['MONGO_HOST'] = 'mastarke-lnx-v2'
app.config['MONGO_DBNAME'] = 'meritDB'
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


# INDEX
@app.route('/', methods=['GET', 'POST'])
def index():

    return render_template('index.html')


# ABOUT
@app.route('/about', methods=['GET', 'POST'])
def about():

    return render_template('about.html')


# Image
@app.route('/image', methods=['GET', 'POST'])
def image():

    command = ('ls /auto/prod_weekly_archive1/bin/  '
               '/auto/prod_weekly_archive2/bin/  '
               '/auto/prod_weekly_archive3/bin/')

    command_output = os.popen(command).read()

    matchObj = re.findall(r'\d+.\d+.\d+.\d+I.*', command_output)
    cur_releases = list(set(matchObj))

    return render_template('image.html', cur_releases=cur_releases)


@app.route('/packages', methods=['GET', 'POST'])
def packages():

    if request.method == 'POST':
        image = request.form['image']
        platform = request.form['platform']
        

        session['platform'] = platform
        # session['tftp_server_ip'] = tftp_server_ip
        
        # app.logger.info('Matthew tftp_server_ip is {}'.format(tftp_server_ip))
        
    command = ('ls /auto/prod_weekly_archive1/bin/{image}/{platform}  '
                 '/auto/prod_weekly_archive2/bin/{image}/{platform}  '
                 '/auto/prod_weekly_archive3/bin/{image}/{platform}'.format(image=image,platform=platform))
    command_output = os.popen(command).read()

    dir_found = re.search(r'\/\w+\/\w+\/\w+\/.*', command_output)
    path = re.sub(r':', '', dir_found.group(0))
    image_repo = path
    

    session['image_repo'] = image_repo


    packages = re.sub(r'\/\w+\/\w+\/\w+\/.*', '', command_output)
    pies = re.findall(r'\w+.*', packages)
    
    return render_template('packages.html', pies=pies)


@app.route('/copycmd', methods=['GET', 'POST'])
def copycmd():

    image_repo = session.get('image_repo', None)
    platform = session.get('platform', None)
    

    if request.method == 'POST':
        pies = request.form.getlist('pies')
        tftp_dir = request.form['tftp_dir']
        tftp_server_ip = request.form['tftp_server_ip']
    
        pies_str = ' '.join(pies)

        for item in pies:
            copy_cmd = 'cp {}/{} {}'.format(image_repo, item, tftp_dir)
            chmod_cmd = 'chmod 777 {}/{}'.format(tftp_dir, item)
            os.popen(copy_cmd).read()
            os.popen(chmod_cmd).read()

    return render_template('copycmd.html', pies=pies, pies_str=pies_str, 
                                           tftp_dir=tftp_dir, platform=platform,
                                           tftp_server_ip=tftp_server_ip)


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




if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.run(debug=True, port=1111, host='sjc-ads-4581')
