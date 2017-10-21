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

    command = ('ls /auto/prod_weekly_archive1/bin/  '
               '/auto/prod_weekly_archive2/bin/  '
               '/auto/prod_weekly_archive3/bin/')

    command_output = os.popen(command).read()

    matchObj = re.findall(r'\d+.\d+.\d+.\d+I.*', command_output)
    cur_releases = list(set(matchObj))

    return render_template('index.html', cur_releases=cur_releases)


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
            # app.logger.info('Matthew copy_cmd is {}'.format(copy_cmd))
            # app.logger.info('Matthew chmod_cmd is {}'.format(chmod_cmd))
            os.popen(copy_cmd).read()
            os.popen(chmod_cmd).read()

    return render_template('copycmd.html', pies=pies, pies_str=pies_str, 
                                           tftp_dir=tftp_dir, platform=platform)




if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.run(debug=True, port=1111, host='sjc-ads-4581')
