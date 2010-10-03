from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app as run_wsgi

from django.utils import simplejson as json

from turkanet.models import Experiment, Worker, Labeling, Evaluation
from turkanet import mturk

import cgi, yaml, urllib


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


class Root(RequestHandler):
  def get(self):
    self.write('OK')


class Upload(RequestHandler):
  def get(self):
    self.render('priv/upload.html', {'action': self.request.url})

  def post(self):
    experiment = Experiment()

    for (k, v) in yaml.load(self.request.get('file')).iteritems():
      setattr(experiment, k, v)

    experiment.put()

    response = mturk.create_hit(experiment, self.host_url('/hit', {'key': experiment.key()}))

    if response.status is True:
      experiment.hit_id = response[0].HITId
      experiment.put()

      self.reply(201, 'Created HIT: ' + experiment.hit_id)
    else:
      self.reply(500, 'Bad Mechanical Turk response: ' + repr(response))


class HIT(RequestHandler):
  def get(self):
    self.write('TODO')


def handlers():
  return [
    ('/', Root)
  , ('/upload', Upload)
  , ('/hit', HIT)
  ]


def application():
  return webapp.WSGIApplication(handlers(), debug=True)


def main():
  run_wsgi(application())


if __name__ == '__main__':
  main()
