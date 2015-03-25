import logging
FORMAT = "[%(levelname)s %(asctime)s %(filename)s:%(lineno)s] %(funcName)20s()  %(message)s"
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)
import uuid
import os
import datetime

from google.appengine.ext import webapp
from google.appengine.ext.webapp import WSGIApplication
from google.appengine.ext.webapp import Route
from google.appengine.ext.webapp import RedirectHandler

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.api import app_identity
from google.appengine.api import users
from google.appengine.ext import deferred
from google.appengine.api import logservice
from models import Link

import short_url


def log(request_log_id, memcache_hit, link, target_url, cookies):
    for rlog in logservice.fetch(request_ids=[request_log_id]):
        ga = dict()
        ga['v'] = 1  # protocol version
        ga['tid'] = 'UA-XXXX-Y'  # tracking id
        ga['ds'] = 'shorty'  # data source
        ga['cid'] = uuid.uuid4()  # client id
        ga['uip'] = rlog.ip  # ip address override
        ga['ua'] = rlog.user_agent  # user agent override
        ga['dr'] = rlog.referrer  # document referrer
        ga['t'] = 'event'  # HIT Type
        ga['dh'] = rlog.host  # host name
        ga['dp'] = rlog.resource  # path
        ga['ec'] = 'shorturl'  # event category
        ga['ea'] = 'request'  # event action
        ga['el'] = rlog.resource[1:]  # event label
        ga['ev'] = short_url.decode_url(rlog.resource[1:])  # event value
        ga['plt'] = rlog.latency  # page load time
        ga['rrt'] = rlog.latency  # redirect response time
        logger.debug('log ga:%s', ga)


CLEARDOT = 'GIF89a\x01\x00\x01\x00\x80\xff\x00\xc0\xc0\xc0\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'


class Cookie(webapp.RequestHandler):

    def get(self):
        fields = ('gid', 'mid', 'aid')
        data = {k: self.request.GET.get(k)
                for k in fields if k in self.request.GET}
        logger.debug('Cookie data:%s', data)
        cookies = {k: self.request.cookies.get(
            k) for k in fields if k in self.request.cookies}
        logger.debug('Cookie cookies:%s', cookies)
        expires = datetime.datetime.now()
        expires = expires.replace(year=expires.year + 2)
        logger.debug('Cookie expires:%s', expires)
        for field, value in data.iteritems():
            if value != cookies.get(field):
                logger.debug('Cooke data conflict cookie=%s, data=%s',
                             cookies.get(field), value)
            self.response.set_cookie(field, value=value, expires=expires)
        self.response.content_type = 'image/gif'
        self.response.write(CLEARDOT)


class Create(webapp.RequestHandler):

    def post(self):
        local = app_identity.get_default_version_hostname().startswith('localhost')
        if not local and not users.is_current_user_admin():
            self.abort(405)
        fields = ('target_url', 'path', 'utm_campaign', 'utm_source',
                  'utm_medium', 'utm_content', 'artmap_userid',
                  'mailchimp_userid', 'mixpanel_distinctid', 'google_clientid')
        data = {k: self.request.get(k)
                for k in fields if k in self.request.POST}

        link = Link.create(**data).get()
        return self.response.write(link.json) if link else self.abort(400)


def redirector(handler, *args, **kwargs):
    link = handler.request.path_url
    logger.debug('redirector link:%s', link)
    url = memcache.get(link)
    if url:
        logger.debug(
            'redirector memcache_hit link:%s target_url:%s', link, url)
        memcache_hit = True
    else:
        logger.debug(
            'redirector memcache_miss link:%s target_url:%s', link, url)
        url = str(Link.get_by_id(link).target_url)
        memcache_hit = False
    deferred.defer(log, os.environ['REQUEST_LOG_ID'], memcache_hit, link, url,
                   handler.request.cookies)
    return url


app = WSGIApplication([
    Route('/images/cleardot.gif', Cookie, methods=['GET']),
    Route('/', Create, methods=['POST']),
    Route('/<path>', RedirectHandler,
          methods=['GET'], defaults={'_uri': redirector}),
    Route('/', RedirectHandler, methods=['GET'],
          defaults={'_uri': 'http://detroitartmap.com'}),
], debug=True)


if __name__ == "__main__":
    run_wsgi_app(app)
