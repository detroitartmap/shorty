# -*- coding: utf-8 -*-
import os
import logging
logger = logging.getLogger(__name__)

import settings

from google.appengine.ext import ndb
from django.core.validators import URLValidator
validate_url = URLValidator()
from django.core.validators import validate_email
from django.core.validators import validate_ipv46_address


class URLProperty(ndb.StringProperty):
    def _validate(self, value):
        logger.debug('URLProperty._validate(%s)' % value)
        if not value:
            return
        validate_url(value)


class EmailProperty(ndb.StringProperty):
    def _validate(self, value):
        logger.debug('EmailProperty._validate(%s)' % value)
        if not value:
            return
        validate_email(value)


class IPv46AddressProperty(ndb.StringProperty):
    def _validate(self, value):
        logger.debug('IPv46AddressProperty._validate(%s)' % value)
        if not value:
            return
        validate_ipv46_address(value)


class PhoneNumberProperty(ndb.StringProperty):
    def _validate(self, value):
        pass
