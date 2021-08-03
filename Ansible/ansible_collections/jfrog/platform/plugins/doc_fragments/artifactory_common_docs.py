#!/usr/bin/python

# Public Domain 2021, Jared Schmidt <jared.schmidt.civ@gmail.com>
# CC0 1.0 Universal license (see https://creativecommons.org/publicdomain/zero/1.0/)
# License applies only to the contents of this file, not the collection as a whole
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

class ModuleDocFragment(object):
    DOCUMENTATION = r'''
options:
    artifactory_base_url:
        description:
        - Base url of the artifactory server.  It must include the schema (http or https), the fqdn, and port
            number (if not 80 or 443).
        required: True
        type: string
    auth_type:
        description:
        - Specifies which authentication type to use with artifactory's API.  Basic auth uses an admin's username
            and password.
        choices:
        - Basic
        - AccessToken
        - ApiKey
        default: Basic
        type: string
        required: True
    auth_string:
        description:
        - The authentication string to be provided in artifactory api calls.  Paired with selection given in "auth_type".
        - Basic auth requires that auth_string be provided in the format "username:password".  The plugin performs the base64 encoding.
        - AccessToken and ApiKey require that auth_string be the access token or api key.
        required: True
        type: string
    ignore_ca_error:
        description:
        - Flag to disable CA verification.  Opens API calls to MITM attack.  Do not use in production environments.
        default: False
        required: False
        type: boolean
    state:
        description:
        - Desired state of the configuration after execution.
        - "Present" ensures configurations are present in artifactory and match what has been defined
        - "Absent" ensures matching configurations are deleted
        - "Prune" ensures that only matching configurations are present.  All other configurations are deleted.
        default: Present
        choices:
        - Present
        - Absent
        - Prune
        type: string
        
requirements:
    - Python >= 3.6

notes:
    - Check mode is supported.
'''