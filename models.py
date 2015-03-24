# Copyright 2008 Adam Stiles
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required
# by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS
# OF ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.api import app_identity

import logging
FORMAT = "[%(levelname)s %(asctime)s %(filename)s:%(lineno)s] %(funcName)20s()  %(message)s"
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)

import urlparse
import urllib

import short_url

DEFAULT_SCHEME = 'http'

DEFAULT_NETLOC = '4RT.mp'
if app_identity.get_default_version_hostname().startswith('localhost'):
    DEFAULT_NETLOC = app_identity.get_default_version_hostname()


class View(ndb.Model):
    url_key = ndb.KeyProperty(kind='URL')
    create_date = ndb.DateTimeProperty(auto_now_add=True)


class Link(ndb.Model):
    target_url = ndb.TextProperty(required=True, default='oops')
    sequence_index = ndb.ComputedProperty(lambda self: self.index)
    create_date = ndb.DateTimeProperty(auto_now_add=True)
    created_by = ndb.UserProperty(
        validator=lambda p,
        v: users.get_current_user())
    vanity_path = ndb.BooleanProperty(default=False)

    artmap_user_id = ndb.TextProperty()
    mixpanel_distinct_id = ndb.TextProperty()
    mailchimp_user_id = ndb.TextProperty()
    google_analytics_client_id = ndb.TextProperty()

    utm_campaign = ndb.TextProperty()
    utm_source = ndb.TextProperty()
    utm_medium = ndb.TextProperty()
    utm_content = ndb.TextProperty()

    def __repr__(self):
        return 'link:%s target:%s' % (self.key.id(), self.target_url)

    def __unicode__(self):
        return unicode(self.key.id())

    def __str__(self):
        return self.__unicode__()

    @staticmethod
    def update_query_string(target_url, **kwargs):
        logger.debug('update_query_string target_url:%s, kwargs:%s',
                     target_url, kwargs)

        parts = urlparse.urlsplit(target_url)
        logger.debug('update_query_string parts:%s', parts)
        query_dict = urlparse.parse_qs(parts[3])
        logger.debug('update_query_string query_dict:%s', query_dict)
        query_dict.update(kwargs)
        logger.debug('update_query_string updated query_dict:%s', query_dict)

        query_string = urllib.urlencode(query_dict)
        logger.debug('update_query_string query_string:%s', query_string)
        url = urlparse.urlunsplit(parts[0], parts[1],
                                  parts[2], query_string, parts[4])
        logger.debug('update_query_string new url:%s', url)
        return url

    @classmethod
    def get_highest_index(cls):
        try:
            return int(cls.query().order(-cls.sequence_index).get().sequence_index)
        except Exception as e:
            logger.error(e)
            return 1

    @classmethod
    def create_key(cls, scheme, netloc, path):
        logger.debug(
            'create_key scheme:%s, netloc:%s, path:%s',
            scheme,
            netloc,
            path)
        if not path:
            logger.debug('create_key no vanity path-> generating unique_path')
            count = cls.get_highest_index()
            logger.debug('create_key entity count: %s', count)
            path = short_url.encode_url(count)
            logger.debug('create_key encoded entity count: %s', path)
        logger.debug('create_key path:%s', path)
        url = urlparse.urlunsplit([scheme, netloc, path, '', ''])
        logger.debug('create_key url:%s', url)
        entity = cls(key=ndb.Key(cls, url))
        result = ndb.transaction(
            lambda: entity.put() if not entity.key.get() else None)
        logger.debug('create_key result:%s', result)
        if result:
            return result
        else:
            raise KeyError('Link already exists for url:%s' % url)

    @classmethod
    def create(cls, target_url=None, scheme=DEFAULT_SCHEME,
               netloc=DEFAULT_NETLOC, path=None,
               utm_campaign=None, utm_source=None, utm_medium=None,
               utm_content=None):

        if any([utm_campaign, utm_source, utm_medium, utm_content]):
            target_url = cls.update_query_string(target_url,
                                                 utm_campaign=utm_campaign,
                                                 utm_source=utm_source,
                                                 utm_medium=utm_medium,
                                                 utm_content=utm_content)

        vanity_path = False if not path else True
        logger.debug('create vanity_path: %s', vanity_path)
        key = cls.create_key(scheme, netloc, path)
        logger.debug('create key: %s', key)
        link = cls(key=key, target_url=target_url, utm_campaign=utm_campaign,
                   utm_source=utm_source, utm_medium=utm_medium,
                   utm_content=utm_content, vanity_path=vanity_path)
        logger.debug('create link: %s', link)
        key = link.put()
        if key:
            memcache.set(key=link.key.id(), value=link.target_url)
            logger.debug(
                'Added to memcache: %s=%s',
                link.key.id(),
                link.target_url)

        logger.debug('create key: %s', key)
        return key

    @property
    def path(self):
        path = urlparse.urlsplit(self.key.id())[3]
        logger.debug('path: %s', path)
        return path


    @property
    def index(self, path=None):
        if self.vanity_path is True:
            logger.debug('index vanity path: %s index = 0', self)
            return 0
        try:
            index = short_url.decode_url(self.path)
            logger.debug('index for %s = %s', self, index)
            return index
        except Exception as e:
            logger.error(e)
            return 1

    @property
    def url(self):
        return self.key.id()

    @property
    def json(self):
        return "{\"link\":\"%s\",\"target_url\":\"%s\"}\n" % (
            self.key.id(), self.target_url)
