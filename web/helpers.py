# helpers.py
#
# Copyright (C) 2011-2020 Vas Vasiliadis
# University of Chicago
#
# Miscellaneous helper functions
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import re
import json

from flask import request, render_template
from threading import Lock

import globus_sdk

try:
  from urllib.parse import urlparse, urljoin
except:
  from urlparse import urlparse, urljoin

from gas import app, db

"""Create an AuthClient for the GAS app
"""
def load_portal_client():
  return globus_sdk.ConfidentialAppAuthClient(
    app.config['GAS_CLIENT_ID'],
    app.config['GAS_CLIENT_SECRET']
  )

"""https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html
"""
def is_safe_redirect_url(target):    
  host_url = urlparse(request.host_url)
  redirect_url = urlparse(urljoin(request.host_url, target))
  return (redirect_url.scheme in ('http', 'https')) and \
    (host_url.netloc == redirect_url.netloc)

"""https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html
"""
def get_safe_redirect():    
  url = request.args.get('next')
  if url and is_safe_redirect_url(url):
    return url

  url = request.referrer
  if url and is_safe_redirect_url(url):
    return url

  return '/'

"""Grant access token to GAS app
Uses the client_credentials grant to get access tokens 
on the GAS's "client identity"
"""
def get_portal_tokens(scopes=None):
  scopes = scopes or \
    ['openid','urn:globus:auth:scope:demo-resource-server:all']
  with get_portal_tokens.lock:
    if not get_portal_tokens.access_tokens:
      get_portal_tokens.access_tokens = {}

    scope_string = ' '.join(scopes)

    client = load_portal_client()
    tokens = client.oauth2_client_credentials_tokens(
      requested_scopes=scope_string
    )

    # Walk all resource servers in the token response (includes the
    # top-level server, as found in tokens.resource_server), and store the
    # relevant Access Tokens
    for resource_server, token_info in tokens.by_resource_server.items():
      get_portal_tokens.access_tokens.update({
        resource_server: {
          'token': token_info['access_token'],
          'scope': token_info['scope'],
          'expires_at': token_info['expires_at_seconds']
        }
      })

    return get_portal_tokens.access_tokens

get_portal_tokens.lock = Lock()
get_portal_tokens.access_tokens = None

### EOF
