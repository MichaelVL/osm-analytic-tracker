#!/usr/bin/env python

import argparse
import os, io, sys
import kombu, kombu.mixins, kombu.pools
import json
import jsonschema
import avro.schema, avro.io
import base64
import random
import logging

logger = logging.getLogger('messagebus')

class SchemaRegistry(object):
    def __init__(self):
        self.registry = {
        }
        self.path = 'schemas'

    def schema_get(self, schema, version=1):
        # FIXME store versions...
        if schema not in self.registry:
            self.registry[schema] = avro.schema.parse(open(os.path.join(self.path, schema, str(version))+'.avsc', "rb").read())
        return self.registry[schema]

ENVELOPE_SCHEMA = {
    'type': 'object',
    'properties': {
        'schema': {
            'type': 'string'
        },
        'version': {
            'type': 'integer',
            'minimum': 1
        },
        'message': {
            'type': 'string'
        }
    },
    'required': ['schema', 'version', 'message']
}

class Amqp(kombu.mixins.ConsumerProducerMixin):
    def __init__(self, url, exchange, exchange_type, declare_queues, handle_queues=None):
        logger.info('AMQP URL={}'.format(url))
        self.connection = kombu.Connection(url)
        self.exchange = kombu.Exchange(exchange, type=exchange_type)
        self.declare_queues = [kombu.Queue(name=n, exchange=self.exchange, routing_key=k, auto_delete=d) for n,k,d in declare_queues]
        if handle_queues:
            self.handle_queues = [kombu.Queue(name=n, exchange=self.exchange, routing_key=k, auto_delete=d) for n,k,d in handle_queues]
        logger.info('Exchange {}, queues declared {}, handle queues {}'.format(exchange, declare_queues, handle_queues))
        self.schema_registry = SchemaRegistry()

    def __del__(self):
        logger.debug('AMQP cleanup...')

    def send(self, message, schema_name, schema_version, routing_key):
        schema = self.schema_registry.schema_get(schema_name, schema_version)
        writer = avro.io.DatumWriter(schema)
        bytes_writer = io.BytesIO()
        encoder = avro.io.BinaryEncoder(bytes_writer)
        writer.write(message, encoder)
        raw_bytes = bytes_writer.getvalue()
        msg = {
            'schema': schema_name,
            'version': schema_version,
            'message': base64.b64encode(raw_bytes)#json.dumps(message)
        }
        self.producer.publish(msg, exchange=self.exchange,
                              declare = self.declare_queues,
                              routing_key=routing_key, retry=True)

    def get_consumers(self, Consumer, channel):
        handle_queues = getattr(self, 'handle_queues', None)
        logger.debug('Consumer queues: {}'.format(handle_queues))
        return [Consumer(
            queues = handle_queues,
            on_message = self.message_cb,
            accept = {'application/json'},
            prefetch_count = 1,
        )]

    def message_cb(self, message):
        msg = message.payload
        try:
            jsonschema.validate(msg, ENVELOPE_SCHEMA)
            try:
                schema = self.schema_registry.schema_get(msg['schema'], msg['version'])
                bytes_reader = io.BytesIO(base64.b64decode(msg['message']))
                decoder = avro.io.BinaryDecoder(bytes_reader)
                reader = avro.io.DatumReader(schema)
                msg = reader.read(decoder)
                self.on_message(msg, message)
            except avro.schema.AvroException as e:
                logging.error('Unable to validate message schema. Message: {}, schema ({}/{}): {}, delivery info: {}, exception: {}'.format(msg, msg['schema'], msg['version'], schema, message.delivery_info, e))
                message.ack()
        except jsonschema.ValidationError as e:
            logging.error('Unable to validate envelope schema. Message: {}, type {}, delivery info: {}, exception: {}'.format(msg, type(msg), message.delivery_info, e))
            message.ack()

    def on_message(self, payload, message):
        message.ack()


class TestAmqp(Amqp):
    def on_message(self, payload, message):
        print 'Delivery info: {}'.format(message.delivery_info)
        print 'Payload:', payload
        message.ack()

def test_recv(args):
    logging.debug('Entering test_recv(), key={}'.format(args.key))
    if args.queue:
        qname = args.queue
    else:
        qname = 'q-recv-'+str(random.randint(1,1000))
    amqp = TestAmqp(args.url, args.exchange, args.exchange_type, [(qname, args.key, args.noautodelete)], [(args.queue, args.key, args.noautodelete)])
    amqp.run()

def test_logs(args):
    '''Firehose logging. Enable with rabbitmqctl trace_on'''
    logging.debug('Entering test_logs()')
    queues = [('firehose', '#', True)]
    amqp = TestAmqp(args.url, 'amq.rabbitmq.trace', 'topic', queues, queues)
    amqp.run()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='AMQP Test')
    parser.add_argument('-l', dest='log_level', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the log level')
    #parser.add_argument('--url', default='amqp://guest:guest@localhost:5672')
    parser.add_argument('--url', default='amqp://osmtracker-amqp')
    parser.add_argument('--exchange', default='osmtracker')
    parser.add_argument('--exchange-type', default='topic', choices=['topic', 'fanout'])
    parser.add_argument('--noautodelete', default=True, action='store_false')
    subparsers = parser.add_subparsers()

    parser_recv = subparsers.add_parser('recv')
    parser_recv.set_defaults(func=test_recv)
    parser_recv.add_argument('--key', default='new_cset.osmtracker')
    parser_recv.add_argument('--queue', default=None)

    parser_logs = subparsers.add_parser('logs')
    parser_logs.set_defaults(func=test_logs)

    args = parser.parse_args()
    logging.getLogger('').setLevel(getattr(logging, args.log_level))

    sys.exit(args.func(args))
