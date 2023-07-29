#!/bin/bash

experiment_creator=$( geni-get user_urn | rev | cut -d '+' -f -1 | rev )
sudo su -c /local/repository/scripts/startup_creator.sh $experiment_creator
