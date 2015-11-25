from chef import autoconfigure, Node
from pprint import pprint
import logging
import sys

class Metadata(object):
	"""
	The metadata information of a chef node

	Attributes:
		
	"""
	CONFIG_FILE = 'metadata.config'
	LOG_FILE = 'metadata.log'

	logger = logging.getLogger(__name__)
	logger.setLevel(logging.INFO)

	handler = logging.FileHandler(LOG_FILE)
	handler.setLevel(logging.INFO)
	formatter = logging.Formatter(
		'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	config = []
	organization = ''
	nodes_metadata = []

	def __init__(self):
		self.api = autoconfigure()

	def run(self):
		self.readConfig()
		self.collectMetadata()
		# get the token as argument
		#printNodes(nodes)
		
	def readConfig(self):
		self.config = []
		with open('metadata.config') as f:
			lines = f.readlines()
			for line in lines:
				if not line.startswith("#"):
					if line != '\n':
						self.config.append(line.rstrip('\n'))

	def apiGetRequest(self, endpoint):
		value = None
		try:
			value = self.api.api_request('GET', endpoint)
		except Exception as e:
			self.logger.error('Unable to perform api GET request', exc_info=True)
			print("Error logged into the log file! Exiting...");
			sys.exit(1)
		return value

	def collectMetadata(self):
		# Get the organizations
		organization_details =  self.apiGetRequest('')
		self.organization = organization_details['name']
		nodes = self.apiGetRequest('/nodes')
		for node_name in nodes.keys():
			self.getNodeInformation(node_name)

	def getNodeInformation(self, node_name):
		chefUniqueId = self.organization+"_"+node_name
		node_details = self.apiGetRequest('/nodes/'+node_name)
		nodeInformation = {}
		nodeInformation['chefUniqueId'] = chefUniqueId
		for attribute in self.config:
			nodeInformation[attribute] = self.getAttributeValue(
				self.buildFullAttribute(attribute), node_details);
		print nodeInformation
		# add this dictionary to an array

	def buildFullAttribute(self, attribute):
		normal = ['tags']
		base = ['chef_environment', 'chef_type', 'default', 'json_class',
		'name', 'override', 'run_list']
		if attribute in normal:
			return 'normal.'+attribute
		elif attribute in base:
			return attribute
		else:
			return 'automatic.'+attribute

	def getAttributeValue(self, attribute, node_details):
		tokens = attribute.split('.')
		tempValue = node_details
		for token in tokens:
			try:
				tempValue = tempValue[token]
			except Exception as e:
				self.logger.error('Invalid attribute is listed in '+self.CONFIG_FILE, exc_info=True)
				print("Error logged into the log file! Exiting...");
				sys.exit(1)
		return tempValue

m = Metadata()
m.run()