import logging
import requests
import keystoneclient.session as keystoneclient_session
import keystoneclient.exceptions


class SelOSCompute:
    session = None  # type: keystoneclient_session.Session

    def __init__(self, session):
        self.session = session
        self.endpoint_url = session.get_endpoint(service_type="compute")

    def list(self):
        """
        Return servers list with ip list
        Empty dictionary on errors
        """
        # Dictionary to save servers. Key is server id
        detailed_servers_info = dict()
        request_url = self.endpoint_url + '/servers'
        try:
            response = self.session.get(url=request_url)  # type: requests.Response
        except keystoneclient.exceptions.ClientException as err:
            logging.error("Error on get compute list {}:  {}".format(request_url, err))
            return dict()
        try:
            servers_list = response.json()
        except ValueError:
            logging.error("Error on formatting json. Get {}".format(response.text))
            return dict()
        if not isinstance(servers_list, dict) or 'servers' not in servers_list:
            logging.error("Server list broken format: ".format(servers_list))
            return dict()
        for server in servers_list['servers']:
            # Checking valid json and get id of current servers
            if isinstance(server, dict) \
                    and 'id' in server \
                    and 'name' in server \
                    and 'links' in server \
                    and isinstance(server['links'], list):
                # Getting href for server info
                for l in server['links']:
                    if isinstance(l, dict) \
                            and 'href' in l \
                            and 'rel' in l \
                            and l['rel'] == 'self':
                        # Save servers by id
                        serv_obj = SelOSServer(
                            session=self.session,
                            link=l['href']
                        )
                        # some errors on server info get. skip it
                        if serv_obj.id is None:
                            logging.warning("Skip reading server: {}".format(l['href']))
                            break
                        # Formatting output
                        detailed_servers_info[serv_obj.id] = {
                            'name': serv_obj.name,
                            'ip_list': [ip for ip in serv_obj.ip_address.keys()]
                        }
                        break
        return detailed_servers_info

    def create(self, options):
        # List of required options, minimal
        required = [
            "flavorRef",  # flavor ID or url
            "name",       # name of container
            "networks"    # network config
        ]
        # Some base checks before forward options
        if not isinstance(options, dict) \
                or 'server' not in options.keys() \
                or not isinstance(options['server'], dict):
            raise ValueError("Create server options must contained server key")
        for required_key in required:
            if required_key not in options['server']:
                raise ValueError("Option {} not found".format(required_key))
        request_url = self.endpoint_url + '/servers'
        try:
            r = self.session.post(url=request_url, json=options)
        except keystoneclient.exceptions.BadRequest as err:
            logging.error("Create failed: {}".format(vars(err.response)))
            # reraise it after log
            raise err
        response_create = r.json()
        if isinstance(response_create, dict) \
                and 'server' in response_create \
                and isinstance(response_create['server'], dict) \
                and 'links' in response_create['server']:
            del response_create['server']['links']
        return response_create


class SelOSServer:
    _session = None     # type: keystoneclient_session.Session

    def __init__(self, session, link):
        self._session = session

        self._id = None                 # ID of VM
        self._name = None               # Name of VM
        self._status = None             # Current status of VM
        self._power_status = None       # True - On, False - Off, None - Unknown
        self._addresses = None          # Dict of IP addresses. Key - IP
        self._self_link = link          # Link to API info about server
        self._bookmark_link = None
        self._volumes = None            # List of server volumes id

    @property
    def id(self):
        """
        ID server
        :return:
        """
        if self._id is None:
            self._update_base()
        return self._id

    @property
    def name(self):
        """
        Name of the server
        :return:
        """
        if self._name is None:
            self._update_base()
        return self._name

    @property
    def status(self):
        """
        Current status of server
        :return:
        :rtype: None, str
        """
        if self._status is None:
            self._update_base()
        return self._status

    @property
    def power(self):
        """
        Power status of server
        :return: True - On, False - Off
        :rtype: None, bool
        """
        if self._power_status is None:
            self._update_base()
        return self._power_status

    @property
    def ip_address(self):
        """
        Dictionary of ip addresses. Key as IP address. IP address may have 'mac' and 'type' of IP.
        :return:
        :rtype: None, Dict
        """
        if self._addresses is None:
            self._update_base()
        return self._addresses

    def _update_base(self):
        """
        Parsing server info, Require self._self_link
        """
        if self._self_link is None:
            return
        try:
            r = self._session.get(self._self_link)          # type: requests.Response
        except keystoneclient.exceptions.EndpointNotFound:
            logging.error("No such endpoint: {}".format(self._self_link))
            return
        try:
            server_base_status = r.json()['server']
        except ValueError as err:
            logging.error("Json request parse error {}: {}".format(r, err))
            return
        except KeyError as err:
            logging.error("Json request don't have server info: {}".format(err))
            return
        try:
            # Set ID
            self._id = server_base_status['id']
            # Set Name
            self._name = server_base_status['name']
            # Set Power State
            if int(server_base_status['OS-EXT-STS:power_state']) > 0:
                self._power_status = True
            else:
                self._power_status = False
            # Set IP addresses and MACs
            self._addresses = dict()
            if 'addresses' in server_base_status and isinstance(server_base_status['addresses'], dict):
                for net in server_base_status['addresses'].keys():
                    # Networks
                    for net_interface in server_base_status['addresses'][net]:
                        # Interfaces
                        if 'addr' not in net_interface:
                            continue
                        ip = net_interface['addr']
                        if ip is None or ip == '':
                            continue
                        self._addresses[ip] = dict()
                        if 'OS-EXT-IPS-MAC:mac_addr' in net_interface:
                            self._addresses[ip]['mac'] = net_interface['OS-EXT-IPS-MAC:mac_addr']
                        if 'OS-EXT-IPS:type' in net_interface:
                            self._addresses[ip]['type'] = net_interface['OS-EXT-IPS:type']
            # Set Volumes IDs
            self._volumes = list()
            if 'os-extended-volumes:volumes_attached' in server_base_status \
                    and isinstance(server_base_status['os-extended-volumes:volumes_attached'], list):
                for volume in server_base_status['os-extended-volumes:volumes_attached']:
                    if isinstance(volume, dict) and 'id' in volume:
                        self._volumes.append(volume['id'])
        except KeyError as err:
            logging.error("Error get server property: {}".format(err))
            return


class SelOSFlavor:
    session = None  # type: keystoneclient_session.Session

    def __init__(self, session):
        self.session = session
        self.compute_endpoint_url = session.get_endpoint(service_type="compute")

    def list(self):
        returned_flavors_data = {'flavors': list()}
        try:
            r = self.session.get(url=self.compute_endpoint_url + "/flavors")  # type: requests.Response
        except keystoneclient.exceptions.ClientException as err:
            logging.error("Error on getting flavors: {}".format(err))
            return dict()
        data = r.json()
        if not isinstance(data, dict) or 'flavors' not in data:
            raise ValueError("Wrong format of flavors from server")
        # output only id and name, ignore other
        if isinstance(data['flavors'], list):
            for flavor in data['flavors']:
                if isinstance(flavor, dict) \
                        and 'id' in flavor \
                        and 'name' in flavor:
                    new_flavor = {'id': flavor['id'], 'name': flavor['name']}
                    returned_flavors_data['flavors'].append(new_flavor)
        return returned_flavors_data
