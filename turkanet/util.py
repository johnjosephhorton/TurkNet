import os, hashlib


def nonce():
  sha = hashlib.sha1()

  sha.update(os.urandom(40))

  return sha.hexdigest()
