import hashlib
from django.conf import settings
from dimagi.utils.mixins import UnicodeMixIn
import urllib
try:
    import simplejson
except ImportError:
    from django.utils import simplejson

from couchforms.models import XFormInstance, XFormDuplicate, XFormError, XFormDeprecated,\
    SubmissionErrorLog
import logging
from couchdbkit.resource import RequestFailed
from couchforms.exceptions import CouchFormException
from couchforms.signals import xform_saved
from dimagi.utils.couch import uid
from dimagi.utils.couch.database import is_bigcouch, bigcouch_quorum_count, get_safe_write_kwargs, get_safe_read_kwargs
import re
from dimagi.utils.post import post_authenticated_data, post_unauthenticated_data
from restkit.errors import ResourceNotFound
from lxml import etree

class SubmissionError(Exception, UnicodeMixIn):
    """
    When something especially bad goes wrong during a submission, this 
    exception gets raised.
    """
    
    def __init__(self, error_log, *args, **kwargs):
        super(SubmissionError, self).__init__(*args, **kwargs)
        self.error_log = error_log
    
    def __str__(self):
        return str(self.error_log)

def post_from_settings(instance, extras=None):
    extras = extras or {}
    # HACK: for cloudant force update all nodes at once
    # to prevent 412 race condition
    extras.update(get_safe_write_kwargs())

    url = settings.XFORMS_POST_URL if not extras else "%s?%s" % \
        (settings.XFORMS_POST_URL, urllib.urlencode(extras))
    if settings.COUCH_USERNAME:
        return post_authenticated_data(instance, url, 
                                       settings.COUCH_USERNAME, 
                                       settings.COUCH_PASSWORD)
    else:
        return post_unauthenticated_data(instance, url)

def post_xform_to_couch(instance, attachments={}):
    """
    Post an xform to couchdb, based on the settings.XFORMS_POST_URL.
    Returns the newly created document from couchdb, or raises an
    exception if anything goes wrong.

    attachments is a dictionary of the request.FILES that are not the xform.  Key is the parameter name, and the value is the django MemoryFile object stream.
    """
    try:
        response, errors = post_from_settings(instance)
        if not _has_errors(response, errors):
            doc_id = response
            try:
                xform = XFormInstance.get(doc_id)
                #put attachments onto the saved xform instance
                for key, val in attachments.items():
                    res = xform.put_attachment(val, name=key, content_type=val.content_type, content_length=val.size)

                # fire signals
                # We don't trap any exceptions here. This is by design. 
                # If something fails (e.g. case processing), we quarantine the
                # form into an error location.
                xform_saved.send(sender="couchforms", xform=xform)
                return xform
            except Exception, e:
                logging.error("Problem with form %s" % doc_id)
                logging.exception(e)
                # "rollback" by changing the doc_type to XFormError
                try: 
                    bad = XFormError.get(doc_id)
                    bad.problem = "%s" % e
                    bad.save()
                    return bad
                except ResourceNotFound: 
                    pass # no biggie, the failure must have been in getting it back 
                raise
        else:
            raise CouchFormException("Problem POSTing form to couch! errors/response: %s/%s" % (errors, response))
    except RequestFailed, e:
        if e.status_int == 409:
            # this is an update conflict, i.e. the uid in the form was the same.
            return _handle_id_conflict(instance, attachments)
        else:
            doc = _log_hard_failure(instance, attachments, e)
            raise SubmissionError(doc)

def _has_errors(response, errors):
    return errors or "error" in response
    
    
def _handle_id_conflict(instance, attachments):
    """
    For id conflicts, we check if the files contain exactly the same content,
    If they do, we just log this as a dupe. If they don't, we deprecate the 
    previous form and overwrite it with the new form's contents.
    """
    def _extract_id_from_raw_xml(xml):
        
        # this is the standard openrosa way of doing things
        parsed = etree.XML(xml)
        meta_ns = "http://openrosa.org/jr/xforms"
        val = parsed.find("{%(ns)s}meta/{%(ns)s}instanceID" % \
                          {"ns": meta_ns})
        if val is not None and val.text:
            return val.text
        
        # if we get here search more creatively for some of the older
        # formats
        _PATTERNS = (r"<instanceID>([\w-]+)</instanceID>",
                     r"<uid>([\w-]+)</uid>",
                     r"<uuid>([\w-]+)</uuid>")
        for pattern in _PATTERNS:
            if re.search(pattern, xml): 
                return re.search(pattern, xml).groups()[0]
        
        logging.error("Unable to find conflicting matched uid in form: %s" % xml)
        return ""
    
    conflict_id = _extract_id_from_raw_xml(instance)
    
    # get old document
    existing_doc = XFormInstance.get(conflict_id)

    # compare md5s
    existing_md5 = existing_doc.xml_md5()
    new_md5 = hashlib.md5(instance).hexdigest()

    # if not same:
    # Deprecate old form (including changing ID)
    # to deprecate, copy new instance into a XFormDeprecated
    if existing_md5 != new_md5:
        doc_copy = XFormInstance.get_db().copy_doc(conflict_id)
        xfd = XFormDeprecated.get(doc_copy['id'], **get_safe_read_kwargs())
        xfd.orig_id = conflict_id
        xfd.doc_type=XFormDeprecated.__name__
        xfd.save()

        # after that delete the original document and resubmit.
        XFormInstance.get_db().delete_doc(conflict_id)
        return post_xform_to_couch(instance, attachments=attachments)
    else:
        # follow standard dupe handling
        new_doc_id = uid.new()
        response, errors = post_from_settings(instance, {"uid": new_doc_id})
        if not _has_errors(response, errors):
            # create duplicate doc
            # get and save the duplicate to ensure the doc types are set correctly
            # so that it doesn't show up in our reports
            dupe = XFormDuplicate.get(response)
            dupe.problem = "Form is a duplicate of another! (%s)" % conflict_id
            dupe.save()
            return dupe
        else:
            # how badly do we care about this?
            raise CouchFormException("Problem POSTing form to couch! errors/response: %s/%s" % (errors, response))

def _log_hard_failure(instance, attachments, error):
    """
    Handle's a hard failure from posting a form to couch. 
    
    Currently, it will save the raw payload to couch in a hard-failure doc
    and return that doc.
    """
    return SubmissionErrorLog.from_instance(instance, str(error))
    
    
def value_for_display(value, replacement_chars="_-"):
    """
    Formats an xform value for display, replacing the contents of the 
    system characters with spaces
    """
    for char in replacement_chars:
        value = str(value).replace(char, " ")
    return value
