#!/bin/sh

set -e

rm -rf virtualenv || true
virtualenv --distribute virtualenv
. virtualenv/bin/activate
./update_requirements.sh
