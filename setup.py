from setuptools import setup, find_packages

setup(
    name='snakebasket',
    version='1.0.0',
    author_email='peter.neumark@prezi.com',
    packages=find_packages(),
    scripts=['bin/sb'],
    url='https://github.com/prezi/snakebasket',
    description='Python environment and release management for prezi.',
    long_description='This is part of the example-project.',
    install_requires=['pip==1.1'],
)
