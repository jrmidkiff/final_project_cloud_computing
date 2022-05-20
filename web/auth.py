# auth.py
#
# Copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
#
# Manage GAS user profiles and Globus Auth integration
#
# ************************************************************************
#
# DO NOT MODIFY THIS FILE IN ANY WAY.
#
# ************************************************************************
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import uuid
from flask import (flash, redirect, render_template, url_for,
  request, session, abort)

from globus_sdk import RefreshTokenAuthorizer, ConfidentialAppAuthClient

from gas import app, db
from decorators import authenticated
from helpers import (load_portal_client, get_portal_tokens,
  get_safe_redirect)

from models import Profile

"""Create a new user profile
This is run automatically the first time we see a (valid) new identity
"""
def create_profile(identity_id=None, name=None, email=None):
  profile = Profile(
    identity_id=identity_id,
    name=name,
    email=email,
    institution=None,
    role="free_user"
  )
  try:
    db.session.add(profile)
    db.session.commit()
  except:
    app.logger.error('Failed to create user profile')
    db.session.rollback()
    db.session.flush()
  return id

"""Gets user profile from RDS database
"""
def get_profile(identity_id=None):
  return db.session.query(Profile).filter_by(identity_id=identity_id).first()

"""Update an existing user's profile
"""
def update_profile(identity_id=None, name=None,
  email=None, institution=None, role=None):
  profile = db.session.query(Profile).filter_by(identity_id=identity_id).first()
  profile.name = name if name else profile.name
  profile.email = email if email else profile.email
  profile.institution = institution if institution else profile.institution
  profile.role = role if role else profile.role
  try:
    db.session.commit()
  except:
    app.logger.error('Failed to update user profile')
    db.session.rollback()
    db.session.flush()
  return id

"""Logout from Globus Auth
"""
@app.route('/logout', methods=['GET'])
@authenticated
def logout():
  client = load_portal_client()

  # Revoke the tokens with Globus Auth
  for token, token_type in ((token_info[ty], ty)
    # Get all of the token info dicts
    for token_info in session['tokens'].values()
      # cross product with the set of token types
      for ty in ('access_token', 'refresh_token')
        # only where the relevant token is actually present
        if token_info[ty] is not None):
          client.oauth2_revoke_token(
            token, additional_params={'token_type_hint': token_type})

  # Destroy the session state
  app.logger.info(f"{session['name']} ({session['primary_identity']}) logged out")
  session.clear()

  redirect_uri = url_for('home', _external=True)

  logout_url = []
  logout_url.append(app.config['GLOBUS_AUTH_LOGOUT_URI'])
  logout_url.append(f"?client={app.config['GAS_CLIENT_ID']}")
  logout_url.append(f"&redirect_uri={redirect_uri}")
  logout_url.append("&redirect_name=Genomics Annotation Service")

  # Redirect the user to the Globus Auth logout page
  return redirect(''.join(logout_url))

"""User profile information; assocated with a Globus Auth identity
"""
@app.route('/profile', methods=['GET', 'POST'])
@authenticated
def profile():
  identity_id = session.get('primary_identity')
  profile = get_profile(identity_id=identity_id)

  if profile:
    # GAS user exists
    if request.method == 'GET':
      session['name'] = profile.name
      session['email'] = profile.email
      session['institution'] = profile.institution
      session['role'] = profile.role

      if request.args.get('next'):
        session['next'] = get_safe_redirect()

      return render_template('profile.html', profile=profile)

    elif request.method == 'POST':
      name = session['name'] = request.form['name']
      email = session['email'] = request.form['email']
      institution = session['institution'] = request.form['institution']

      update_profile(identity_id=identity_id,
        name=name,
        email=email,
        institution=institution)

      flash('Thank you! Your profile has been successfully updated.', 'success')
  else:
    # First-time GAS user; auto-create a profiles
    create_profile(identity_id=identity_id,
      name=session['name'],
      email=session['email'])
    #session['next'] = url_for('annotate')

  if 'next' in session:
    redirect_to = session['next']
    session.pop('next')
  else:
    redirect_to = url_for('profile')

  return redirect(redirect_to)


"""Handle interaction with Globus Auth
"""
@app.route('/authcallback', methods=['GET'])
def authcallback():
  # If we're coming back from Globus Auth in an error state, the error
  # will be in the "error" query string parameter
  if 'error' in request.args:
    flash("GAS login failed: " +
      request.args.get('error_description', request.args['error']))
    return redirect(url_for('home'))

  # Set up our Globus Auth/OAuth2 state
  redirect_uri = url_for('authcallback', _external=True)

  client = load_portal_client()
  client.oauth2_start_flow(redirect_uri, refresh_tokens=True)

  # If there's no "code" query string parameter, we're in this route
  # starting a Globus Auth login flow
  if 'code' not in request.args:
    additional_authorize_params = (
      {'signup': 1} if request.args.get('signup') else {})

    auth_uri = client.oauth2_get_authorize_url(
      additional_params=additional_authorize_params)

    return redirect(auth_uri)
      
  else:
    # If we do have a "code" param, we're coming back from Globus Auth
    # and can start the process of exchanging an auth code for a token
    code = request.args.get('code')
    tokens = client.oauth2_exchange_code_for_tokens(code)

    id_token = tokens.decode_id_token(client)
    session.update(
      tokens=tokens.by_resource_server,
      is_authenticated=True,
      name=id_token.get('name', ''),
      email=id_token.get('email', ''),
      institution=id_token.get('organization', ''),
      primary_username=id_token.get('preferred_username'),
      primary_identity=id_token.get('sub'),
    )

    profile = get_profile(identity_id=session['primary_identity'])

    if profile:
      session['name'] = profile.name
      session['email'] = profile.email
      session['institution'] = profile.institution
      session['role'] = profile.role

      app.logger.info(f"Successful login by {profile.name} (Globus identity: {profile.identity_id})")
  
      if 'next' in session:
        redirect_to = session['next']
        session.pop('next')
      else:
        redirect_to = url_for('annotations_list')

      return redirect(redirect_to)

    else:
      return redirect(url_for('profile', next=url_for('annotate')))

### EOF
