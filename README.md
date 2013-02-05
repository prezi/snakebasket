Snakebasket
===============

The pip++ which will eventually make python development a little easier:
Features:
 * Follow requirements.txt or requirements-$POSTFIX.txt files in 
   the root of editable requirements during install.
 * In case of conflicting requirements, choose the newer version.

Installation
---
Within your virtualenv, run:
`curl -ss -L http://href.prezi.com/snakebasket | bash -s`

Legacy
---
*Don't use this version unless you want to spend countless hours debugging unreadable code!*
The old and untested version of snakebasket can be installed via pip from:
`pip install -e git+git@github.com:prezi/snakebasket.git@v1.0.0#egg=snakebasket`

Development
---
To run snakebasket tests, you must first create a virtualenv
and add the necessary testing packages:
```
virtualenv --distribute --no-site-packages sb-venv
. sb-venv/bin/activate
pip install -r requirements-development.txt 
```
To run tests, make sure the virtualenv is active, then execute the
following from the project root:
```
cd tests/
python runtests.py
```
Warnings about certificates are expected, pay them no attention:
```
warning: bitbucket.org certificate with fingerprint 24:9c:45:8b:9c:aa:ba:55:4e:01:6d:58:ff:e4:28:7d:2a:14:ae:3b not verified (check hostfingerprints or web.cacerts config setting)
```

