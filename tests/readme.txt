created symlinks with:
# make sure you're in the snakebasket/tests dir
# python test files
for i in `ls ../pip/tests/*.py`; do eval "ln -s $i `basename $i`"; done
# assets
for i in `find ../pip/tests -type d -maxdepth 1 -mindepth 1`; do cmd="ln -s $i `basename $i`"; echo $cmd; eval $cmd; done
