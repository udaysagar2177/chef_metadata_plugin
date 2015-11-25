from chef import autoconfigure, Node
from pprint import pprint

class Metadata(object):
	"""
	The metadata information of a chef node

	Attributes:
		chef_node_organization: abcd
		chef_node_name: abcd
		chef_node_environment: abcd
		chef_node_roles: abcd
		chef_node_tags: abcd
	"""
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

	def printNodes(self, nodes):
		for node in nodes:
			print "chefUniqueId: " + node.chefUniqueId
			print("chef_environment: " + node.chef_node_environment)
			print("roles: "+str(node.chef_node_roles))
			print("tags: "+str(node.chef_node_tags))
			print("******")

	def collectMetadata(self):
		# Get the organizations
		organization_details =  self.api.api_request('GET', '')
		self.organization = organization_details['name']
		nodes = self.api.api_request('GET', '/nodes')
		for node_name in nodes.keys():
			self.getNodeInformation(node_name)

	def getNodeInformation(self, node_name):
		chefUniqueId = self.organization+"_"+node_name
		node_details = (self.api.api_request('GET','/nodes/'+node_name))
		#pprint(node_details)
		nodeInformation = {}
		nodeInformation['chefUniqueId'] = chefUniqueId
		for attribute in self.config:
			nodeInformation[attribute] = self.getAttributeValue(
				self.buildFullAttribute(attribute), node_details);
		print nodeInformation

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
			tempValue = tempValue[token]
		return tempValue

	def abcd(self):
		chef_node_environment = node_details['chef_environment']
		chef_node_roles = node_details['run_list']
		chef_node_tags = node_details['normal']['tags']
		node = Metadata(chefUniqueId, chef_node_environment, 
			chef_node_roles, chef_node_tags)
		nodes.append(node)

m = Metadata()
m.run()