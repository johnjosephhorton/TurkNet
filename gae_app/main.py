from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app as run_wsgi
from google.appengine.api.labs import taskqueue

from turknet.http import RequestHandler, throws_boto_errors, entity_required, worker_required, token_required
from turknet.models import Experiment, Worker, Labeling, Evaluation
from turknet.models import worker_lookup, worker_evaluation, experiment_grouping_already_started
from turknet.util import nonce, index_decr
from turknet import mturk

from datetime import datetime

import yaml, random


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

      if worker.has_labeled_an_image():
        self.render('priv/first_stage_complete.html', {})
      else:
        self.render('priv/labeling_form.html', {
          'image_url': self.experiment.images[0]
        , 'form_action': self.request.url
        })

  @worker_required
  @entity_required(Experiment, 'experiment')
  def post(self):
    if not self.worker.has_labeled_an_image():
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
        if worker.has_labeled_an_image():
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

    cycle = Cycle(range(self.experiment.cohort_count))

    workers, peer_workers = [], {}

    for worker in Worker.all().filter('experiment = ', self.experiment):
      worker.cohort_index = cycle.next()

      workers.append(worker)

      if peer_workers.has_key(worker.cohort_index):
        peer_workers[worker.cohort_index].append(worker)
      else:
        peer_workers[worker.cohort_index] = [worker]

    for worker in workers:
      previous_cohort_index = index_decr(worker.cohort_index, self.experiment.cohort_count)

      previous_cohort = peer_workers[previous_cohort_index]

      worker.peer_worker = previous_cohort.pop(random.randrange(len(previous_cohort)))
      worker.put()

      if worker.cohort_index == 0:
        taskqueue.add(queue_name='worker_notification', params={'key': worker.key()})


class WorkerNotificationTask(RequestHandler):
  @entity_required(Worker, 'worker')
  @throws_boto_errors
  def post(self):
    labeling = self.worker.peer_worker.labelings.order('-created').get()

    evaluation = Evaluation()
    evaluation.worker = self.worker
    evaluation.labeling = labeling
    evaluation.put()

    connection = mturk.connection(self.worker.experiment)

    url = self.host_url('/second_stage/evaluation', {'token': self.worker.nonce})

    message_text = template.render('priv/notification_message.txt', {'url': url})

    connection._process_request('NotifyWorkers', {
      'WorkerId': self.worker.id
    , 'Subject': 'Second part of Mechanical Turk task'
    , 'MessageText': message_text
    })

    self.write('OK')


class SecondStageEvaluation(RequestHandler):
  @token_required
  def get(self):
    self.render('priv/evaluation_form.html', {
      'labeling': worker_evaluation(self.worker).labeling
    , 'form_action': self.request.url
    })

  @token_required
  def post(self):
    evaluation = worker_evaluation(self.worker)

    evaluation.bonus_split = self.request.get('bonus_split')
    evaluation.approval = self.request.get('approve') == 'true'
    evaluation.put()

    self.redirect('/second_stage/labeling?token=' + self.token)


class SecondStageLabeling(RequestHandler):
  def image_url(self, worker):
    if worker.cohort_index % 2 == 0: # even cohort *index*, odd cohort *number*
      return worker.experiment.images[1]
    else:
      return worker.experiment.images[2]

  @token_required
  def get(self):
    self.render('priv/labeling_form.html', {
      'image_url': self.image_url(self.worker)
    , 'form_action': self.request.url
    })

  @token_required
  def post(self):
    labeling = Labeling()
    labeling.image_url = self.image_url(self.worker)
    labeling.worker = self.worker
    labeling.labels = self.request.get_all('label')
    labeling.time = int(self.request.get('time'))
    labeling.put()

    evaluator = Worker.all().filter('peer_worker = ', self.worker).get()

    taskqueue.add(queue_name='worker_notification', params={'key': evaluator.key()})

    self.redirect(self.mturk_submit_url())


def handlers():
  return [
    ('/', Root)
  , ('/upload', Upload)
  , ('/hit', FirstStage)
  , ('/cron', Cron)
  , ('/_ah/queue/worker_grouping', WorkerGroupingTask)
  , ('/_ah/queue/worker_notification', WorkerNotificationTask)
  , ('/second_stage/evaluation', SecondStageEvaluation)
  , ('/second_stage/labeling', SecondStageLabeling)
  ]


def application():
  return webapp.WSGIApplication(handlers(), debug=True)


def main():
  run_wsgi(application())


if __name__ == '__main__':
  main()
