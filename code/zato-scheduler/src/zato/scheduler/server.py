# -*- coding: utf-8 -*-

"""
Copyright (C) 2016 Dariusz Suchojad <dsuch at zato.io>

Licensed under LGPLv3, see LICENSE.txt for terms and conditions.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# stdlib
import logging
from traceback import format_exc

# Bunch
from bunch import Bunch

# gevent
from gevent.pywsgi import WSGIServer

# Zato
from zato.common import ZATO_ODB_POOL_NAME
from zato.common.odb.api import ODBManager, PoolStore
from zato.scheduler.api import Scheduler

# ################################################################################################################################

logger = logging.getLogger(__name__)

# ################################################################################################################################

ok = b'200 OK'
headers = [(b'Content-Type', b'application/json')]

# ################################################################################################################################

class Config(object):
    """ Encapsulates configuration of various scheduler-related layers.
    """
    def __init__(self):
        self.main = Bunch()
        self.startup_jobs = []
        self.odb = None
        self.on_job_executed_cb = None
        self.stats_enabled = None
        self.job_log_level = 'info'
        self.broker_client = None
        self._add_startup_jobs = True
        self._add_scheduler_jobs = True

# ################################################################################################################################

class SchedulerServer(object):
    """ Main class spawning scheduler-related tasks and listening for HTTP API requests.
    """
    def __init__(self, config):
        self.config = config
        self.sql_pool_store = PoolStore()
        self.sql_pool_store[ZATO_ODB_POOL_NAME] = self.config.main.odb

        main = self.config.main

        if main.crypto.use_tls:
            priv_key, cert = main.crypto.priv_key_location, main.crypto.cert_location
        else:
            priv_key, cert = None, None

        # API server
        self.api_server = WSGIServer((main.bind.host, int(main.bind.port)), self, keyfile=priv_key, certfile=cert)

        # ODB connection
        self.odb = ODBManager()
        self.odb.pool = self.sql_pool_store[ZATO_ODB_POOL_NAME].pool
        self.odb.init_session(ZATO_ODB_POOL_NAME, self.config.odb, self.odb.pool, False)
        self.config.odb = self.odb

        # Scheduler
        self.scheduler = Scheduler(self.config)

# ################################################################################################################################

    def serve_forever(self):
        self.scheduler.serve_forever()
        self.api_server.serve_forever()

# ################################################################################################################################

    def __call__(self, env, start_response):
        try:
            start_response(ok, headers)
            return [b'{}\n']
        except Exception, e:
            logger.warn(format_exc(e))

# ################################################################################################################################
