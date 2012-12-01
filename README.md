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
The old and untested version of snakebasket can be installed via pip from:
`pip install -e git+git@github.com:prezi/snakebasket.git@v1.0.0#egg=snakebasket`
