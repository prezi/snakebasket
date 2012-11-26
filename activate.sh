#!/bin/sh

APP="snakebasket"

# You don't need modify below this line
export PIP_TEST_USE_DISTRIBUTE="true"
ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROD_VIRTUALENV="/opt/prezi/virtual_environments/${APP}/"
DEVELOPMENT_VIRTUALENV="${ROOT}/virtualenv"

if [ -d "${PROD_VIRTUALENV}" ] ; then
    source "${PROD_VIRTUALENV}/bin/activate"
else
    source "${DEVELOPMENT_VIRTUALENV}/bin/activate"
fi

ORIG_PYTHONPATH="${PYTONPATH}"
export PYTHONPATH="${ROOT}:${PYTONPATH}"

copy_function() {
    local ORIG_FUNC=$(declare -f $1)
    local NEWNAME_FUNC="$2${ORIG_FUNC#$1}"
    eval "$NEWNAME_FUNC"
}

copy_function deactivate orig_deactivate

deactivate () {
    orig_deactivate
    export PYTHONPATH="${ORIG_PYTONPATH}"
}
