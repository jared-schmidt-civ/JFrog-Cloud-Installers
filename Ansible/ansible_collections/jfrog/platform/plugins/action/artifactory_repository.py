# -*- coding: utf-8 -*-

# Public Domain: 2021, Jared Schmidt
# CC0 1.0 Universal license (see https://creativecommons.org/publicdomain/zero/1.0/)
# License applies only to the contents of this file, not the collection as a whole

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import urllib
import base64
import json

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleOptionsError, AnsibleActionFail

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

class ActionModule(ActionBase):

    _VALID_ARGS = frozenset(['repository_configs', 'state', 'artifactory_base_url', 'auth_type', 'auth_string', 'ignore_ca_error'])
    _PARAM_DEFAULTS = {
        'state': 'Present',
        'ignore_ca_error': False,
        'auth_type': 'Basic'
    }

    # _VALID_REPOSITORYTYPES = frozenset(['local', 'remote', 'virtual', 'federated', 'distribution'])

    # _VALID_PACKAGETYPES = frozenset(['maven', 'gradle', 'ivy', 'sbt', 'helm', 'cargo', 'cocoapods', \
    # 'opkg', 'rpm', 'nuget', 'cran', 'gems', 'npm', 'bower', 'debian', 'composer', 'pypi', 'docker', \
    # 'vagrant', 'gitlfs', 'go', 'yum', 'conan', 'chef', 'puppet', 'generic'])

    def run(self, tmp=None, task_vars=None):
        ''' This plugin verifies that repositories matching the key, rclass, and packagetype
        in the repository configs are present or absent as selected by "state".  When prune is the selected state,
        all repositories not in the repository_configs are removed.  The plugin uses "artifactory_base_url"
        and an authentication method to connect to artifactory's API. CAs are checked by default unless
        "ignore_ca_error" is set to True.  The repository type defaults to "local", but can be modified
        by setting it in the "repository_config['rclass']" field.
        '''

        # Set ansible module flags
        self.__supports_check_mode = True
        self.__supports_async = True

        # Execute the class's parent definition of the run function
        # (It runs some validation checks and warnings)
        if task_vars is None:
            task_vars = dict()
        result = super(ActionModule, self).run(task_vars=task_vars)

        # Add defaults to arguments
        args = self._PARAM_DEFAULTS.copy()
        args.update(self._task.args)

        # Validate and adjust arguments as needed
        if args['repository_configs'] is None:
            raise AnsibleOptionsError('"repository_configs" is a required argument')
        if isinstance(args['repository_configs'], str):
            args['repository_configs'] = json.loads(self._task.args['repository_configs'])
        if not isinstance(args['repository_configs'], list):
            raise AnsibleOptionsError('"repository_configs" needs to be a list or JSON list')
        for repo in args['repository_configs']:
            if isinstance(repo, str):
                repo = json.loads(repo)
            if repo['key'] is None:
                raise AnsibleOptionsError('"key" is a required field in "repository_configs"')
            if repo['packageType'] is None:
                raise AnsibleOptionsError('"packageType" is a required field in "repository_configs"')
            if repo['rclass'] is None:
                raise AnsibleOptionsError('"rclass" is a required field in "repository_configs"')
        if len(args['repository_configs']) >= 2:
            for repo1 in range(0, len(args['repository_configs']) - 1):
                for repo2 in range(repo1 + 1, len(args['repository_configs'])):
                    if args['repository_configs'][repo1]['key'].lower() == args['repository_configs'][repo2]['key'].lower():
                        raise AnsibleOptionsError('Repository configurations must have unique "key" names')
        if args['artifactory_base_url'] is None:
            raise AnsibleOptionsError('"artifactory_base_url" is a required argument')
        args['state'] = str(args['state']).lower()
        if not (args['state'] == 'absent' or args['state'] == 'present' or args['state'] == 'prune'):
            raise AnsibleOptionsError('"State" must be "Absent", "Present", or "Prune"')
        args['auth_type'] = str(args['auth_type']).lower()
        if not (args['auth_type'] == 'basic' or args['auth_type'] == 'accesstoken' or args['auth_type'] == 'apikey'):
            raise AnsibleOptionsError('"auth_type" must be "Basic", "AccessToken", or "ApiKey"')
        if args['auth_type'] == 'basic' and ':' not in args['auth_string']:
            raise AnsibleOptionsError('Basic auth_type requires that username and password be provided in auth_string in the format username:password')
        if str(args['ignore_ca_error']).lower() == 'false' or str(args['ignore_ca_error']).lower() == 'no':
            args['ignore_ca_error'] = False
        args['ignore_ca_error'] = bool(args['ignore_ca_error'])

        # Build base URL path
        baseUrl = args['artifactory_base_url'] + '/artifactory/'

        # Build auth for URI request
        uriParams = dict()
        if args['auth_type'] == 'accesstoken':
            uriParams['headers'] = {"Authorization": ("Bearer " + args['auth_string'])}
        elif args['auth_type'] == 'apikey':
            uriParams['headers'] = {"X-JFrog-Art-Api": args['auth_string']}
        else:
            uriParams['headers'] = {"Authorization": ("Basic " + base64.standard_b64encode(args['auth_string']))}

        # Set cert validation for requests.  It defaults to 'yes' in the ansible URI module.
        if args['ignore_ca_error']:
            uriParams['validate_certs'] = 'no'
            if result['warning'] is None:
                result['warning'] = list()
            result['warning'].append('API calls to Artifactory are not validating CA certs. Auth tokens vulnerable to MITM attack.')

        # Get repositories
        getReposUrl = baseUrl + 'api/repositories'
        getRepoUriParams = {
            'url': urllib.parse.quote(getReposUrl),
            'method': 'GET'
        }
        getRepoUriParams.update(uriParams)
        getReposResult = self._execute_module('uri', module_args=getRepoUriParams, task_vars=task_vars, wrap_async=self._task.async_val)

        # Check for failed query
        if getReposResult.get('failed', False):
            raise AnsibleActionFail('Querying repositories in artifactory failed with status ' + getReposResult['status'] + ': ' + getReposResult['msg'])

        # Parse JSON response
        jsonGetResult = json.loads(getReposResult['content'])

        # ---- Primary logic -----
        # In this section the decision and API logic happens.  The list of repository configurations in the arguments and the list
        # of repositories currently in artifactory is separated into three groups, those unique to each and those common to both.
        # The state argument is then used to determine what happens to each group that isn't empty.

        # Sort the repository_configs and artifactory repos into those only in the args (new), only in artifactory (not in args), and in both (in args and artifactory)
        inBoth = list()
        onlyInArtifactory = jsonGetResult.copy()
        onlyInArgs = args['repository_configs'].copy()
        for repo in args['repository_configs']:
            for item in jsonGetResult:
                if str(item['key']).lower() == str(repo['key']).lower():
                    onlyInArgs.remove(repo)
                    # Force keys to match capitalization
                    repo['key'] = item['key']
                    inBoth.append(repo)
                    onlyInArtifactory.remove(repo)

        # These counters are used to determine what result to return
        addedRepos = 0
        updatedRepos = 0
        deletedRepos = 0

        # If the state is present or prune and onlyInArgs is not empty, add the onlyInArgs repos to artifactory
        if (args['state'] == 'present' or args['state'] == 'prune') and onlyInArgs:
            addedRepos = len(onlyInArgs)
            if not self._play_context.check_mode:
                for repo in onlyInArgs:
                    putRepoUrl = baseUrl + 'api/repositories/' + repo['key']
                    putRepoUriParams = {
                        'url': urllib.parse.quote(putRepoUrl),
                        'method': 'PUT',
                        'body': json.dumps(repo),
                        'body_format': 'json'
                    }
                    putRepoUriParams.update(uriParams)
                    putRepoResult = self._execute_module('uri', module_args=putRepoUriParams, task_vars=task_vars, wrap_async=self._task.async_val)

                    # Check for failed call
                    if putRepoResult.get('failed', False):
                        raise AnsibleActionFail('Adding repository ' + repo['key'] + ' to artifactory failed with status ' + putRepoResult['status'] + ': ' + putRepoResult['msg'])

        # If the state is present or prune and inBoth is not empty, update the inBoth repos in artifactory
        if (args['state'] == 'present' or args['state'] == 'prune') and inBoth:
            for repo in inBoth:
                # Compare present and (desired) future states.  Update the repo in artifactory if the two states differ.
                getRepoConfigUrl = baseUrl + 'api/repositories/' + repo['key']
                getRepoConfigUriParams = {
                    'url': urllib.parse.quote(getRepoConfigUrl),
                    'method': 'GET'
                }
                getRepoConfigUriParams.update(uriParams)
                getRepoConfigResult = self._execute_module('uri', module_args=getRepoConfigUriParams, task_vars=task_vars, wrap_async=self._task.async_val)

                # Check for failed query
                if getRepoConfigResult.get('failed', False):
                    raise AnsibleActionFail('Querying repository config for ' + repo['key'] + ' in artifactory failed with status ' + getRepoConfigResult['status'] + ': ' + getRepoConfigResult['msg'])

                currentConfig = json.loads(getRepoConfigResult['content'])
                futureConfig = currentConfig.copy()
                futureConfig.update(repo)

                # Update if different, return unchanged if the same
                if futureConfig != currentConfig:
                    updatedRepos += 1
                    if not self._play_context.check_mode:
                        postRepoConfigUrl = baseUrl + 'api/repositories/' + repo['key']
                        postRepoConfigUriParams = {
                            'url': urllib.parse.quote(postRepoConfigUrl),
                            'method': 'POST',
                            'body': json.dumps(repo),
                            'body_format': 'json'
                        }
                        postRepoConfigUriParams.update(uriParams)
                        postRepoConfigResult = self._execute_module('uri', module_args=postRepoConfigUriParams, task_vars=task_vars, wrap_async=self._task.async_val)

                        # Check for failed call
                        if postRepoConfigResult.get('failed', False):
                            raise AnsibleActionFail('Updating repository config for ' + repo['key'] + ' in artifactory failed with status ' + postRepoConfigResult['status'] + ': ' + postRepoConfigResult['msg'])

        # If the state is absent and inBoth is not empty, remove the inBoth repos from artifactory
        # If the state is prune and onlyInArtifactory is not empty, remove the onlyInArtifactory repos from artifactory
        toRemove = ()
        if args['state'] == 'absent' and inBoth:
            toRemove = inBoth
        if args['state'] == 'prune' and onlyInArtifactory:
            toRemove = onlyInArtifactory
        for repo in toRemove:
            deletedRepos = len(toRemove)
            if not self._play_context.check_mode:
                deleteRepoUrl = baseUrl + 'api/repositories/' + repo['key']
                deleteRepoUriParams = {
                    'url': urllib.parse.quote(deleteRepoUrl),
                    'method': 'DELETE'
                }
                deleteRepoUriParams.update(uriParams)
                deleteRepoResult = self._execute_module('uri', module_args=deleteRepoUriParams, task_vars=task_vars, wrap_async=self._task.async_val)

                # Check for failed call
                if deleteRepoResult.get('failed', False):
                    raise AnsibleActionFail('Deleting repository ' + repo['key'] + ' from artifactory failed with status ' + deleteRepoResult['status'] + ': ' + deleteRepoResult['msg'])

        # For all other combinations, do nothing.

        # Determine result and generate output message
        if addedRepos + updatedRepos + deletedRepos == 0:
            result['msg'] = 'No repositories changed'
            result['changed'] = False
        else:
            result['msg'] = str(addedRepos) + " repositories were added\r\n" + str(updatedRepos) + " repositories were updated\r\n" + str(deletedRepos) + " repositories were deleted"
            result['changed'] = True

        return result
