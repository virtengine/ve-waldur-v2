import collections
import os
import re

from jira import JIRA, JIRAError, utils
from jira.resources import Attachment, RequestType, User
from jira.utils import json_loads
from requests import Request

PADDING = 3
CHARS_LIMIT = 255


def _get_filename(path):
    limit = CHARS_LIMIT - PADDING
    fname = os.path.basename(path)
    filename = fname.split('.')[0]
    filename_extension = fname.split('.')[1:]
    count = (
        len('.'.join(filename_extension).encode('utf-8')) + 1
        if filename_extension
        else 0
    )
    char_limit = 0

    for char in filename:
        count += len(char.encode('utf-8'))
        if count > limit:
            break
        else:
            char_limit += 1

    if not char_limit:
        raise JIRAError('Attachment filename is very long.')

    tmp = [filename[:char_limit]]
    tmp.extend(filename_extension)
    filename = '.'.join(tmp)
    return filename


def _upload_file(manager, issue, upload_file, filename):
    # This method will fix original method jira.JIRA.add_attachment (jira/client.py line 591)
    url = manager._get_url('issue/' + str(issue) + '/attachments')
    files = {
        'file': (filename, upload_file),
    }
    headers = {
        'X-Atlassian-Token': 'nocheck',
    }
    req = Request('POST', url, headers=headers, files=files, auth=manager._session.auth)
    prepped = req.prepare()
    prepped.body = re.sub(
        b'filename=.*', b'filename="%s"\r' % filename.encode('utf-8'), prepped.body
    )
    r = manager._session.send(prepped)

    js = utils.json_loads(r)

    if not js or not isinstance(js, collections.Iterable):
        raise JIRAError("Unable to parse JSON: %s" % js)

    attachment = Attachment(manager._options, manager._session, js[0])

    if attachment.size == 0:
        raise JIRAError(
            "Added empty attachment?!: r: %s\nattachment: %s" % (r, attachment)
        )

    return attachment


def add_attachment(manager, issue, path):
    """
    Replace jira's method 'add_attachment' while don't well fixed this issue
    https://github.com/shazow/urllib3/issues/303
    And we need to set filename limit equaled 252 chars.
    :param manager: [jira.JIRA instance]
    :param issue: [jira.JIRA.resources.Issue instance]
    :param path: [string]
    :return: [jira.JIRA.resources.Attachment instance]
    """
    filename = _get_filename(path)

    with open(path, 'rb') as f:
        return _upload_file(manager, issue, f, filename)


def service_desk(manager, id_or_key):
    """In Jira v8.7.1 / SD 4.7.1 a Service Desk ID must be an integer.
    We use a hackish workaround to make it work till Atlassian resolves bug
    https://jira.atlassian.com/browse/JSDSERVER-4877.
    """
    try:
        return manager.service_desk(id_or_key)
    except JIRAError as e:
        if 'java.lang.NumberFormatException' in e.text:
            service_desks = [
                sd for sd in manager.service_desks() if sd.projectKey == id_or_key
            ]
            if len(service_desks):
                return service_desks[0]
            else:
                msg = 'The Service Desk with ID {id} does not exist.'.format(
                    id=id_or_key
                )
                raise JIRAError(text=msg, status_code=404)
        else:
            raise e


def request_types(manager, service_desk, project_key=None, strange_setting=None):
    types = manager.request_types(service_desk)

    if len(types) and not hasattr(types[0], 'issueTypeId'):
        if hasattr(service_desk, 'id'):
            service_desk = service_desk.id

        url = manager._options[
            'server'
        ] + '/rest/servicedesk/%s/servicedesk/%s/groups/%s/request-types' % (
            strange_setting,
            project_key.lower(),
            service_desk,
        )
        headers = {'X-ExperimentalApi': 'opt-in'}
        r_json = json_loads(manager._session.get(url, headers=headers))
        types = [
            RequestType(manager._options, manager._session, raw_type_json)
            for raw_type_json in r_json
        ]
        list(map(lambda t: setattr(t, 'issueTypeId', t.issueType), types))
        return types


def search_users(
    self, query, startAt=0, maxResults=50, includeActive=True, includeInactive=False
):
    """Get a list of user Resources that match the specified search string. Use query instead of
    username field for lookups.
    """
    params = {
        'query': query,
        'includeActive': includeActive,
        'includeInactive': includeInactive,
    }
    return self._fetch_pages(User, None, 'user/search', startAt, maxResults, params)


JIRA.waldur_add_attachment = add_attachment
JIRA.waldur_service_desk = service_desk
JIRA.waldur_request_types = request_types
JIRA.waldur_search_users = search_users
