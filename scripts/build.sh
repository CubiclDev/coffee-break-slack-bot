#!/usr/bin/env bash

rm -r ./slack_bot_with_dependencies/
cp -r slack_bot slack_bot_with_dependencies
pip install -r requirements.txt -t ./slack_bot_with_dependencies/
