from setuptools import setup

VERSION = '0.1'

setup(
    name='Flask-MongoRest-Swagger',
    version=VERSION,
    url='https://github.com/matchbox/flask-mongorest-swagger/',
    license='MIT',
    author='Paul Swartz',
    author_email='pswartz@matchbox.net',
    description='Swagger API generation for Flask-MongoRest',
    long_description=open('README.md').read(),
    py_modules=['flask_mongorest_swagger'],
    platforms='any',
    install_requires=[
        'Flask>=0.7',
        'Flask-MongoRest>=0.1.1',
        'ordereddict>=1.1',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
