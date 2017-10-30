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
from hltapi import Ixia


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



class Common_setup(aetest.CommonSetup):
    """Common Setup section."""


    # IMPORT THE JOBFILE INTO NAMESPACE
    jobfile = runtime.job.name  # GET JOB FILE NAME
    a = importlib.import_module(jobfile)  # IMPORT THE JOB FILE INTO NAMESPACE
    ScriptArgs = a.ScriptArgs()  # INSTANCE OF SRSCRIPTARGS


    # IMPORT YAML FILE ATTRIBUTES
    testbed = loader.load(ScriptArgs.testbed_file)
    rtr = testbed.devices[ScriptArgs.rtr]
    mgmt_ip = rtr.connections.vty_1['ip']
    ixia = testbed.devices.ixia
    tcl_server = testbed.devices.ixia.connections.a.tcl_server
    user_tftp_dir = ScriptArgs.user_tftp_dir

   
    log.info(banner('@@@ ATTEMPTING TO TELNET TO ROUTER {} @@@'.format(rtr)))
    # CONNECTING TO ROUTER VIA VTY LINE
    rtr.connect(via ='vty_1', alias = 'mgmt1')
    rtr.connect(via ='vty_2', alias = 'mgmt2')
    
    ixia = Ixia()
    ixia.connect(ixnetwork_tcl_server=tcl_server)

   

class ImageUpgrade(aetest.Testcase):
    """Upgrade image."""

    @aetest.setup
    def setup(self):
        """Testcase setup"""
        # GETTING COMMON_SETUP ATTRIBUTES TO PASS TO TC
        log.info('Matthew your in setup')

    @aetest.test
    def test(self):
        log.info('Matthew your in test')

        
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

