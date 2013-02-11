#!/bin/bash
# clean test artifacts.
./clean.sh
# create virtualenv if no virtualenv
VIRTUALENV=$WORKSPACE/sb-venv
cd $WORKSPACE
if [ ! -f $VIRTUALENV/bin/activate ]; then
    echo "Virtualenv doesn't exist. Building."
    virtualenv --distribute sb-venv
    . $VIRTUALENV/bin/activate && pip install -r requirements-development.txt
fi
. $VIRTUALENV/bin/activate
cd $WORKSPACE/tests
python runtests.py --with-xunit -verbose
# run snakebasket tests
