# decorators.py
#
# Copyright (C) 2011-2020 Vas Vasiliadis
# University of Chicago
#
# Decorators for the GAS
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

from flask import redirect, request, session, url_for
from functools import wraps

from gas import db
from models import Profile

"""Mark a route as requiring authentication
"""
def authenticated(fn):
  @wraps(fn)
  def decorated_function(*args, **kwargs):
    if not session.get('is_authenticated'):
      return redirect(url_for('login', next=request.url))

    if request.path == '/logout':
      return fn(*args, **kwargs)

    if (not session.get('name') or not session.get('email')):
      return redirect(url_for('profile', next=request.url))

    return fn(*args, **kwargs)

  return decorated_function

"""Mark a route as accessible to subscribers (premium users) only
Subscriber must have profile.role = premium_user
"""
def is_premium(fn):
  @wraps(fn)
  def decorated_function(*args, **kwargs):
    # Check if user is a subscriber
    profile = db.session.query(Profile).filter_by(identity_id=session.get('primary_identity')).first()
    if not profile:
      # Force login
      return redirect(url_for('login', next=request.url))
    elif (profile.role != "premium_user"):
      # Redirect free user to subscribe
      return redirect(url_for('subscribe', next=request.url))

    return fn(*args, **kwargs)

  return decorated_function

### EOF