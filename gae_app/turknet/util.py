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


if __name__ == '__main__':
  import unittest

  class TestCase(unittest.TestCase):
    def test_cycle(self):
      cycle = Cycle(range(3))

      self.assertEqual(0, cycle.next())
      self.assertEqual(1, cycle.next())
      self.assertEqual(2, cycle.next())
      self.assertEqual(0, cycle.next())
      self.assertEqual(1, cycle.next())
      self.assertEqual(2, cycle.next())

    def test_index_decr(self):
      self.assertEqual(2, index_decr(0, 3))
      self.assertEqual(0, index_decr(1, 3))
      self.assertEqual(1, index_decr(2, 3))

  unittest.main()
