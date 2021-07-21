#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Public Domain: 2021, Jared Schmidt
# CC0 1.0 Universal license (see https://creativecommons.org/publicdomain/zero/1.0/)
# License applies only to the contents of this file, not the collection as a whole

DOCUMENTATION = '''
---
options:
  repository_configs:
    description:
      - List of python dictionaries of repository configurations to be created, updated, or deleted.  Must contain
        the "key", "rclass", and "packageType" fields at a minimum in each configuration.  Repository configuration
        format can be found at https://www.jfrog.com/confluence/display/JFROG/Repository+Configuration+JSON
      - It is best practice to avoid using capital letters in the "key" field.
      - This can also be passed as a JSON string.
    required: True
    type: list
  state:
    description:
      - Desired state of the repository after execution.
      - "Present" ensures repositories are present and match the configurations
      - "Absent" ensures matching repositories are deleted
      - "Prune" ensures that only matching repositories are present.  All other repositories are deleted.
    default: Present
    choices:
      - Present
      - Absent
      - Prune
    type: string
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
'''