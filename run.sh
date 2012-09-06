#!/bin/bash


if [ $# -lt 1 ] ; then
  echo "Usage: $0 <scriptname in bin/ without ending '.py'> [arguments to the script...]"
  exit 1
fi

(
ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${ROOT}"
source ./activate.sh

if [ -x "bin/$1" ] ; then
    SCRIPT="bin/$1"
elif [ -x "bin/$1.sh" ] ; then
    SCRIPT="bin/$1.sh"
elif [ -x "bin/$1.py" ] ; then
    SCRIPT="bin/$1.py"
else
    echo "$1 not found or not executable"
    exit 1
fi

shift

${SCRIPT} "$@"

deactivate
)
