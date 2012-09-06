from setuptools import setup, find_packages

setup(
    name='pip-rinstall',
    version='1.0.0',
    author_email='peter.neumark@prezi.com',
    packages=find_packages(),
    scripts=[],
    url='https://github.com/prezi/pip-rinstall',
    description='recursive requirements.txt processing for pip',
    long_description='This is part of the example-project.',
    install_requires=['pip'],
)
