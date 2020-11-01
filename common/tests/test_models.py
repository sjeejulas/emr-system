from datetime import datetime
from django.test import TestCase

from model_mommy import mommy

from accounts.models import MedidataUser


class SoftDeletionModelTest(TestCase):
    def setUp(self):
        self.medidata_user = mommy.make(MedidataUser, deleted_at=None)

    def test_deleted_at_is_null(self):
        self.assertIsNone(self.medidata_user.deleted_at)

    def test_delete(self):
        self.medidata_user.delete()
        self.assertEqual(type(self.medidata_user.deleted_at), datetime)

    def test_hard_delete(self):
        self.medidata_user.hard_delete()
        self.assertEqual(MedidataUser.objects.count(), 0)
