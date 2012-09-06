from setuptools import setup, find_packages

setup(
    name='pip-rinstall',
    version='0.0.1',
    author_email='peter.neumark@prezi.com',
    packages=find_packages(),
    scripts=[],
    url='https://github.com/prezi/pip-rinstall',
    description='recursive requirements.txt processing for pip',
    long_description='Please fill in this description.',
    install_requires=['pip'],
)
