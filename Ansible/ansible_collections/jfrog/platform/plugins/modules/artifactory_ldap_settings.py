#!/usr/bin/python

# Public Domain 2021, Jared Schmidt <jared.schmidt.civ@gmail.com>
# CC0 1.0 Universal license (see https://creativecommons.org/publicdomain/zero/1.0/)
# License applies only to the contents of this file, not the collection as a whole
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.module_utils.ArtifactoryApi import ArtifactoryApi
import ansible.module_utils.urls
import urllib

DOCUMENTATION = r'''
---
module: ansible_ldap

short_description: This module is used for configuring Artifactory to use LDAP

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "7.22.0"

description: 
    - This module uses the API provided by adding the "Artifactory LDAP Settings Config"
      user plugin to Artifactory to configure Artifactory to use LDAP.
    - "Artifactory LDAP Settings Config" and "Artifactory LDAP Group Config" plugins must be installed.
    - The LDAP plugins can be found at https://github.com/jfrog/artifactory-user-plugins/tree/master/config/ldapGroupsConfig
      and https://github.com/jfrog/artifactory-user-plugins/tree/master/config/ldapSettingsConfig

options:
    ldap_settings:
        description:
          - 
        type: list of dictionaries
        suboptions:


# Specify this value according to your collection
# in format of namespace.collection.doc_fragment_name
extends_documentation_fragment:
    - jfrog.platform.artifactory_common_docs

author:
    - Jared Schmidt (@jared-schmidt-civ)
'''

EXAMPLES = r'''
# Add or update an LDAP configuration on a server with a non-standard port number
- name: Add or update LDAP configuration
  jfrog.platform.artifactory_ldap_settings:
    ldap_settings:
      - key: myconnection
        enabled: true
        ldapUrl: ldaps://myldapserver.example.com
        userDnPattern: "uid=\{0\}"
        searchFilter: null
        searchBase: null
        searchSubTree: false
        managerDn: {{ ldap_svcacct_username }}
        managerPassword: {{ ldap_svcacct_password }}
        autoCreateUser: false
        emailAttribute: email
    artifactory_base_url: https://artifactory.example.com:8081
    state: Present
    auth_type: Basic
    auth_string: {{ artifactory_username }}:{{ artifactory_password }}

# Delete an LDAP configuration while not verifying CA certs
- name: Delete LDAP configuration
  jfrog.platform.artifactory_ldap_settings:
    ldap_settings:
      - key: myconnection
    artifactory_base_url: https://artifactory.example.com
    state: Absent
    auth_type: ApiKey
    auth_string: {{ api_key }}
    ignore_ca_error: True

# Add or update LDAP configurations while deleting all others
- name: Add or update LDAP configuration
  jfrog.platform.artifactory_ldap_settings:
    ldap_settings:
      - key: myconnection
        enabled: true
        ldapUrl: ldaps://myldapserver.example.com
        userDnPattern: "uid=\{0\}"
        searchFilter: null
        searchBase: null
        searchSubTree: false
        managerDn: {{ ldap_svcacct_username }}
        managerPassword: {{ ldap_svcacct_password }}
        autoCreateUser: false
        emailAttribute: email
      - key: myotherconnection
        enabled: false
        ldapUrl: ldap://myldapserver.example.com
        userDnPattern: "uid=\{0\}"
        searchFilter: null
        searchBase: null
        searchSubTree: false
        managerDn: {{ ldap_svcacct_username }}
        managerPassword: {{ ldap_svcacct_password }}
        autoCreateUser: false
        emailAttribute: email
    artifactory_base_url: https://artifactory.example.com:8081
    state: Prune
    auth_type: AccessToken
    auth_string: {{ access_token }}

# These are examples of possible return values, and in general should use other names for return values.
message:
    description: Message stating whether things changed or not
    type: str
    returned: always
    sample: 'LDAP settings modified'
'''

