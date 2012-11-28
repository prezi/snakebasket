from setuptools import setup, find_packages

setup(
    name='snakebasket',
    version='1.0.0',
    author_email='peter.neumark@prezi.com',
    packages=find_packages(exclude=['tests']),
    entry_points=dict(console_scripts=['sb=snakebasket:main']),
    url='https://github.com/prezi/snakebasket',
    description='Python environment and release management for prezi.',
    long_description='This is part of the example-project.'
)
