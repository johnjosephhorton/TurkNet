from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext import db as datastore

from boto.exception import BotoClientError, BotoServerError

from turknet.models import worker_lookup

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

  def mturk_submit_url(self, worker):
    host_url = self.request.get('turkSubmitTo', 'https://www.mturk.com')

    params = {'assignmentId': worker.assignment_id, 'workerId': worker.id}

    return '%s/mturk/externalSubmit?%s' % (host_url, urllib.urlencode(params))

  def bad_request(self, text='Bad Request'):
    self.reply(400, text)

  def not_found(self, text='Not Found'):
    self.reply(404, text)

  def method_not_allowed(self, text='Method Not Allowed'):
    self.reply(405, text)

  def internal_server_error(self, text='Internal Server Error'):
    self.reply(500, text)


def throws_boto_errors(fn):
  def _fn(self, *args, **kwargs):
    try:
      return fn(self, *args, **kwargs)
    except (BotoClientError, BotoServerError), response:
      message = '%s: %s' % (response.errors[0][0], response.errors[0][1])

      self.internal_server_error(message)

  return _fn


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


def worker_required(fn):
  def _fn(self, *args, **kwargs):
    worker_id = self.request.get('workerId', None)

    assignment_id = self.request.get('assignmentId', None)

    if worker_id is None:
      self.bad_request('No workerId')
    elif assignment_id is None:
      self.bad_request('No assignmentId')
    else:
      try:
        self.worker = worker_lookup(worker_id, assignment_id)

        if self.worker is None:
          self.not_found()
        else:
          return fn(self, *args, **kwargs)
      except datastore.BadKeyError:
        self.not_found()

  return _fn
