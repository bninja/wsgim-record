============
wsgim-record
============

.. image:: https://travis-ci.org/bninja/wsgim-record.png
   :target: https://travis-ci.org/bninja/wsgim-record

.. image:: https://coveralls.io/repos/bninja/wsgim-record/badge.png
   :target: https://coveralls.io/r/bninja/wsgim-record


WSGI middleware for conditionally recording request/response information.

Install it:

.. code:: bash

   $ pip install wsgim-record
   ...

and use it:

.. code:: python

   import wsgim_record

   class RecordMiddleware(wsgim_record.RecordMiddleware)
   
       # tell what to record

       def record_input(self, environ)
           return True

       def record_errors(self, environ)
           return False

       def record_output(self, environ, status, headers, exc_info=None)
           return True

        # what was recorded
        
        def recorded(self, environ, input, errors, status, headers, output):
            ...

   wrapped = RecordMiddleware(app)
