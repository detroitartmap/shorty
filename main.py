import logging
FORMAT = "[%(levelname)s %(asctime)s %(filename)s:%(lineno)s] %(funcName)20s()  %(message)s"
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)

from google.appengine.ext import webapp
from google.appengine.ext.webapp import WSGIApplication
from google.appengine.ext.webapp import Route
from google.appengine.ext.webapp import RedirectHandler

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache

from models import Link


class Create(webapp.RequestHandler):
    def post(self):
#        if not users.is_current_user_admin():
#            self.abort(405)
        fields = ('target_url', 'path', 'utm_campaign', 'utm_source',
                    'utm_medium', 'utm_content')
        data = {k: self.request.get(k) for k in fields}
        link = Link.create(**data).get()
        return self.response.write(link.json) if link else self.abort(400)


def redirector(handler, *args, **kwargs):
    link = handler.request.path_url
    logger.debug('redirector link:%s', link)
    url = str(memcache.get(link)) or str(Link.get_by_id(link).target_url)
    logger.debug('redirector target_url:%s', url)
    return url


app = WSGIApplication([
    Route('/', Create, methods=['POST']),
    Route('/<path>', RedirectHandler, methods=['GET'], defaults={'_uri': redirector}),
    Route('/', RedirectHandler, methods=['GET'],
          defaults={'_uri':'http://detroitartmap.com'}),
], debug=True)


if __name__ == "__main__":
    run_wsgi_app(app)
