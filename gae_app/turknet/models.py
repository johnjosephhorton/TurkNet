from google.appengine.ext import db as datastore


def worker_lookup(worker_id, assignment_id):
  return Worker.all().filter('id = ', worker_id).filter('assignment_id = ', assignment_id).get()


def experiment_grouping_already_started(experiment):
  def _fn(key):
    entity = datastore.get(key)

    if entity.second_stage_grouping_started:
      return True
    else:
      entity.second_stage_grouping_started = datetime.now()
      entity.put()
      return False

  return datastore.run_in_transaction(_fn, experiment.key())


class Experiment(datastore.Model):
  created = datastore.DateTimeProperty(auto_now_add=True)
  second_stage_started = datastore.DateTimeProperty()
  second_stage_grouping_started = datastore.DateTimeProperty()
  aws_access_key_id = datastore.StringProperty()
  aws_secret_access_key = datastore.StringProperty()
  aws_hostname = datastore.StringProperty()
  hit_id = datastore.StringProperty()
  hit_title = datastore.StringProperty()
  hit_description = datastore.StringProperty()
  hit_lifetime = datastore.IntegerProperty()
  hit_max_assignments = datastore.IntegerProperty()
  hit_keywords = datastore.StringListProperty()
  hit_duration = datastore.IntegerProperty()
  hit_approval_delay = datastore.IntegerProperty()
  hit_frame_height = datastore.IntegerProperty()
  hit_reward = datastore.StringProperty()
  cohort_count = datastore.IntegerProperty()
  cohort_size = datastore.IntegerProperty()
  images = datastore.StringListProperty()


class Worker(datastore.Model):
  created = datastore.DateTimeProperty(auto_now_add=True)
  id = datastore.StringProperty()
  assignment_id = datastore.StringProperty()
  experiment = datastore.ReferenceProperty(Experiment)
  peer_worker = datastore.SelfReferenceProperty()
  cohort_index = datastore.IntegerProperty()
  nonce = datastore.StringProperty()


class Labeling(datastore.Model):
  created = datastore.DateTimeProperty(auto_now_add=True)
  image_url = datastore.StringProperty()
  worker = datastore.ReferenceProperty(Worker)
  labels = datastore.StringListProperty()
  time = datastore.IntegerProperty()


class Evaluation(datastore.Model):
  created = datastore.DateTimeProperty(auto_now_add=True)
  labeling = datastore.ReferenceProperty(Labeling)
  worker = datastore.ReferenceProperty(Worker)
  bonus_split = datastore.IntegerProperty()
  approval = datastore.BooleanProperty()
