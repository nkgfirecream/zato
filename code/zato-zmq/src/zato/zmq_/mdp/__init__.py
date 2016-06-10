# -*- coding: utf-8 -*-

"""
Copyright (C) 2016 Dariusz Suchojad <dsuch at zato.io>

Licensed under LGPLv3, see LICENSE.txt for terms and conditions.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# stdlib
import logging

# ZeroMQ
import zmq.green as zmq

# ################################################################################################################################

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ################################################################################################################################

class const:
    """ Constants used by the MDP protocol.
    """
    heartbeat = 3 # In seconds
    ttl = heartbeat * 5 # Time to live, i.e. when to assume the connection is permanently down

    class worker_type:
        zmq = 'zmq'
        zato = 'zato'

    class v01:
        """ Constants for MDP 0.1.
        """
        client = 'MDPC01'
        worker = 'MDPW01'

        ready = chr(1)
        request_to_worker = chr(2)
        reply_from_worker = chr(3)
        heartbeat = chr(4)
        disconnect = chr(5)

        # Custom types used internally
        request_from_client = 'zato.request_from_client'
        reply_to_client = 'zato.reply_to_client'
        heartbeat_worker_to_broker = 'zato.heartbeat_worker_to_broker'
        heartbeat_broker_to_worker = 'zato.heartbeat_broker_to_worker'

# ################################################################################################################################

class BaseZMQConnection(object):
    """ A base class for both client and worker ZeroMQ connections.
    """
    def __init__(self, broker_address='tcp://localhost:47047', linger=0, poll_interval=100, log_details=False):
        self.broker_address = broker_address
        self.linger = linger
        self.poll_interval = poll_interval
        self.keep_running = True
        self.log_details = log_details

        self.ctx = zmq.Context()
        self.connect_client_socket()

# ################################################################################################################################

    def stop_client_socket(self):
        self.client_poller.unregister(self.client_socket)
        self.client_socket.close()

# ################################################################################################################################

    def connect_client_socket(self):

        self.client_socket = self.ctx.socket(zmq.DEALER)
        self.client_socket.linger = self.linger
        self.client_poller = zmq.Poller()
        self.client_poller.register(self.client_socket, zmq.POLLIN)

# ################################################################################################################################

    def reconnect_client_socket(self):
        self.stop_client_socket()

# ################################################################################################################################

class Service(object):
    """ A service offered by an MDP broker along with all the workers registered to handle it.
    """
    def __init__(self, name=None, workers=None):
        self.name = name
        self.workers = workers or []
        self.pending_requests = [] # All requests currently queued up, i.e. received from clients but not delivered to workers yet

# ################################################################################################################################

class WorkerData(object):
    """ An MDP worker registered to handle a given service.
    """
    prefix = 'mdp.worker.'

    def __init__(self, type, id, service_name, last_hb_received=None, last_hb_sent=None, expires_at=None):
        self.type = type
        self.id = self.wrap_id(id)
        self.service_name = service_name
        self.last_hb_received = last_hb_received
        self.last_hb_sent = last_hb_sent
        self.expires_at = expires_at

    @staticmethod
    def wrap_worker_id(type, id):
        return '{}{}.{}'.format(WorkerData.prefix, type, id.encode('hex'))

    def wrap_id(self, id):
        return WorkerData.wrap_worker_id(self.type, id)

    def unwrap_id(self):
        return self.id.replace(self.prefix, '').replace(self.type + '.', '').decode('hex')

    def __repr__(self):
        return '<{} at {}, type:{}, id:{}, srv:{}, exp:{}>'.format(
            self.__class__.__name__, hex(id(self)), self.type, self.id, self.service_name, self.expires_at.isoformat())

# ################################################################################################################################

class EventReady(object):
    """ An MDP ready sent by workers to broker.
    """
    type = const.v01.ready

    def __init__(self, service_name):
        self.service_name = service_name

    def serialize(self):
        return ['', const.v01.worker, const.v01.ready, self.service_name]

# ################################################################################################################################

class EventWorkerHeartbeat(object):
    """ A heartbeat sent from a worker to its broker.
    """
    type = const.v01.heartbeat_worker_to_broker

    def serialize(self):
        return ['', const.v01.worker, const.v01.heartbeat]

# ################################################################################################################################

class EventBrokerHeartbeat(object):
    """ A heartbeat sent from a broker to its worker.
    """
    type = const.v01.heartbeat_broker_to_worker

    def __init__(self, worker_id):
        self.worker_id = worker_id

    def serialize(self):
        return [self.worker_id, '', const.v01.worker, const.v01.heartbeat]

# ################################################################################################################################

class EventClientRequest(object):
    """ An MDP request sent from a client to broker.
    """
    type = const.v01.request_from_client

    def __init__(self, body=None, service_name=None):
        self.body = body
        self.service_name = service_name

    def serialize(self):
        """ Serializes this message on behalf of a client sending it to a broker.
        """
        return ['', const.v01.client, self.service_name, self.body]

# ################################################################################################################################

class EventWorkerRequest(object):
    """ An MDP request sent from a broker to worker.
    """
    type = const.v01.request_to_worker

    def __init__(self, body=None, client=None):
        self.body = body
        self.client = client

    def serialize(self, worker_id):
        """ Serializes this message on behalf of a broker sending it to a given worker by its worker_id.
        """
        return [worker_id, '', const.v01.worker, const.v01.request_to_worker, self.client, '', self.body]

# ################################################################################################################################

class EventClientReply(object):
    """ An MDP reply sent from a broker to a given client by the latter's ID.
    """
    type = const.v01.reply_to_client

    def __init__(self, body=None, recipient=None, service=None):
        self.body = body
        self.recipient = recipient
        self.service = service

    def serialize(self):
        """ Serializes this message on behalf of a worker sending it to a broker.
        """
        return [self.recipient, '', const.v01.client, self.service, self.body]

# ################################################################################################################################

class EventWorkerReply(object):
    """ An MDP reply sent from a worker to broker.
    """
    type = const.v01.reply_from_worker

    def __init__(self, body=None, recipient=None):
        self.body = body
        self.recipient = recipient

    def serialize(self):
        """ Serializes this message on behalf of a worker sending it to a broker.
        """
        return [b'', const.v01.worker, const.v01.reply_from_worker, self.recipient, b'', self.body]

# ################################################################################################################################

class EventWorkerDisconnect(object):
    """ A disconnect event sent from a worker to its broker.
    """
    type = const.v01.disconnect

    def serialize(self):
        return ['', const.v01.worker, const.v01.disconnect]

# ################################################################################################################################

class EventBrokerDisconnect(object):
    """ A disconnect event sent from a broker to a specific worker.
    """
    type = const.v01.disconnect

    def serialize(self, worker_id):
        return [worker_id, '', const.v01.worker, const.v01.disconnect]

# ################################################################################################################################
