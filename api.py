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

	def __init__(self, chefUniqueId, chef_environment, chef_node_roles,
		chef_node_tags, ):
		self.chefUniqueId     = chefUniqueId
		self.chef_node_environment = chef_environment
		self.chef_node_roles  = chef_node_roles
		self.chef_node_tags   = chef_node_tags


def main():
	api = autoconfigure()
	nodes = []
	collectMetadata(api, nodes)
	# get the token as argument
	printNodes(nodes)
	
def printNodes(nodes):
	for node in nodes:
		print "chefUniqueId: " + node.chefUniqueId
		print("chef_environment: " + node.chef_node_environment)
		print("roles: "+str(node.chef_node_roles))
		print("tags: "+str(node.chef_node_tags))
		print("******")

def collectMetadata(api, nodes):
	# Get the organizations
	organization_details =  api.api_request('GET', '')
	organization = organization_details['name']
	pprint('Organization: ' + organization)
	print "******"
	chefUniqueId = ''
	nodes_details = api.api_request('GET', '/nodes')
	for node_name in nodes_details.keys():
		chefUniqueId = organization+"_"+node_name
		node_details = (api.api_request('GET','/nodes/'+node_name))
		chef_node_environment = node_details['chef_environment']
		chef_node_roles = node_details['run_list']
		chef_node_tags = node_details['normal']['tags']
		node = Metadata(chefUniqueId, chef_node_environment, 
			chef_node_roles, chef_node_tags)
		nodes.append(node)


main()