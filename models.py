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

import logging
import urlparse
import urllib

#from properties import URLProperty
import short_url

DEFAULT_SHORT_SCHEME = 'http'
DEFAULT_SHORT_NETLOC = '4RT.mp'


class View(ndb.Model):
    url_key = ndb.KeyProperty(kind='URL')
    create_date = ndb.DateTimeProperty(auto_now_add=True)


class User(ndb.Model):
    mixpanel_distinct_id = ndb.TextProperty()
    google_analytics_client_id = ndb.TextProperty()
    mailchimp_user_id = ndb.TextProperty()
    artmap_user_id = ndb.TextProperty()
    create_date = ndb.DateTimeProperty(auto_now_add=True)


class Link(ndb.Model):
    target_url = ndb.TextProperty(required=True)
    utm_campaign = ndb.TextProperty()
    utm_source = ndb.TextProperty()
    utm_medium = ndb.TextProperty()
    utm_content = ndb.TextProperty()
    create_date = ndb.DateTimeProperty(auto_now_add=True)
    user = ndb.UserProperty(validator=lambda p, v: users.get_current_user())
    vanity_path = ndb.BooleanProperty(default=False)

    def __repr__(self):
        return 'link:%s target:%s' % (self.key.id(), self.target_url)

    def __unicode__(self):
        return unicode(self.key.id())

    def __str__(self):
        return self.__unicode__()

    @staticmethod
    def update_query_string(target_url, **kwargs):
        parts = urlparse.urlsplit(target_url)
        query_dict = urlparse.parse_qs(parts[3])
        query_dict.update(kwargs)
        query_string = urllib.urlencode(query_dict)
        return urlparse.urlunsplit(parts[0], parts[1],
                                   parts[2], query_string, parts[4])

    @classmethod
    def compute_shortpath(cls):

    @classmethod
    def new(cls, target_url, short_scheme=DEFAULT_SHORT_SCHEME,
            short_netloc=DEFAULT_SHORT_NETLOC, short_path=None,
            utm_campaign=None, utm_source=None, utm_medium=None,
            utm_content=None):

        if any([utm_campaign, utm_source, utm_medium, utm_content]):
            target_url = cls.update_query_string(target_url,
                                                 utm_campaign=utm_campaign,
                                                 utm_source=utm_source,
                                                 utm_medium=utm_medium,

                                                 utm_content=utm_content)
        if not short_path:
            short_path = cls.compute_shortpath()
            vanity_path = False
        else:
            vanity_path = True
        path = urlparse.urlunsplit([short_scheme, short_netloc,
                                    short_path, '',''])
        if ndb.Key(cls,path).get():
            raise KeyError

        link = cls(id=path, target_url=target_url, utm_campaign=utm_campaign,
                   utm_source=utm_source, utm_medium=utm_medium,
                   utm_content=utm_content, user=user, vanity_path=vanity_path)
        return link.put()

    @property
    def path(self):
        return urlparse.urlsplit(self.key.id())

    @property
    def url(self):
        return self.key.id()

    @property
    def json(self):
        return "{\"link\":\"%s\",\"target_url\":\"%s\"}\n" % (
            self.key.id(), self.target_url)
