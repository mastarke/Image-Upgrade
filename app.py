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
        app.logger.info('Matthew platform is {}'.format(platform))
        
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
    
        pies_str = ' '.join(pies)

        for item in pies:
            copy_cmd = 'cp {}/{} {}'.format(image_repo, item, tftp_dir)
            chmod_cmd = 'chmod 777 {}/{}'.format(tftp_dir, item)
            os.popen(copy_cmd).read()
            os.popen(chmod_cmd).read()

    return render_template('copycmd.html', pies=pies, pies_str=pies_str, 
                                           tftp_dir=tftp_dir, platform=platform)


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

if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.run(debug=True, port=1111, host='sjc-ads-4581')
