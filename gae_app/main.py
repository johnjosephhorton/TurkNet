from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app as run_wsgi
from google.appengine.api.labs import taskqueue

from turknet.http import RequestHandler, entity_required, worker_required
from turknet.models import Experiment, Worker, Labeling, Evaluation
from turknet.models import worker_lookup, experiment_grouping_already_started
from turknet.util import nonce
from turknet import mturk

from datetime import datetime

import yaml


class Root(RequestHandler):
  def get(self):
    self.write('OK')


class Upload(RequestHandler):
  def get(self):
    self.render('priv/upload.html', {'action': self.request.url})

  @throws_boto_errors
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

      self.render('priv/first_stage_labeling.html', {
        'image_url': self.experiment.images[0]
      , 'form_action': self.request.url
      })

  @worker_required
  @entity_required(Experiment, 'experiment')
  def post(self):
    labeling = Labeling()
    labeling.image_url = self.experiment.images[0]
    labeling.worker = self.worker
    labeling.labels = self.request.get_all('label')
    labeling.time = int(self.request.get('time'))
    labeling.put()

    self.render('priv/first_stage_complete.html', {})


class Cron(RequestHandler):
  def get(self):
    experiments = Experiment.all().filter('second_stage_started = ', None)

    for experiment in experiments:
      worker_count = 0

      for worker in Worker.all().filter('experiment = ', experiment):
        if Labeling.all().filter('worker = ', worker).filter('image_url = ', experiment.images[0]).get():
          worker_count += 1

      if worker_count == experiment.cohort_size * experiment.cohort_count:
        taskqueue.add(queue_name='worker_grouping', params={'key': experiment.key()})

        experiment.second_stage_started = datetime.now()
        experiment.put()


class WorkerGroupingTask(RequestHandler):
  @entity_required(Experiment, 'experiment')
  def post(self):
    if experiment_grouping_already_started(self.experiment): # be idempotent
      return

    cycle = Cycle(range(experiment.cohort_count))

    for worker in Worker.all().filter('experiment = ', experiment):
      worker.cohort_index = cycle.next()

      # TODO: if worker.cohort_index == 0:
      # TODO:   taskqueue.add(queue_name='worker_notification', params={'key': worker.key()})

      worker.put()


def handlers():
  return [
    ('/', Root)
  , ('/upload', Upload)
  , ('/hit', FirstStage)
  , ('/cron', Cron)
  , ('/_ah/queue/worker_grouping', WorkerGroupingTask)
  ]


def application():
  return webapp.WSGIApplication(handlers(), debug=True)


def main():
  run_wsgi(application())


if __name__ == '__main__':
  main()
