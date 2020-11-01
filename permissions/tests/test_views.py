from django.test import TestCase
from model_mommy import mommy
from accounts.models import User, MedidataUser, ClientUser, GeneralPracticeUser,\
        MEDIDATA_USER, GENERAL_PRACTICE_USER, CLIENT_USER
from django.contrib.auth.models import Permission
from permissions.model_choices import MANAGER_PERMISSIONS, GP_PERMISSIONS,\
        OTHER_PERMISSIONS, CLIENT_ADMIN_PERMISSIONS, MEDI_PERMISSIONS,\
        MEDI_ADMIN_PERMISSIONS, MEDI_TEAM_PERMISSIONS, CLIENT_MANAGER_PERMISSIONS


class PermissionTestCase(TestCase):
    def setUp(self):
        self.user = mommy.make(User, type=GENERAL_PRACTICE_USER)
        mommy.make(GeneralPracticeUser, user=self.user)
        self.client.force_login(self.user, backend=None)


class UserManagementWithoutPermissionTest(PermissionTestCase):
    def test_view_user_management(self):
        response = self.client.get('/accounts/view-users/')
        self.assertEqual(302, response.status_code)

    def test_add_user_management(self):
        response = self.client.get('/accounts/create-user/')
        self.assertEqual(302, response.status_code)

    def test_update_permission(self):
        response = self.client.get('/accounts/update-permission/')
        self.assertEqual(302, response.status_code)


class UserManagementTest(PermissionTestCase):
    def test_view_user_management(self):
        permission = Permission.objects.get(codename='view_user_management')
        self.user.user_permissions.add(permission)
        response = self.client.get('/accounts/view-users/')
        self.assertEqual(200, response.status_code)

    def test_add_user_management(self):
        permission = Permission.objects.get(codename='add_user_management')
        self.user.user_permissions.add(permission)
        response = self.client.get('/accounts/create-user/')
        self.assertEqual(200, response.status_code)

    def test_update_permission(self):
        permission = Permission.objects.get(codename='change_instructionpermission')
        self.user.user_permissions.add(permission)
        response = self.client.get('/accounts/update-permission/')
        self.assertEqual(response.url, '/accounts/view-users/?show=True')


class AutoAssignPermissionGP(TestCase):
    def setUp(self):
        self.user = mommy.make(User, type=GENERAL_PRACTICE_USER)
        self.client.force_login(self.user, backend=None)

    def test_permission_manager(self):
        mommy.make(
            GeneralPracticeUser,
            user=self.user,
            role=GeneralPracticeUser.PRACTICE_MANAGER,
        )
        for permission in self.user.user_permissions.all():
            permission_verify = permission.codename in MANAGER_PERMISSIONS
            self.assertEqual(permission_verify, True)

    def test_permission_gp(self):
        mommy.make(
            GeneralPracticeUser,
            user=self.user,
            role=GeneralPracticeUser.GENERAL_PRACTICE,
        )
        for permission in self.user.user_permissions.all():
            permission_verify = permission.codename in GP_PERMISSIONS
            self.assertEqual(permission_verify, True)

    def test_permission_other(self):
        mommy.make(
            GeneralPracticeUser,
            user=self.user,
            role=GeneralPracticeUser.OTHER_PRACTICE,
        )
        for permission in self.user.user_permissions.all():
            permission_verify = permission.codename in OTHER_PERMISSIONS
            self.assertEqual(permission_verify, True)


class AutoAssignPermissionMedi(TestCase):
    def setUp(self):
        self.user = mommy.make(User, type=MEDIDATA_USER)
        self.client.force_login(self.user, backend=None)

    def test_permission_medi_super_user(self):
        mommy.make(
            MedidataUser,
            user=self.user,
            role=MedidataUser.MEDI_SUPER_USER
        )
        self.assertEqual(self.user.is_superuser, True)

    def test_permission_medi_admin(self):
        mommy.make(
            MedidataUser,
            user=self.user,
            role=MedidataUser.MEDI_ADMIN
        )
        for permission in self.user.user_permissions.all():
            permission_verify = permission.codename in MEDI_ADMIN_PERMISSIONS
            self.assertEqual(permission_verify, True)

    def test_permission_medi_team(self):
        mommy.make(
            MedidataUser,
            user=self.user,
            role=MedidataUser.MEDI_TEAM
        )
        for permission in self.user.user_permissions.all():
            permission_verify = permission.codename in MEDI_TEAM_PERMISSIONS
            self.assertEqual(permission_verify, True)

class AutoAssignPermissionClient(TestCase):
    def setUp(self):
        self.user = mommy.make(User, type=CLIENT_USER)
        self.client.force_login(self.user, backend=None)

    def test_permission_client(self):
        mommy.make(
            ClientUser,
            user=self.user,
            role=ClientUser.CLIENT_ADMIN,
        )
        for permission in self.user.user_permissions.all():
            permission_verify = permission.codename in CLIENT_ADMIN_PERMISSIONS
            self.assertEqual(permission_verify, True)

    def test_permission_admin(self):
        mommy.make(
            ClientUser,
            user=self.user,
            role=ClientUser.CLIENT_MANAGER,
        )
        for permission in self.user.user_permissions.all():
            permission_verify = permission.codename in CLIENT_MANAGER_PERMISSIONS
            self.assertEqual(permission_verify, True)
