#!/bin/bash

# Do git pull
cd $WORKSPACE
commit=$(git log --pretty=format:'%H' -n 1)
name=$(git log --pretty=format:'%an' -n 1)
git checkout $commit
git log --pretty=format:'description <a href="https://github.com/prezi/snakebasket/commit/%H">%h %an</a> eof-description' -n 1

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
