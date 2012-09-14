Snakebasket
===============

The pip++ which will eventually make python development a little easier:

`pip install -e git+git@github.prezi.com:infra/snakebasket.git@v1.0.0#egg=snakebasket`

`sb freeze` will correctly print the tag of editable packages (broken in vanilla pip)
and requirements.txt-s in dependencies will also be processed by `sb install`
