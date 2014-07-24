import re
import setuptools


setuptools.setup(
    name='wsgim-record',
    version=(
        re
        .compile(r".*__version__ = '(.*?)'", re.S)
        .match(open('wsgim_record.py').read())
        .group(1)
    ),
    url='https://github.com/bninja/wsgim-record',
    license='BSD',
    author='stan',
    author_email='stan@hooper.com',
    description='WSGI middleware for recording requests/responses.',
    long_description=open('README.rst').read(),
    py_modules=['wsgim_rip'],
    include_package_data=True,
    platforms='any',
    install_requires=[],
    extras_require={
        'test': [
            'pytest >=2.5.2,<3',
            'pytest-cov >=1.7,<2',
        ],
    },
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)