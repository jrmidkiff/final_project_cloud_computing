# models.py
#
# Copyright (C) 2011-2020 Vas Vasiliadis
# University of Chicago
#
# Database models
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

from gas import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

"""Profile
"""
class Profile(db.Model):
  __tablename__ = 'profiles'

  # Globus Auth identity UUID
  identity_id = db.Column(UUID(as_uuid=True), primary_key=True)
  name = db.Column(db.String(256))
  email = db.Column(db.String(256))
  institution = db.Column(db.String(256))
  role = db.Column(db.String(32), default="free_user")
  created = db.Column(db.DateTime(timezone=True), server_default=func.now())
  updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

  def __repr__(self):
    return (f"<Profile(id={self.identity_id}, name={self.name})>")

### EOF