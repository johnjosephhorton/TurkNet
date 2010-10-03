from boto.mturk.connection import MTurkConnection
from boto.mturk.question import ExternalQuestion


def connection(obj):
  return MTurkConnection(
    aws_access_key_id=obj.aws_access_key_id
  , aws_secret_access_key=obj.aws_secret_access_key
  , host=obj.aws_hostname
  )


def create_hit(experiment, url):
  return connection(experiment).create_hit(
    question=ExternalQuestion(url, experiment.hit_frame_height)
  , title=experiment.hit_title
  , description=experiment.hit_description
  , lifetime=experiment.hit_lifetime
  , max_assignments=experiment.hit_max_assignments
  , keywords=experiment.hit_keywords
  , duration=experiment.hit_duration
  , approval_delay=experiment.hit_approval_delay
  , reward=experiment.reward
  , response_groups=['Minimal', 'HITDetail', 'HITQuestion', 'HITAssignmentSummary']
  )
