"""
"""

__version__ = '0.1.0'

__all__ = [
    'RecordMiddleware'
]

import logging
import pprint
import StringIO


logger = logging.getLogger(__name__)


class RecordMiddleware(object):
    """
    """

    def __init__(self, next_app):
        self.next_app = next_app

    def __call__(self, environ, start_response):
        return self.AppProxy(self)(environ, start_response)

    def record_input(self, environ):
        """
        """
        return True

    def record_errors(self, environ):
        """
        """
        return True

    def record_response(self, environ, status, headers, exc_info=None):
        """
        """
        return True

    def recorded(self, environ, input, errors, status, headers, output):
        """
        """
        pass

    # internals

    class ReadProxy(object):

        def __init__(self, obj):
            self.obj = obj
            self.value = StringIO.StringIO()

        def getvalue(self):
            return self.value.getvalue()

        def close(self):
            return self.value.close()

        # wsgi

        def read(self, size):
            value = self.obj.read(size)
            self.value.write(value)
            return value

        def readline():
            value = self.obj.readline()
            self.value.write(value)
            return value

        def readlines(self, hint):
            value = self.obj.readline(hint)
            for line in value:
                self.value.write(line)
            return value

        def __iter__(self):

            def iterator(iter):
                value = iter.next()
                self.value.write(value)
                yield value

            return iterator(self.obj.__iter__())


    class WriteProxy(object):

        def __init__(self, obj, close=None):
            self.obj = obj
            self.value = StringIO.StringIO()
            if close is not None:
                self.close = close

        def getvalue(self):
            return self.value.getvalue()

        def close(self):
            return self.value.close()

        # wsgi

        def write(self, bytes):
            self.value.write(bytes)
            return self.obj.write(bytes)

        def writelines(self, lines):
            for bytes in lines:
                self.value.write(bytes)
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
            if self.parent.record_input(environ):
                self.input = self.parent.ReadProxy(environ['wsgi.input'])
                environ['wsgi.input'] = self.input
            self.errors = None
            if self.parent.record_errors(environ):
                self.errors = self.parent.WriteProxy(environ['wsgi.errors'])
                environ['wsgi.errors'] = self.errors
            self._start_response = start_response
            self._iter = iter(self.parent.next_app(environ, self.start_response))
            return self

        # wsgi

        def start_response(self, status, response_headers, exc_info=None):
            self.status = status
            self.response_headers = response_headers
            if self.parent.record_response(
                    self.environ, status, response_headers, exc_info,
                ):
                self.output = StringIO.StringIO()
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
