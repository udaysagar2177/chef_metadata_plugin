from chef import autoconfigure, Node
from pprint import pprint
from time import sleep
import logging
import sys
import getopt
import requests
import copy
import re
import pickle


class Metadata(object):
	"""
	Collect metadata of a chef node
	"""
	CONFIG_FILE = 'configuration.txt'
	LOG_FILE = '/var/log/ChefMetadata.log'
	URL = 'http://lab-api.corp.signalfuse.com:8080/v1/dimension'
	PICKLE_FILE = 'pk_metadata.pk'
	SLEEP_DURATION = 60 			# IN SECONDS
	propertyNamePattern = re.compile('^[a-zA-Z_][a-zA-Z0-9_-]*$')
	config = []
	organization = ''
	nodes_metadata = []

	logger = logging.getLogger(__name__)
	logger.setLevel(logging.INFO)
	handler = logging.FileHandler(LOG_FILE)
	handler.setLevel(logging.INFO)
	formatter = logging.Formatter(
		'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	def __init__(self, ACCESS_TOKEN):
		self.api = autoconfigure()
		self.ACCESS_TOKEN = ACCESS_TOKEN

	def run(self):
		self.nodes_metadata = []
		self.readConfig()
		self.collectMetadataFromChef()
		for nodeInformation in self.nodes_metadata:
			self.sendMetadataToSignalfx(nodeInformation)
		self.saveMetadata()

	def saveMetadata(self):
		pickleData = {}
		for nodeInformation in self.nodes_metadata:
			pickleData[nodeInformation['chefUniqueId']] = nodeInformation
			pickleData[nodeInformation['chefUniqueId']].pop('chefUniqueId')
		output = open(self.PICKLE_FILE, 'wb')
		pickle.dump(pickleData, output)
		self.logger.info('Saved updated metadata to '+self.PICKLE_FILE)
		output.close()

	def sendMetadataToSignalfx(self, nodeInformation):
		headers = {
			'X-SF-Token':self.ACCESS_TOKEN,
		}
		resp = self.getSignalfxObjectId(nodeInformation, headers)
		if len(resp.json()['rs']) == 0:
			self.logger.info('Signalfx does not have your dimension'
				+'object chefUniqueId:'+nodeInformation['chefUniqueId'])
			return
		signalfxObjectId = resp.json()['rs'][0]
		self.logger.info("ObjectID for "+nodeInformation['chefUniqueId']
			+" is "+signalfxObjectId)
		new_metadata = self.checkForUpdatesInMetadata(copy.deepcopy(nodeInformation))
		if new_metadata:
			resp = requests.patch(self.URL+'/'+signalfxObjectId, params=new_metadata
				, headers=headers)
		else:
			self.logger.info('No new metadata is found for '+nodeInformation['chefUniqueId'])

	def checkForUpdatesInMetadata(self, current_data):
		inputPickle = open(self.PICKLE_FILE, 'rb')
		self.logger.info('Reading previous metadata from '+self.PICKLE_FILE)
		savedMetadata = pickle.load(inputPickle)
		inputPickle.close()
		if current_data['chefUniqueId'] not in savedMetadata:
			return current_data
		previous_data = savedMetadata[current_data['chefUniqueId']]
		for key in previous_data.keys():
			if key in current_data and current_data[key] == previous_data[key]:
				current_data.pop(key)
		current_data.pop('chefUniqueId')
		return current_data

	def getSignalfxObjectId(self, nodeInformation, headers):
		params = {
			'query':'chefUniqueId:'+nodeInformation['chefUniqueId'],
			'getIDs':'true'
		}
		resp = requests.get(self.URL, params=params, headers=headers)
		if resp.status_code != 200:
			self.logger.error('Unable to get ID of'+
				'chefUniqueId object from Signalfx')
			print(resp.raise_for_status())
			self.exitNow()
		return resp
		
	def readConfig(self):
		self.config = []
		with open(self.CONFIG_FILE, 'r') as f:
			lines = f.readlines()
			for line in lines:
				if not line.startswith("#") and line != '\n':
					attribute = line.rstrip('\n')
					if self.checkPropertyNameSyntax(attribute
						.replace('.', '_')):
						self.config.append(attribute)

	def checkPropertyNameSyntax(self, attribute):
		if not self.propertyNamePattern.match(attribute):
			self.logger.error('Invalid attribute name '
				+ attribute
				+'Attribute names should follow '
				+'the regex pattern ^[a-zA-Z_][a-zA-Z0-9_-]*$')
			return False
		return True

	def exitNow(self):
		print("Error logged into the log file! Exiting...");
		sys.exit(1)

	def apiGetRequest(self, endpoint):
		value = None
		try:
			value = self.api.api_request('GET', endpoint)
		except Exception as e:
			self.logger.error('Unable to perform api GET request'
				, exc_info=True)
			self.exitNow()
		return value

	def collectMetadataFromChef(self):
		organization_details =  self.apiGetRequest('')
		self.organization = organization_details['name']
		nodes = self.apiGetRequest('/nodes')
		for node_name in nodes.keys():
			self.getNodeInformation(node_name)

	def getNodeInformation(self, node_name):
		chefUniqueId = self.organization+"_"+node_name
		node_details = Node(node_name)
		nodeInformation = {}
		nodeInformation['chefUniqueId'] = chefUniqueId
		nodeInformation['chef_environment'] = node_details.chef_environment
		for attribute in self.config:
			attributeValue = self.getAttributeValue(
				attribute, node_details)
			if attributeValue:
				attribute = self.adjustAttributeName(attribute)
				nodeInformation[attribute] = attributeValue
		self.nodes_metadata.append(nodeInformation)

	def adjustAttributeName(self, attribute):
		attribute = attribute.replace('.', '_')
		if not attribute.startswith('chef_'):
			attribute = 'chef_' + attribute
		return attribute

	def getAttributeValue(self, attribute, node_details):
		tokens = attribute.split('.')
		tempValue = node_details
		for token in tokens:
			try:
				tempValue = tempValue[token]
			except Exception as e:
				self.logger.error('Invalid attribute is listed in '
					+self.CONFIG_FILE, exc_info=True)
				return None
		if isinstance(tempValue, dict):
			self.logger.error('Attribute value for '+attribute+' cannot be a dictionary!')
			return None
		if isinstance(tempValue, list) and not (any(isinstance(x, dict) for x in tempValue)):
			return '$'.join(tempValue)
		return str(tempValue)


def main(argv):
	FILE_NAME = sys.argv[0]
	try:
		opts, argv = getopt.getopt(argv, "ht:", ["accessToken="])
	except getopt.GetoptError:
		print 'Usage: python '+FILE_NAME+' -t <ACCESS_TOKEN>'
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print 'Usage: python '+FILE_NAME+' -t <ACCESS_TOKEN>'
			sys.exit()
		elif opt in ["-t", "accessToken"]:
			ACCESS_TOKEN = arg
	if ACCESS_TOKEN:
		m = Metadata(ACCESS_TOKEN)
		while True:
			m.run()
			sleep(m.SLEEP_DURATION)
	else:
		print 'Enter valid Access Token!'
		print 'Usage: python '+FILE_NAME+' -t <ACCESS_TOKEN>'
		sys.exit(2)


if __name__ == "__main__":
   main(sys.argv[1:])
