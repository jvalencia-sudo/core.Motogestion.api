#!/usr/bin/zsh

## Extract strings from templates
pybabel extract --mapping=babel.ini --no-wrap --output-file=messages.pot ./

## Update the actual translation with the latest messages
pybabel update -i messages.pot -d locales -l es

## Compile .po files to .mo
pybabel compile -d locales -f
