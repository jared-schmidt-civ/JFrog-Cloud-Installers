# Public Domain: Jared Schmidt <jared.schmidt.civ@gmail.com>
# CC0 1.0 Universal license (see https://creativecommons.org/publicdomain/zero/1.0/)
# License applies only to the contents of this file, not the collection as a whole

'''
This library is used for declaratively defining a desired configuration state
and applying it using Create, Read, Update, Delete operations in an API
where Create is a PUT message, Read is a GET message, Update is a POST
message, and Delete is a DELETE message.
'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import urllib
from ansible.module_utils.urls import Request
import base64
import json
from abc import ABC, abstractmethod

class ArtifactoryApi(ABC):
    '''This abstract class defines an Artifactory API endpoint and how to perform CRUD operations
    on it in a declarative fashion.  Applying a list of configs will add and/or update
    the list to artifactory. Deleting a list of configs will delete them from artifactory.  
    Pruning a list will add and/or update the list to artifactory and remove any configs in 
    artifactory that are not in the list.
    '''

    def __init__(self, artifactory_base_url, auth_type, auth_string, ignore_ca_error = False, inCheckMode = False):
        '''Creates a new Artifactory API endpoint object.

        :param artifactory_base_url: Contains the schema, hostname, and port number (if not default) for the Artifactory server
        :param auth_type: Must be "accesstoken", "apikey", or "basic"
        :param auth_string: For auth_type="accesstoken", it is the access token string.
            For auth_type="apikey", it is the api key.
            For auth_type="basic", is is the username and password joined with a colon in the format "username:password".
        :param ignore_ca_error: Defaults to false.  When set to true, API calls to Artifactory will skip cert verification.
        :param inCheckMode: Defaults to false.  When set to true, no changes will be made to Artifactory, but functions will still
            return as if they had.
        '''

        self.baseUrl = artifactory_base_url
        if auth_type == 'accesstoken':
            self.headers = {"Authorization": ("Bearer " + auth_string)}
        elif auth_type == 'apikey':
            self.headers = {"X-JFrog-Art-Api": auth_string}
        else:
            self.headers = {"Authorization": ("Basic " + base64.standard_b64encode(auth_string))}
        self.ignore_ca_error = ignore_ca_error
        self.configs = list()
        self.keyList = self._getRecordKeyList()
        self.inCheckMode = inCheckMode

    def applyConfigs(self, configs):
        '''This method applies all of the config records in the argument to Artifactory.  It updates or creates new.  Honors check mode.
        :args configs: list of configs
        :return: True if something has changed.  False if no changes occurred.
        '''
        # Sort configs to find the lists of what needs to be added and what needs to be updated
        for config in configs:
            self.configs = self.ConfigRecord(config, self.keyList)
        artifactoryRecordList = self._getConfigRecordListFromArtifactory()
        onlyInConfigList, inBoth, onlyInArtifactory = self._sortConfigs(self.configs, artifactoryRecordList)
        
        isChanged = False

        # Add new configs
        if onlyInConfigList:
            for config in onlyInConfigList:
                self._addToArtifactory(config)
            isChanged = True

        # Update existing configs
        if inBoth:
            for config in inBoth:
                temp = self._updateInArtifactory(config)
                if temp:
                    isChanged = True

        return isChanged

    def deleteConfigs(self, configs):
        '''This method deletes all of the config records in the argument from Artifactory.  It deletes or skips records.  Honors check mode.
        :return: True if something has changed.  False if no changes occurred.
        '''
        # Sort configs to find the list of what needs to be removed
        for config in configs:
            self.configs = self.ConfigRecord(config, self.keyList)
        artifactoryRecordList = self._getConfigRecordListFromArtifactory()
        onlyInConfigList, inBoth, onlyInArtifactory = self._sortConfigs(self.configs, artifactoryRecordList)

        isChanged = False

        # Remove configs that are in both
        if inBoth:
            for config in inBoth:
                self._deleteFromArtifactory(config)
            isChanged = True
        
        return isChanged

    def pruneConfigs(self, configs):
        '''This method applies the config records in the argument to Artifactory and removes any records in Artifactory that are not
        in the list.  Honors check mode.
        :return: True if something has changed. False if no changes occurred.
        '''
        # Sort configs to find the lists of what needs to be added, what needs to be updated, and what needs to be removed
        for config in configs:
            self.configs = self.ConfigRecord(config, self.keyList)
        artifactoryRecordList = self._getConfigRecordListFromArtifactory()
        onlyInConfigList, inBoth, onlyInArtifactory = self._sortConfigs(self.configs, artifactoryRecordList)
        
        isChanged = False

        # Add new configs
        if onlyInConfigList:
            for config in onlyInConfigList:
                self._addToArtifactory(config)
            isChanged = True

        # Update existing configs
        if inBoth:
            for config in inBoth:
                temp = self._updateInArtifactory(config)
                if temp:
                    isChanged = True

        # Remove configs that are only in Artifactory
        if onlyInArtifactory:
            for config in onlyInArtifactory:
                self._deleteFromArtifactory(config)
            isChanged = True

        return isChanged

    @abstractmethod
    def _getRecordKeyList(self):
        '''This method returns the list of keys in a config record that uniquely identify it.  Honors check mode.
        '''
        pass

    @abstractmethod
    def _addToArtifactory(self, configRecord):
        '''This method takes a single new config record and adds it to artifactory. Honors check mode.
        '''
        pass

    @abstractmethod
    def _deleteFromArtifactory(self, configRecord):
        '''This method takes a single config record and deletes it from artifactory. Honors check mode.
        '''
        pass

    @abstractmethod
    def _updateInArtifactory(self, configRecord):
        '''This method takes a single config record and updates it in artifactory.
        If the record is the same as what's in Artifactory, nothing happens and the
        method returns false.  Honors check mode.

        :return: True if changed, False if no changes occurred.
        '''
        pass

    @abstractmethod
    def _getConfigRecordListFromArtifactory(self):
        '''This method gets a list of configurations from Artifactory and returns a list of 
        ConfigRecord objects
        :return: List of configs from Artifactory endpoint
        :rtype: List of ConfigRecords
        '''
        pass

    def _sortConfigs(self, configRecordListA, configRecordListB):
        '''This helper function performs some set algebra to determine what is just in
        configRecordListA, what is in configRecordListB, and what is in both.'''
        inBoth = list()
        onlyInListA = list()
        onlyInListB = configRecordListB.copy()
        for item in configRecordListA:
            if item in configRecordListB:
                inBoth.append(item.copy())
                onlyInListB.remove(item)
            else:
                onlyInListA.append(item.copy())
        return (onlyInListA, inBoth, onlyInListB)

    def _sendRequest(self, urltail, method, content = None):
        '''This helper function uses self.baseUrl and urltail to send a request and return a parsed object
        :returns: Parsed JSON object (List or Dictionary)
        '''
        url = self.baseUrl + urltail
        request = Request(headers=self.headers, validate_certs=self.ignore_ca_error)
        response = request.open(method, urllib.parse.quote(url), data=content)
        return json.loads(response.read())

    class ConfigRecord():
        '''This record allows records to be compared by their key list (unique identifier) for sorting purposes.
        Two records can be compared by all fields if a deep equals is used.
        '''

        def __init__(self, record, keylist):
            '''Creates a record based on a json string and a key list
            :param record: JSON string or a dictionary defining the record
            :param keylist: list of fields (as strings) that when used together can uniquely identify a record
            '''
            # Parse as json if record is passed as a single string.  Otherwise, assume it is a dictionary.
            if isinstance(record, str):
                self.record = json.loads(record)
            else:
                self.record = record

            # Save key list
            self._keylist = keylist

        def __eq__(self, other):
            # Compare data types
            if not isinstance(other, self.ConfigRecord):
                return False

            # Compare keys
            for key in self._keylist:
                if other.record['key'] != self.record['key']:
                    return False

            return True

        def __str__(self):
            return str(self.record)

        def deepEquals(self, other):
            # Compare data types
            if not isinstance(other, self.ConfigRecord):
                return False

            # Compare all record fields
            keys = self.record.keys()
            for key in keys:
                if other.record['key'] != self.record['key']:
                    return False

            return True

        def update(self, other):
            self.record.update(other)