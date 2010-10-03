from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext import db as datastore

from django.utils import simplejson as json

import cgi, urllib


class RequestHandler(webapp.RequestHandler):
  def write(self, data):
    self.response.out.write(data)

  def render(self, path, params):
    self.write(template.render(path, params))

  def inspect(self, obj):
    self.write(cgi.escape(repr(obj)))

  def reply(self, code, text):
    self.response.set_status(code)

    self.write(cgi.escape(text))

  def json(self, data):
    self.response.headers['Content-Type'] = 'application/json'

    self.write(json.dumps(data))

  def host_url(self, path, query_params={}):
    if len(query_params) > 0:
      return '%s%s?%s' % (self.request.host_url, path, urllib.urlencode(query_params))
    else:
      return '%s%s' % (self.request.host_url, path)

  def bad_request(self, text='Bad Request'):
    self.reply(400, text)

  def not_found(self, text='Not Found'):
    self.reply(404, text)

  def method_not_allowed(self, text='Method Not Allowed'):
    self.reply(405, text)


def entity_required(model, attr):
  def _decorate(fn):
    def _wrapper_fn(self, *args, **kwargs):
      key = self.request.get('key', None)

      if key is None:
        self.bad_request('No key')
      else:
        try:
          setattr(self, attr, model.get(key))

          if getattr(self, attr) is None:
            self.not_found()
          else:
            return fn(self, *args, **kwargs)
        except datastore.BadKeyError:
          self.not_found()

    return _wrapper_fn
  return _decorate
