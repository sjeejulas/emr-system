class DummyUser(object):
    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name


class DummyPatient(object):
    def __init__(self, first_name, last_name, date_of_birth):
        self.user = DummyUser(first_name, last_name)
        self.date_of_birth = date_of_birth


class DummyPractice(object):
    def __init__(self, emis_username, emis_password, external_organisation_id):
        self.emis_username = emis_username
        self.emis_password = emis_password
        self.external_organisation_id = external_organisation_id


class DummySnomedConcept(object):
    def __init__(self):
        self.external_id = 365981007
        self.id = 226057
        self.fsn_description = 'Finding of tobacco smoking behavior (finding)'
        self.created_at = '2018-01-12 10:55:14.0'
        self.updated_at = '2018-01-12 10:55:14.0'
        self.external_fsn_description_id = 772426012
        self.file_path = 'uk_sct2cl_23.0.0_20170401000001/SnomedCT_InternationalRF2_Production_20170131T120000/Snapshot/Terminology/sct2_Concept_Snapshot_INT_20170131.txt'
        self.tsvector_content_fsn_description = "'behavior':5 'find':1,6 'smoke':4 'tobacco':3"
