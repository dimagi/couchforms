import os
from datetime import date
from django.conf import settings
from django.test import TestCase
from dimagi.utils.post import post_authenticated_data
from couchforms.models import XFormInstance

class TestMeta(TestCase):
    
    def testClosed(self):
        file_path = os.path.join(os.path.dirname(__file__), "data", "meta.xml")
        xml_data = open(file_path, "rb").read()
        doc_id, errors = post_authenticated_data(xml_data, 
                                                 settings.XFORMS_POST_URL, 
                                                 settings.COUCH_USERNAME,
                                                 settings.COUCH_PASSWORD)
        xform = XFormInstance.get(doc_id)
        self.assertNotEqual(None, xform.metadata)
        self.assertEqual(date(2010,07,22), xform.metadata.timeStart.date())
        self.assertEqual(date(2010,07,23), xform.metadata.timeEnd.date())
        self.assertEqual("admin", xform.metadata.username)
        self.assertEqual("f7f0c79e-8b79-11df-b7de-005056c00008", xform.metadata.userID)

    def testSurviveMissingDates(self):
        file_path = os.path.join(os.path.dirname(__file__), "data", "no-dates.xml")
        xml_data = open(file_path, "rb").read()
        doc_id, errors = post_authenticated_data(xml_data, 
                                                 settings.XFORMS_POST_URL, 
                                                 settings.COUCH_USERNAME,
                                                 settings.COUCH_PASSWORD)
        xform = XFormInstance.get(doc_id)
        xforms_by_xmlns = XFormInstance.view('couchforms/counts_by_type', startkey=[xform.xmlns], endkey=[xform.xmlns, {}], reduce=False)

        vacuous = True
        for row in xforms_by_xmlns:
            if row['id'] == xform.get_id:
                vacuous = False
                self.assertEqual(row['key'][1:], [1970, 0, 1]) # Javascript months start at zero
        self.assertFalse(vacuous) # Make sure we did actually test something
