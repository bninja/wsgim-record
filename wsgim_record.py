"""
WSGI middleware for recording request/response information. Could use it like:

.. code:: python

    import pprint

    import wsgim_record

    class RecordMiddleware(wsgim_record.RecordMiddleware)

        def record_input(self, environ):
            # just first 100 bytes
            return 100

        def record_errors(self, environ):
            # all of it
            return True

        def record_response(self, environ, status, headers, exc_info=None):
            status_code = int(status.parition(' ')[0])
            # all for non-200s
            if status_code != 200:
                return True
            # othwerwise just last 100 bytes
            return -100

        def recorded(self, environ, input, errors, status, headers, output):
            # here's what we recorded
            pprint.pprint({
                'environ': environ,
                'status': status,
                'errors': errors,
                'headers': headers,
                'output': output,
            })

"""

__version__ = '0.1.1'

__all__ = [
    'RecordMiddleware'
]

import logging
import StringIO


logger = logging.getLogger(__name__)


class RecordMiddleware(object):
    """
    Conditionally records bytes :

    - read from ``environ["wsgi.input"]``
    - written to ``environ["wsgi.errors"]``
    - yielded by ``next_app``
    or
    - written by ``next_app`` to ``start_response()``
    """

    def __init__(self, next_app):
        self.next_app = next_app

    def __call__(self, environ, start_response):
        return self.AppProxy(self)(environ, start_response)

    # interface

    def record_input(self, environ):
        """
        Whether to record bytes read from ``environ["wsgi.input"]``.

        :param environ: WSGI environment for the request.

        :param environ: WSGI environment for the request.
        :param status: descriptive response status (e.g. "200 OK").
        :param headers: response headers as a list of name, value pairs.
        :param exc_info: optional exception information captured by wrapped WSGI.

        :returns:
            One of:
            - ``True`` to record everything
            - ``False`` to record nothing
            - number to record only first number bytes
            - Negative number to record only last number bytes

        """
        return True

    def record_errors(self, environ):
        """
        Whether to record bytes written to ``environ["wsgi.errors"]``.

        :param environ: WSGI environment for the request.

        :param environ: WSGI environment for the request.
        :param status: descriptive response status (e.g. "200 OK").
        :param headers: response headers as a list of name, value pairs.
        :param exc_info: optional exception information captured by wrapped WSGI.

        :returns:
            One of:
            - ``True`` to record everything
            - ``False`` to record nothing
            - number to record only first number bytes
            - Negative number to record only last number bytes
        """
        return True

    def record_response(self, environ, status, headers, exc_info=None):
        """
        Whether to record bytes yielded by ``next_app`` or written to
        ``start_response()``.

        :param environ: WSGI environment for the request.
        :param status: descriptive response status (e.g. "200 OK").
        :param headers: response headers as a list of name, value pairs.
        :param exc_info: optional exception information captured by wrapped WSGI.

        :returns:
            One of:
            - ``True`` to record everything
            - ``False`` to record nothing
            - A number to record only first n bytes
            - A negative number to record only last n bytes

        """
        return True

    def recorded(self, environ, input, errors, status, headers, output):
        """
        What was recorded.

        :param environ: WSGI environment for the request.
        :param input: bytes written from ``environ["wsgi.input"]`` or None if declined.
        :param errors: bytes written from ``environ["wsgi.errors"]`` or None if declined.
        :param status: descriptive response status (e.g. "200 OK").
        :param headers: response headers as a list of name, value pairs.
        :param errors: bytes yielded by ``next_app`` or written to ``start_response()`` or None if declined.

        """
        pass

    # internals

    def buffer_for(self, decision):
        """
        :param decision:

            One of:
            - ``True`` for unbounded
            - ``False`` for none
            - + integer for first number bytes (i.e. head)
            - - integer for last number bytes (i.e. tail)
            - 0 for none

        """
        # bool
        if decision is True:
            return StringIO.StringIO()
        if decision is False:
            return None

        # number
        if decision > 0:
            return self.Head(decision)
        if decision < 0:
            return self.Tail(-decision)
        return None

    class Head(object):

        def __init__(self, max_len):
            self.max_len = max_len
            self.io = StringIO.StringIO()

        # io

        def write(self, bytes):
            allowed = min(len(bytes), self.max_len - self.io.tell())
            if not allowed:
                return 0
            if allowed == len(bytes):
                self.io.write(bytes)
            else:
                self.io.write(bytes[:allowed])
            return allowed

        def getvalue(self):
            return self.io.getvalue()

        def close(self):
            return self.io.close()

    class Tail(object):

        def __init__(self, max_len):
            self.max_len = max_len
            self.io1 = StringIO.StringIO()
            self.io2 = StringIO.StringIO()
            self.ioc, self.iop = self.io1, self.io2

        # io

        def write(self, bytes):
            if len(bytes) <= self.max_len - self.ioc.tell():
                self.ioc.write(bytes)
                return len(bytes)
            if len(bytes) >= self.max_len:
                self.ioc.truncate(0)
                self.ioc.write(bytes[-self.max_len:])
                return self.max_len
            rem = min(len(bytes), self.max_len - self.ioc.tell())
            self.ioc.write(bytes[:rem])
            self.ioc, self.iop = self.iop, self.ioc
            self.ioc.truncate(0)
            self.ioc.write(bytes[rem:])
            return len(bytes)

        def getvalue(self):
            value = self.ioc.getvalue()
            if self.iop.tell() > 0:
                value = self.iop.getvalue()[-(self.max_len - len(value)):] + value
            return value

        def close(self):
            self.io1.close()
            self.io2.close()
            self.ioc, self.iop = None, None

    class ReadProxy(object):

        def __init__(self, obj, io):
            self.obj = obj
            self.io = io

        def getvalue(self):
            return self.io.getvalue()

        def close(self):
            return self.io.close()

        # wsgi

        def read(self, size):
            value = self.obj.read(size)
            self.io.write(value)
            return value

        def readline():
            value = self.obj.readline()
            self.io.write(value)
            return value

        def readlines(self, hint):
            value = self.obj.readline(hint)
            for line in value:
                self.io.write(line)
            return value

        def __iter__(self):

            def iterator(iter):
                value = iter.next()
                self.io.write(value)
                yield value

            return iterator(self.obj.__iter__())


    class WriteProxy(object):

        def __init__(self, obj, io, close=None):
            self.obj = obj
            self.io = io
            if close is not None:
                self.close = close

        def getvalue(self):
            return self.io.getvalue()

        def close(self):
            return self.io.close()

        # wsgi

        def write(self, bytes):
            self.io.write(bytes)
            return self.obj.write(bytes)

        def writelines(self, lines):
            for bytes in lines:
                self.io.write(bytes)
            return self.obj.writelines(lines)


    class AppProxy(object):

        def __init__(self, parent):
            self.parent = parent
            self.environ = None
            self.input = None
            self.errors = None
            self.output = None
            self.status = None
            self.response_headers = None
            self._iter = None
            self._start_response = None
            self._write = None

        def __call__(self, environ, start_response):
            self.environ = environ
            buffer = self.parent.buffer_for(self.parent.record_input(environ))
            if buffer is not None:
                self.input = self.parent.ReadProxy(environ['wsgi.input'], buffer)
                environ['wsgi.input'] = self.input
            self.errors = None
            buffer = self.parent.buffer_for(self.parent.record_errors(environ))
            if buffer is not None:
                self.errors = self.parent.WriteProxy(environ['wsgi.errors'], buffer)
                environ['wsgi.errors'] = self.errors
            self._start_response = start_response
            self._iter = iter(self.parent.next_app(environ, self.start_response))
            return self

        # wsgi

        def start_response(self, status, response_headers, exc_info=None):
            self.status = status
            self.response_headers = response_headers
            buffer = self.parent.buffer_for(self.parent.record_response(
                self.environ, status, response_headers, exc_info,
            ))
            if buffer is not None:
                self.output = buffer
            self._write = self._start_response(status, response_headers, exc_info)
            return self

        def write(self, bytes):
            if self.output is not None:
                self.output.write(bytes)
            return self._write(bytes)

        def close(self):
            recording = any(
               fo is not None for fo in [self.input, self.errors, self.output]
            )
            if not recording:
                return
            try:
                self.parent.recorded(
                    environ=self.environ,
                    input=self.input.getvalue() if self.input else None,
                    errors=self.errors.getvalue() if self.errors else None,
                    status=self.status,
                    headers=self.response_headers,
                    output=self.output.getvalue() if self.output else None,
                )
            finally:
                if self.input is not None:
                    self.input.close()
                    self.input = None
                if self.errors is not None:
                    self.errors.close()
                    self.errors = None
                if self.output is not None:
                    self.output.close()
                    self.output = None

        def __iter__(self):
            return self

        def next(self):
            try:
                bytes = self._iter.next()
            except StopIteration:
                self.close()
                raise
            if self.output is not None:
                self.output.write(bytes)
            return bytes
