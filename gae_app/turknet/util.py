import os, hashlib


class Cycle(object):
  def __init__(self, values):
    self.values = values

    self.length = len(values)

    self.index = 0

  def next(self):
    value = self.values[self.index]

    self.index = (self.index + 1) % self.length

    return value


def nonce():
  sha = hashlib.sha1()

  sha.update(os.urandom(40))

  return sha.hexdigest()


def index_decr(value, length):
  if value == 0:
    return length - 1
  else:
    return value - 1
