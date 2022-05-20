#!/usr/bin/env python

# run_gas_dev.py
#
# Copyright (C) 2011-2020 Vas Vasiliadis
# University of Chicago
#
# Rns the GAS app using Flask's WSGI server for development/testing purposes
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

from gas import app

if __name__ == '__main__':
  app.run(
    host=app.config['GAS_APP_HOST'],
    port=app.config['GAS_HOST_PORT'],
  )

### EOF