from ansible.module_utils.basic import AnsibleModule
import ansible.module_utils.urls


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        ldap_settings=list(
            dict(
                key=dict(type='str', required=True),
                enabled=dict(type='bool', required=False),
                ldapUrl=dict(type='str', required=False),
                userDnPattern=dict(type='str', required=False),
                searchFilter=dict(type='str', required=False),
                searchBase=dict(type='str', required=False),
                searchSubTree=dict(type='bool', required=False),
                managerDn=dict(type='str', required=False),
                managerPassword=dict(type='str', required=False),
                autoCreateUser=dict(type='bool', required=False),
                emailAttribute=dict(type='str', required=False)
            )
        ),
        artifactory_base_url=dict(type='str', required=True),
        state=dict(type='str', required=True),
        auth_type=dict(type='str', required=True),
        auth_string=dict(type='str', required=True),
        ignore_ca_error=dict(type='bool', required=False, default=False)
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        # warnings='',
        message=''
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # Manipulate or modify the state as needed
    api = ArtifactoryLDAP(module.params['ldap_settings'], module.params['artifactory_base_url'], module.params['auth_type'], module.params['auth_string'], \
        ignore_ca_error=module.params['ignore_ca_error'], inCheckMode=module.check_mode)
    if module.params['state'].lower() == 'present':
        result['changed'] = api.applyConfigs(module.params['ldap_settings'])
    elif module.params['state'].lower() == 'absent':
        result['changed'] = api.deleteConfigs(module.params['ldap_settings'])
    elif module.params['state'].lower() == 'prune':
        result['changed'] = api.pruneConfigs(module.params['ldap_settings'])
    else:
        module.fail_json(msg='State was not set to a valid value.  Must be Present, Absent, or Prune', **result)

    if result['changed']:
        result['message'] = "LDAP settings modified"
    else:
        result['message'] = "LDAP settings unchanged"

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)

def main():
    run_module()

class ArtifactoryLDAP(ArtifactoryApi):
    def __init__(self, artifactory_base_url, auth_type, auth_string, ignore_ca_error = False, inCheckMode = False):
        super(artifactory_base_url, auth_type, auth_string, ignore_ca_error, inCheckMode)
        self.baseUrl += '/artifactory/api/plugins/execute/'

    def _getRecordKeyList(self):
        return list("key")

    def _addToArtifactory(self, configRecord):
        '''This method takes a single new config record and adds it to artifactory. Honors check mode.
        '''
        if self.inCheckMode:
            return
        self._sendRequest("addLdapSetting", "POST", str(configRecord))

    def _deleteFromArtifactory(self, configRecord):
        '''This method takes a single config record and deletes it from artifactory. Honors check mode.
        '''
        if self.inCheckMode:
            return
        self._sendRequest("deleteLdapSetting?params=key=" + configRecord['key'], "DELETE")

    def _updateInArtifactory(self, configRecord):
        '''This method takes a single config record and updates it in artifactory.
        If the record is the same as what's in Artifactory, nothing happens and the
        method returns false.  Honors check mode.

        :return: True if changed, False if no changes occurred.
        '''
        # Compare new and old configs
        artConfig = ArtifactoryApi.ConfigRecord(self._sendRequest("getLdapSetting?params=key=" + configRecord['key']))
        newConfig = artConfig.deepCopy()
        newConfig.update(configRecord)
        if newConfig.deepEquals(artConfig):
            return False
        else:
            if not self.inCheckMode:
                self._sendRequest("updateLdapSetting?params=key=" + configRecord['key'], "POST", str(newConfig))
            return True

    def _getConfigRecordListFromArtifactory(self):
        '''This method gets a list of configurations from Artifactory and returns a list of 
        ConfigRecord objects
        :return: List of configs from Artifactory endpoint
        :rtype: List of ConfigRecords
        '''
        # Retrieve list of settings from artifactory
        configNames = self._sendRequest("getLdapSettingsList", "GET")

        # Retrieve list of configs from artifactory and parse into ConfigRecords
        configs = ()
        for name in configNames:
            config = self._sendRequest("getLdapSetting?params=key=" + name, "GET")
            configs.append(ArtifactoryApi.ConfigRecord(config))
        
        return configs

if __name__ == '__main__':
    main()
