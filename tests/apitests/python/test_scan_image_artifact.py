from __future__ import absolute_import
import unittest
import sys

from testutils import harbor_server
from testutils import TEARDOWN
from testutils import ADMIN_CLIENT
from library.project import Project
from library.user import User
from library.repository import Repository
from library.repository import push_image_to_project
from library.artifact import Artifact
from library.scan import Scan
from library.scanner import Scanner
from library.sign import sign_image

class TestScan(unittest.TestCase):
    @classmethod
    def setUp(self):
        self.project= Project()
        self.user= User()
        self.artifact = Artifact()
        self.repo = Repository()
        self.scan = Scan()
        self.scanner = Scanner()

        self.url = ADMIN_CLIENT["endpoint"]
        self.user_password = "Aa123456"
        self.project_id, self.project_name, self.user_id, self.user_name = [None] * 4
        self.user_id, self.user_name = self.user.create_user(user_password = self.user_password, **ADMIN_CLIENT)
        self.USER_CLIENT = dict(with_signature = True, with_immutable_status = True, endpoint = self.url, username = self.user_name, password = self.user_password, with_scan_overview = True)


        #2. Create a new private project(PA) by user(UA);
        self.project_id, self.project_name = self.project.create_project(metadata = {"public": "false"}, **ADMIN_CLIENT)

        #3. Add user(UA) as a member of project(PA) with project-admin role;
        self.project.add_project_members(self.project_id, user_id = self.user_id, **ADMIN_CLIENT)

    @classmethod
    def tearDown(self):
        print("Case completed")

    @unittest.skipIf(TEARDOWN == True, "Test data won't be erased.")
    def test_ClearData(self):
        #1. Delete repository(RA) by user(UA);
        self.repo.delete_repoitory(self.project_name, TestScan.repo_name.split('/')[1], **self.USER_CLIENTT)

        #2. Delete project(PA);
        self.project.delete_project(self.project_id, **self.USER_CLIENT)

        #3. Delete user(UA);
        self.user.delete_user(self.user_id, **ADMIN_CLIENT)

    def testScanImageArtifact(self):
        """
        Test case:
            Scan An Image Artifact
        Test step and expected result:
            1. Create a new user(UA);
            2. Create a new private project(PA) by user(UA);
            3. Add user(UA) as a member of project(PA) with project-admin role;
            4. Get private project of user(UA), user(UA) can see only one private project which is project(PA);
            5. Create a new repository(RA) and tag(TA) in project(PA) by user(UA);
            6. Send scan image command and get tag(TA) information to check scan result, it should be finished;
            7. Swith Scanner;
            8. Send scan another image command and get tag(TA) information to check scan result, it should be finished.
        Tear down:
            1. Delete repository(RA) by user(UA);
            2. Delete project(PA);
            3. Delete user(UA);
        """

        #4. Get private project of user(UA), user(UA) can see only one private project which is project(PA);
        self.project.projects_should_exist(dict(public=False), expected_count = 1,
            expected_project_id = self.project_id, **self.USER_CLIENT)

        #Note: Please make sure that this Image has never been pulled before by any other cases,
        #      so it is a not-scanned image right after repository creation.
        image = "docker"
        src_tag = "1.13"
        #5. Create a new repository(RA) and tag(TA) in project(PA) by user(UA);
        TestScan.repo_name, tag = push_image_to_project(self.project_name, harbor_server, self.user_name, self.user_password, image, src_tag)

        #6. Send scan image command and get tag(TA) information to check scan result, it should be finished;
        self.scan.scan_artifact(self.project_name, TestScan.repo_name.split('/')[1], tag, **self.USER_CLIENT)
        self.artifact.check_image_scan_result(self.project_name, image, tag, **self.USER_CLIENT)

        #7. Swith Scanner;
        uuid = self.scanner.scanners_get_uuid(**ADMIN_CLIENT)
        self.scanner.scanners_registration_id_patch(uuid, **ADMIN_CLIENT)

        image = "tomcat"
        src_tag = "latest"
        TestScan.repo_name, tag = push_image_to_project(self.project_name, harbor_server, self.user_name, self.user_password, image, src_tag)
        #8. Send scan another image command and get tag(TA) information to check scan result, it should be finished.
        self.scan.scan_artifact(self.project_name, TestScan.repo_name.split('/')[1], tag, **self.USER_CLIENT)
        self.artifact.check_image_scan_result(self.project_name, image, tag, **self.USER_CLIENT)

    def testScanSignedImage(self):
        """
        Test case:
            Scan A Signed Image
        Test step and expected result:
            1. Create a new user(UA);
            2. Create a new private project(PA) by user(UA);
            3. Add user(UA) as a member of project(PA) with project-admin role;
            4. Get private project of user(UA), user(UA) can see only one private project which is project(PA);
            5. Create a new repository(RA) and tag(TA) in project(PA) by user(UA);
            6. Send scan image command and get tag(TA) information to check scan result, it should be finished;
            7. Swith Scanner;
            8. Send scan another image command and get tag(TA) information to check scan result, it should be finished.
        Tear down:
            1. Delete repository(RA) by user(UA);
            2. Delete project(PA);
            3. Delete user(UA);
        """

        #Note: Please make sure that this Image has never been pulled before by any other cases,
        #      so it is a not-scanned image right after repository creation.
        image = "redis"
        tag = "latest"
        #5. Create a new repository(RA) and tag(TA) in project(PA) by user(UA);
        TestScan.repo_name_1, tag = push_image_to_project(self.project_name, harbor_server, self.user_name, self.user_password, image, tag)

        sign_image(harbor_server, self.project_name, image, tag)

        #6. Send scan image command and get tag(TA) information to check scan result, it should be finished;
        self.scan.scan_artifact(self.project_name, TestScan.repo_name_1.split('/')[1], tag, **self.USER_CLIENT)
        self.artifact.check_image_scan_result(self.project_name, image, tag, **self.USER_CLIENT)

if __name__ == '__main__':
    suite = unittest.TestSuite(unittest.makeSuite(TestScan))
    result = unittest.TextTestRunner(sys.stdout, verbosity=2, failfast=True).run(suite)
    if not result.wasSuccessful():
        raise Exception(r"Tag immutability test failed: {}".format(result))