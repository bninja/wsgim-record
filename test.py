import json
import threading
import time
import urllib2
import uuid
import wsgiref.simple_server
import wsgiref.validate

import pytest

import wsgim_record


def origin(environ, start_response):
    content_length = int(environ.get('CONTENT_LENGTH') or 0)
    environ['wsgi.input'].read(content_length)
    environ['wsgi.errors'].write('none to report')
    content = json.dumps({'ya': 'ah'})
    response_headers = [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(content))),
    ]
    start_response('200 OK', response_headers)
    return [content[:2], content[2:]]


class RecordMiddleware(wsgim_record.RecordMiddleware):

    captures = {}

    @classmethod
    def wait_for_capture(cls, trace, interval=0.1, timeout=3.0):
        if trace in cls.captures:
            return True
        expires_at = time.time() + timeout
        while time.time() < expires_at:
            time.sleep(interval)
            if trace in cls.captures:
                return True
        return False


    def recorded(self, environ, input, errors, status, headers, output):
        self.captures[environ.get('HTTP_X_WSGIM_RECORD_TRACE')] = {
            'input': input,
            'errors': errors,
            'status': status,
            'headers': headers,
            'output': output,
        }


@pytest.fixture(scope='module')
def recorder():
    return RecordMiddleware(origin)


@pytest.fixture(scope='module')
def server(request, recorder):

    def _shutdown():
        server.shutdown()

    app = wsgiref.validate.validator(recorder)
    server = wsgiref.simple_server.make_server('127.0.0.1', 0, app)
    thd = threading.Thread(target=server.serve_forever)
    thd.daemon = True
    thd.start()
    request.addfinalizer(_shutdown)

    return 'http://{0}:{1}'.format(*server.server_address)

@pytest.fixture()
def trace():
    return uuid.uuid4().hex


def test_capture_w_data(recorder, server, trace):
    data = json.dumps({'nothing': 'special'})
    req = urllib2.Request(
        server,
        data=data,
        headers={
            'X-Wsgim-Record-Trace': trace,
            'Content-Type': 'application/json',
        })
    resp = urllib2.urlopen(req)
    assert recorder.wait_for_capture(trace)
    captured = recorder.captures.pop(trace)
    assert captured == {
        'status': '200 OK',
        'input': '{"nothing": "special"}',
        'errors': 'none to report',
        'output': '{"ya": "ah"}',
        'headers': [
            ('Content-Type', 'application/json'), ('Content-Length', '12')
    ]}


def test_capture_wo_data(recorder, server, trace):
    req = urllib2.Request(server, headers={
        'X-Wsgim-Record-Trace': trace,
    })
    resp = urllib2.urlopen(req)
    assert recorder.wait_for_capture(trace)
    captured = recorder.captures.pop(trace)
    assert captured == {
        'status': '200 OK',
        'input': '',
        'errors': 'none to report',
        'output': '{"ya": "ah"}',
        'headers': [
            ('Content-Type', 'application/json'), ('Content-Length', '12')
    ]}
