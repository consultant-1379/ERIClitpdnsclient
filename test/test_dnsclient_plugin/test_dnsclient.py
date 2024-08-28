##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import unittest

from dnsclient_extension.dnsclientextension import DNSClientExtension
from dnsclient_plugin.dnsclientplugin import DNSClientPlugin
from litp.core.execution_manager import ExecutionManager
from litp.core import constants
from litp.core.model_item import ModelItem
from litp.core.model_manager import ModelManager
from litp.core.model_type import ItemType, Child
from litp.core.plugin_context_api import PluginApiContext
from litp.core.plugin_manager import PluginManager
from litp.core.task import ConfigTask
from litp.core.validators import ValidationError
from litp.extensions.core_extension import CoreExtension
from network_extension.network_extension import NetworkExtension
from litp.core.puppet_manager import PuppetManager


from litp.core.translator import Translator
t = Translator('ERIClitpdnsclient_CXP9031073')
_ = t._


class TestDNSClientPlugin(unittest.TestCase):

    def setUp(self):
        """
        Construct a model, sufficient for test cases
        that you wish to implement in this suite.
        """
        self.model = ModelManager()
        self.plugin_manager = PluginManager(self.model)
        self.context = PluginApiContext(self.model)
        self.plugin_manager.add_property_types(
            CoreExtension().define_property_types())
        self.plugin_manager.add_item_types(
            CoreExtension().define_item_types())
        self.plugin_manager.add_default_model()
        self.plugin_manager.add_property_types(
            NetworkExtension().define_property_types())
        self.plugin_manager.add_item_types(
            NetworkExtension().define_item_types())
        self.plugin = DNSClientPlugin()
        self.plugin_manager.add_plugin('TestPlugin', 'some.test.plugin',
                                       '1.0.0', self.plugin)

        self.plugin_manager.add_property_types(
            DNSClientExtension().define_property_types())
        self.plugin_manager.add_item_types(
            DNSClientExtension().define_item_types())
       # self.execution = ExecutionManager(self.model,
        #                                self.puppet_manager,
         #                               self.plugin_manager)
        #self.execution._phase_id = self.mock_phase_id



    def setup_model(self):
        # Use ModelManager.crete_item and ModelManager.create_link
        # to create and reference (i.e.. link) items in the model.
        # These correspond to CLI/REST verbs to create or link
        # items.
        self.node1 = self.model.create_item("node", "/node1",
                                                 hostname="node1")
        self.node2 = self.model.create_item("node", "/node2",
                                                 hostname="special")

    def query(self, item_type=None, **kwargs):
        # Use PluginApiContext.query to find items in the model
        # properties to match desired item are passed as kwargs.
        # The use of this method is not required, but helps
        # plugin developer mimic the run-time environment
        # where plugin sees QueryItem-s.
        return self.context.query(item_type, **kwargs)

    def _create_standard_items_ok(self):
        self.sys1_url = "/infrastructure/systems/system1"
        self.cluster_url = "/deployments/local_vm/clusters/cluster1"
        self.node1_url = "/deployments/local_vm/clusters/cluster1/nodes/node1"
        self.model.create_root_item("root", "/")
        self.model.create_item('deployment', '/deployments/local_vm')
        self.model.create_item('cluster', self.cluster_url)

        # Nodes
        node1 = self.model.create_item("node", self.node1_url,
                            hostname="node1")

        # new network model
        self.model.create_item(
            'network',
            '/infrastructure/networking/networks/mgmt_network',
            name='mgmt',
            subnet='10.0.1.0/24',
            litp_management='true'
            )
        self.model.create_item(
            'network',
            '/infrastructure/networking/networks/hrbt_ntwk',
            name='heartbleed',
            subnet='10.0.2.0/24'
            )

        # MS NIC
        self.model.create_item(
            'eth',
            '/ms/network_interfaces/if0',
            network_name="mgmt",
            device_name="eth0",
            ipaddress="10.0.1.10",
            macaddress='08:00:27:5B:C1:3F'
            )

        # Node 1 NICs
        self.model.create_item(
            'eth',
            self.node1_url + "/network_interfaces/if0",
            network_name="mgmt",
            device_name="eth0",
            ipaddress="10.0.1.0",
            macaddress='08:00:27:5B:C1:3F'
            )
        self.model.create_item(
            'eth',
            self.node1_url + "/network_interfaces/if1",
            network_name="heartbleed",
            device_name="eth1",
            ipaddress="10.0.2.0",
            macaddress='08:00:27:5B:C1:3F'
            )

    def test_configuration_tasks_and_update(self):
        self._create_standard_items_ok()

        item_dnsclient1=self.model.create_item("dns-client",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dnsclient1",search =
            "examlpedns1.com,ericsson.com,blah.com")

        item_nameserver1 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/dnsclient1/nameservers/nameserver1"),
                ipaddress="11.11.11.1", position="1")

        item_nameserver2 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/dnsclient1/nameservers/nameserver2"),
                ipaddress="11.11.11.2", position="2")

        item_nameserver3 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/dnsclient1/nameservers/nameserver3"),
                ipaddress="2001:4860:0:1001::68", position="3")

        node1 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node1")

        dns_client = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/dnsclient1")

        tasks = self.plugin.create_configuration(self.context)
        call_id = "%s_%s" % (node1.hostname, item_dnsclient1.get_vpath())

        test_task = ConfigTask(node1,dns_client,
                            'Create DNS client configuration on node "node1"',
                            "dnsclient::nameserver",call_id,
                            search=dns_client.search,
                            name1="11.11.11.1",
                            name2="11.11.11.2",
                            name3="2001:4860:0:1001::68"
                            )

        self.assertEquals(test_task.model_item, tasks[0].model_item)
        self.assertEquals(test_task.item_vpath, tasks[0].item_vpath)
        self.assertEquals(test_task.description, tasks[0].description)
        self.assertEquals(test_task.kwargs['name1'],tasks[0].kwargs['name1'])
        self.assertEquals(test_task.kwargs['name2'],tasks[0].kwargs['name2'])
        self.assertEquals(test_task.kwargs['name3'],tasks[0].kwargs['name3'])

        #Updating Nameservers
        item_nameserver2 = self.model.update_item(
            ("/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/dnsclient1/nameservers/nameserver2"),
                ipaddress="11.11.11.33", position="3")

        item_nameserver3 = self.model.update_item(
            ("/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/dnsclient1/nameservers/nameserver3"),
                ipaddress="2001:4860:0:1001::22", position="2")

        tasks = self.plugin.create_configuration(self.context)
        call_id = "%s_%s" % (node1.hostname, item_dnsclient1.get_vpath())

        test_task = ConfigTask(node1,dns_client,
                            'Create DNS client configuration on node "node1"',
                             "dnsclient::nameserver",call_id,
                            search=dns_client.search,
                            name1="11.11.11.1",
                            name2="2001:4860:0:1001::22",
                            name3="11.11.11.33"
                            )
        self.assertEquals(test_task.model_item, tasks[0].model_item)
        self.assertEquals(test_task.item_vpath, tasks[0].item_vpath)
        self.assertEquals(test_task.description, tasks[0].description)
        self.assertEquals(test_task.kwargs['name1'],tasks[0].kwargs['name1'])
        self.assertEquals(test_task.kwargs['name2'],tasks[0].kwargs['name2'])
        self.assertEquals(test_task.kwargs['name3'],tasks[0].kwargs['name3'])

    def test_configuration_task_for_one_nameserver(self):
        self._create_standard_items_ok()

        item_dnsclient1=self.model.create_item("dns-client",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dnsclient1",search =
            "examlpedns1.com,ericsson.com,blah.com")

        item_nameserver1 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/dnsclient1/nameservers/nameserver1"),
                ipaddress="11.11.11.2", position="2")

        node1 = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes/node1")

        dns_client = self.context.query_by_vpath(
            "/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/dnsclient1")

        tasks = self.plugin.create_configuration(self.context)
        call_id = "%s_%s" % (node1.hostname, item_dnsclient1.get_vpath())

        test_task = ConfigTask(node1,dns_client,
                            'Create DNS client configuration on node "node1"',
                            "dnsclient::nameserver",call_id,
                            search=dns_client.search,
                            name1="",
                            name2="11.11.11.2",
                            name3=""
                            )

        self.assertEquals(test_task.model_item, tasks[0].model_item)
        self.assertEquals(test_task.item_vpath, tasks[0].item_vpath)
        self.assertEquals(test_task.description, tasks[0].description)
        self.assertEquals(test_task.kwargs['name1'],tasks[0].kwargs['name1'])
        self.assertEquals(test_task.kwargs['name2'],tasks[0].kwargs['name2'])
        self.assertEquals(test_task.kwargs['name3'],tasks[0].kwargs['name3'])

    def test_configuration_task_for_one_nameserver_update(self):
        self._create_standard_items_ok()

        item_dnsclient1=self.model.create_item("dns-client",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dnsclient1",search =
            "examlpedns1.com,ericsson.com,blah.com")

        item_nameserver1 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/dnsclient1/nameservers/nameserver1"),
                ipaddress="11.11.11.2", position="2")

        item_nameserver1 = self.model.update_item(
            ("/deployments/local_vm/clusters/cluster1/nodes"
            "/node1/configs/dnsclient1/nameservers/nameserver1"),
                ipaddress="11.11.11.2", position="3")

        tasks = self.plugin.create_configuration(self.context)

    def test_node_validate_dublicate_nameserver_positions (self):
        self._create_standard_items_ok()
        dnsclient1 = self.model.create_item("dns-client",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1", search ="examlpedns1.com,ericsson.com,blah.com")

        nameserver1 = self.model.create_item("nameserver",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver1",
                                             ipaddress ="10.10.10.10", position="1")

        nameserver2 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver2"), ipaddress ="10.10.10.10", position="1")

        errors = self.plugin.validate_model(self)
        ref_errors = [ValidationError(
                                      item_path = ("/deployments/local_vm/"
                                                   "clusters/cluster1/"
                                                   "nodes/node1/configs/"
                                                   "dns_client1/nameservers/"
                                                   "nameserver2"),
                                      error_message =_('DUPLICATE_NS_POS')%'1',
                                      error_type=constants.VALIDATION_ERROR),
                      ValidationError(item_path = ("/deployments/local_vm/"
                                                   "clusters/cluster1/"
                                                   "nodes/node1/configs/"
                                                   "dns_client1/nameservers"
                                                   "/nameserver1"),
                                      error_message =_('DUPLICATE_NS_POS')%'1',
                                      error_type=constants.VALIDATION_ERROR)
                      ]
        self.assertEquals(ref_errors, errors)

    def test_validate_search_is_less_than_256_chars (self):
        self._create_standard_items_ok()
        string_val = "x" * 257
        dnsclient1 = self.model.create_item("dns-client",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1"), search = string_val)
        ref_errors = [ValidationError(
                                      property_name="search",
                                      error_message = ("Length of "
                                                       "property cannot "
                                                       "be more than 256 "
                                                       "characters"),
                                      error_type=constants.VALIDATION_ERROR)]
        self.assertEquals(ref_errors, dnsclient1)

    def test_validate_dnslient_searches_not_greater_than_6 (self):
        self._create_standard_items_ok()
        dnsclient1 = self.model.create_item("dns-client",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1"), search ="examlpedns1.com,"
            "ericsson2.com,blah3.com,blah4.com,blah5.com,"
            "blah6.com,blah7.com")
        ref_errors = [ValidationError(
            property_name="search",
            error_message = (
                "A maximum of 6 domains per search may be specified"),
            error_type=constants.VALIDATION_ERROR)]
        self.assertEquals(ref_errors, dnsclient1)

    def test_node_validate_nameservers_position_not_a_number_from_1_to_3 (self):
        errors = []
        self._create_standard_items_ok()
        dnsclient1 = self.model.create_item("dns-client",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1", search =
            "examlpedns1.com,ericsson.com,blah.com")

        nameserver1 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver1")
            , ipaddress ="10.10.10.10", position="4")

        nameserver2 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver2")
            , ipaddress ="10.10.10.10", position="a")


        ref_errors1 = [ValidationError(property_name="position",
                                      error_message = ("Invalid value '4'."),
                                      error_type=constants.VALIDATION_ERROR)]

        ref_errors2 = [ValidationError(property_name="position",
                                      error_message = ("Invalid value 'a'."),
                                      error_type=constants.VALIDATION_ERROR)]

        self.assertEquals(nameserver1, ref_errors1)
        self.assertEquals(nameserver2, ref_errors2)

    def test_only_one_search_item(self):
        self._create_standard_items_ok()

        item_dnsclient1=self.model.create_item("dns-client",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dnsclient1")
        errors = self.plugin.create_configuration(self.context)
        item_dnsclient1=self.model.update_item(
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dnsclient1", search ="foo.com")
        errors = self.plugin.create_configuration(self.context)

    def test_node_validate_nameservers_for_removal (self):
        errors = []
        self._create_standard_items_ok()
        dnsclient1 = self.model.create_item("dns-client",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1", search =
            "examlpedns1.com,ericsson.com,blah.com")

        nameserver1 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver1")
            , ipaddress ="10.10.10.10", position="1")

        nameserver2 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver2")
            , ipaddress ="10.10.10.10", position="2")

        dnsclient1.set_applied()
        nameserver1.set_applied()
        nameserver2.set_applied()

        nameserver2 = self.model.remove_item(
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver2"
            )
        nameserver2 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver3")
            , ipaddress ="10.10.10.11", position="2")
        tasks = self.plugin.create_configuration(self)
        self.assertEqual(1, len(tasks))
        self.assertEqual('Update DNS client configuration on node "node1"', tasks[0].description)
        self.assertEqual("10.10.10.11", tasks[0].kwargs.get("name2"))

    def test_node_validate_empty_plan (self):
        errors = []
        self._create_standard_items_ok()
        dnsclient1 = self.model.create_item("dns-client",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1", search =
            "examlpedns1.com,ericsson.com,blah.com")

        nameserver1 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver1")
            , ipaddress ="10.10.10.10", position="1")

        nameserver2 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver2")
            , ipaddress ="10.10.10.10", position="2")
        dnsclient1.set_applied()
        nameserver1.set_applied()
        nameserver2.set_applied()

        tasks = self.plugin.create_configuration(self)
        self.assertEqual(0, len(tasks))

    def test_node_update_config(self):
        errors = []
        self._create_standard_items_ok()
        dnsclient1 = self.model.create_item("dns-client",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1", search =
            "examlpedns1.com,ericsson.com,blah.com")

        nameserver1 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver1")
            , ipaddress="10.10.10.10", position="1")

        nameserver2 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver2")
            , ipaddress="10.10.10.10", position="2")

        nameserver3 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver3")
            , ipaddress="fe33::5567/64", position="3")
        dnsclient1.set_applied()
        nameserver1.set_applied()
        nameserver2.set_applied()
        nameserver3.set_applied()
        dnsclient1 = self.model.update_item(
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1", search =
            "blah.com,examlpedns1.com,ericsson.com")
        tasks = self.plugin.create_configuration(self)
        self.assertEqual(1, len(tasks))
        self.assertEqual('Update DNS client configuration on node "node1"', tasks[0].description)
        self.assertEqual("blah.com examlpedns1.com ericsson.com", tasks[0].kwargs.get("search"))

    def test_node_remove_and_create_config (self):
        errors = []
        self._create_standard_items_ok()
        dnsclient1 = self.model.create_item("dns-client",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1", search =
            "examlpedns1.com,ericsson.com,blah.com")

        nameserver1 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver1")
            , ipaddress ="10.10.10.100", position="1")

        nameserver2 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1/nameservers/nameserver2")
            , ipaddress ="10.10.10.101", position="2")

        dnsclient1.set_applied()
        nameserver1.set_applied()
        nameserver2.set_applied()

        dnsclient1 = self.model.remove_item(
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client1")
        dnsclient1 = self.model.create_item("dns-client",
            "/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client2", search =
            "newexamlpedns1.com,newericsson.com,newblah.com")

        nameserver1 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client2/nameservers/nameserver1")
            , ipaddress ="10.10.10.12", position="1")

        nameserver2 = self.model.create_item("nameserver",
            ("/deployments/local_vm/clusters/cluster1"
            "/nodes/node1/configs/dns_client2/nameservers/nameserver2")
            , ipaddress ="10.10.10.13", position="2")
        tasks = self.plugin.create_configuration(self)
        self.assertEqual(2, len(tasks))
        self.assertTrue(any(x.description=='Create DNS client configuration on node "node1"' for x in tasks))
        self.assertTrue(any(x.description=='Remove DNS client configuration on node "node1"' for x in tasks))

    def test_node_validate_only_one_dnsclient_per_node (self):
         self._create_standard_items_ok()
         dnsclient1 = self.model.create_item("dns-client",
             "/deployments/local_vm/clusters/cluster1"
             "/nodes/node1/configs/dns_client1", search ="examlpedns1.com,ericsson.com,blah.com")

         dnsclient2 = self.model.create_item("dns-client",
             "/deployments/local_vm/clusters/cluster1"
             "/nodes/node1/configs/dns_client2", search ="examlpedns1.com,ericsson.com,blah.com")

         errors = self.plugin.validate_model(self)
         ref_errors = [ValidationError(
                                       item_path = ("/deployments/local_vm/"
                                                    "clusters/cluster1/"
                                                    "nodes/node1/configs/"
                                                    "dns_client2"),
                                       error_message =_('ONLY_ONE_DNSCLIENT_PER_NODE'),
                                       error_type=constants.VALIDATION_ERROR),
                       ValidationError(item_path = ("/deployments/local_vm/"
                                                    "clusters/cluster1/"
                                                    "nodes/node1/configs/"
                                                    "dns_client1"),
                                       error_message =_('ONLY_ONE_DNSCLIENT_PER_NODE'),
                                       error_type=constants.VALIDATION_ERROR)
                       ]
         self.assertTrue(all(x in ref_errors for x in errors))
