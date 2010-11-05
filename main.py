from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app as run_wsgi

from turkanet.http import RequestHandler, entity_required
from turkanet.models import Experiment, Worker, Labeling, Evaluation, worker_lookup
from turkanet.util import nonce
from turkanet import mturk

import yaml


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


class FirstStage(RequestHandler):
  @entity_required(Experiment, 'experiment')
  def get(self):
    assignment_id = self.request.get('assignmentId', None)

    if assignment_id is None:
      self.not_found()
    elif assignment_id == 'ASSIGNMENT_ID_NOT_AVAILABLE':
      self.render('priv/hit_preview.html', {'experiment': self.experiment})
    else:
      worker_id = self.request.get('workerId')

      worker = worker_lookup(worker_id, assignment_id)

      if worker is None:
        worker = Worker()
        worker.id = worker_id
        worker.assignment_id = assignment_id
        worker.experiment = self.experiment
        worker.nonce = nonce()
        worker.put()

      self.render('priv/hit_accepted.html', {
        'image_url': 'TODO'
      , 'form_action': self.request.url
      })

  # @worker_required
  # @entity_required(Experiment, 'experiment')
  # def post(self):
  #   labeling = Labeling()
  #   labeling.image_url = TODO
  #   labeling.worker = self.worker
  #   labeling.labels = self.request.get_all('label')
  #   labeling.time = int(self.request.get('time'))
  #   labeling.put()
  # 
  #   location = self.mturk_submit_url(self.worker)
  # 
  #   self.redirect(location)


def handlers():
  return [
    ('/', Root)
  , ('/upload', Upload)
  , ('/hit', FirstStage)
  ]


def application():
  return webapp.WSGIApplication(handlers(), debug=True)


def main():
  run_wsgi(application())


if __name__ == '__main__':
  main()
