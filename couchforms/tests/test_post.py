import json
from django.utils.unittest.case import TestCase
import os
from couchforms.models import XFormInstance
from couchforms.util import post_from_settings


class PostTest(TestCase):

    def _test(self, name, any_id_ok=False):
        with open(os.path.join(os.path.dirname(__file__), 'data', '{name}.xml'.format(name=name))) as f:
            instance = f.read()
        doc_id, error = post_from_settings(instance)
        xform = XFormInstance.get(doc_id)

        try:
            xform_json = xform.to_json()
            with open(os.path.join(os.path.dirname(__file__), 'data', '{name}.json'.format(name=name))) as f:
                result = json.load(f)
            result['received_on'] = xform_json['received_on']
            result['_rev'] = xform_json['_rev']
            if any_id_ok:
                result['_id'] = xform_json['_id']
            self.assertEqual(xform_json, result)
        finally:
            xform.delete()

    def test_cloudant_template(self):
        self._test('cloudant-template')

    def test_decimalmeta(self):
        self._test('decimalmeta', any_id_ok=True)

    def test_duplicate(self):
        self._test('duplicate')

    def test_edit(self):
        self._test('edit')

    def test_meta(self):
        self._test('meta', any_id_ok=True)

    def test_meta_bad_username(self):
        self._test('meta_bad_username')

    def test_meta_dict_appversion(self):
        self._test('meta_dict_appversion')

    def test_namespaces(self):
        self._test('namespaces', any_id_ok=True)
