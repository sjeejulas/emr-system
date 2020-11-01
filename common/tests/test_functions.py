from django.test import TestCase
from common.functions import aes_with_salt_encryption, aes_with_salt_decryption

import random
import string


class MultiGetattrTest(TestCase):
    pass


class AesWithSaltTest(TestCase):
    def setUp(self):
        self.salt = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        self.plaintext = 'Medidata 2018'
        self.iv_salt = ''
        self.iv_aes_key = ''

    def test_aed_with_salt_encryption(self):
        self.iv_salt, self.iv_aes_key, self.ciphertext = aes_with_salt_encryption(self.plaintext, self.salt)
        self.assertEqual(type(self.iv_salt), str)
        self.assertEqual(type(self.iv_aes_key), str)
        self.assertNotEqual(self.ciphertext, self.plaintext)

        initial_vector = '{iv_salt}${iv_aes_key}'.format(iv_salt=self.iv_salt, iv_aes_key=self.iv_aes_key)
        salt_with_cyphertext = '{salt}${ciphertext}'.format(salt=self.salt, ciphertext=self.ciphertext)

        dummy_salt = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        dummy_salt_with_cyphertext = '{salt}${ciphertext}'.format(salt=dummy_salt, ciphertext=self.ciphertext)

        self.assertEqual(self.plaintext, aes_with_salt_decryption(salt_with_cyphertext, initial_vector))
        self.assertRaises(ValueError, aes_with_salt_decryption(dummy_salt_with_cyphertext, initial_vector))
