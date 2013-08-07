#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

SECRET_KEY = 'this is not a secret key'

INSTALLED_APPS = (
    'couchdbkit.ext.django',
    'couchforms',
    'coverage'
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'couchforms',
    }
}



####### Couch Config ######
COUCH_HTTPS = False # recommended production value is True if enabling https
COUCH_SERVER_ROOT = '127.0.0.1:5984' #6984 for https couch
COUCH_USERNAME = ''
COUCH_PASSWORD = ''
COUCH_DATABASE_NAME = 'couchforms'

COUCHDB_DATABASES = [
    ('couchforms', 'http://127.0.0.1:5984/couchforms'),
    ('couch', 'http://127.0.0.1:5984/couchforms'), # Why?
]


# Hardcode the test database?
XFORMS_POST_URL = "http://127.0.0.1:5984/couchforms_test/_design/couchforms/_update/xform/" 

TEST_RUNNER = 'couchdbkit.ext.django.testrunner.CouchDbKitTestSuiteRunner'

####### # Email setup ########
# Print emails to console so there is no danger of spamming, but you can still get registration URLs
EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'
EMAIL_LOGIN = "nobody@example.com"
EMAIL_PASSWORD = "******"
EMAIL_SMTP_HOST = "smtp.example.com"
EMAIL_SMTP_PORT = 587

COVERAGE_REPORT_HTML_OUTPUT_DIR='coverage-html'
COVERAGE_MODULE_EXCLUDES= ['tests$', 'settings$', 'urls$', 'locale$',
                           'common.views.test', '^django', 'management', 'migrations',
                           '^south', '^djcelery', '^debug_toolbar', '^rosetta']
