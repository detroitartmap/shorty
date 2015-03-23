import os
import logging


from google.appengine.ext import webapp
from google.appengine.ext.webapp import WSGIApplication
from google.appengine.ext.webapp import Route
from google.appengine.ext.webapp import RedirectHandler

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.ext import ndb

from models import Link


class Index(webapp.RequestHandler):

    def get(self):
        self.response.write('hello')

    def post(self):
#        if not users.is_current_user_admin():
#            self.abort(405)

        fields = ('target_url', 'short_path', 'utm_campaign', 'utm_source', 'utm_medium',
                  'utm_content')
        data = {k: self.request.get(k) for k in fields}
        data['user'] = users.get_current_user()

        for attemps in xrange(3):
            link = Link.new(**data).get()
            if link:
                break
        else:
            self.abort(400)

        memcache.set(link.url, link.target_url)

        self.response.write(link.json)


def get_redirect_url(handler, *args, **kwargs):
    link = handler.request.application_url
    url = memcache.get(link) or Link.get_by_id(link)
    return url or handler.abort(404)


app = WSGIApplication([
    Route('/', Index),
    Route('/(.+)', RedirectHandler, defaults={'_uri': get_redirect_url})
], debug=True)


if __name__ == "__main__":
    run_wsgi_app(app)
