import yaml
import os
import pwd
import logging
from keystoneauth1.identity import v3 as keystoneidentity
from keystoneauth1 import session as keystonesession


class SelOSAuth:
    BASE_APP_CONFIG_PATH = '.selectelclo/app_clouds.yaml'
    BASE_USER_CONFIG_PATH = '.selectelclo/user_clouds.yaml'
    DEFAULT_TIMEOUT = 10

    def __init__(self, cloud_name):
        self.cloud_name = cloud_name
        # Filled by config files
        self.auth_url = None
        self.app_secret = None
        self.app_id = None
        self.domain_id = None
        self.domain_name = None
        self.project_id = None
        self.project_name = None
        self.username = None

        self._session = None

    @property
    def session(self):
        if self._auth():
            return self._session
        return None

    @property
    def token(self):
        if self.session is not None:
            return self.session.get_token()
        return None

    def _read_auth_base_config(self, type_a):
        # Type - app, user
        auth_data = dict()
        home_dir = pwd.getpwuid(os.getuid()).pw_dir
        if type_a == 'app':
            base = self.BASE_APP_CONFIG_PATH
        elif type_a == 'user':
            base = self.BASE_USER_CONFIG_PATH
        else:
            raise ValueError("Only user or app types accepted")
        with open(home_dir + '/' + base, 'r') as stream:
            try:
                auth_data = yaml.load(stream, Loader=yaml.SafeLoader)
            except yaml.YAMLError as err:
                raise ValueError("error loading yaml config for auth: %s" % err)
            try:
                if self.cloud_name not in auth_data['clouds'].keys():
                    raise ValueError("Cloud %s not found in config" % self.cloud_name)
                if type_a == 'app' \
                        and (auth_data['clouds'][self.cloud_name]['auth_type'] != 'v3applicationcredential'
                             or auth_data['clouds'][self.cloud_name]['auth']['application_credential_secret'] is None):
                    raise ValueError("Config must contain application credentials v3")
                elif type_a == 'user' \
                        and (auth_data['clouds'][self.cloud_name]['auth']['username'] is None
                             or auth_data['clouds'][self.cloud_name]['auth']['project_id'] is None):
                    raise ValueError("Config must contain username and project_id")
            except KeyError:
                raise ValueError("Wrong cloud.yaml format")
        return auth_data['clouds'][self.cloud_name]

    def _read_auth_app_config(self):
        return self._read_auth_base_config('app')

    def _read_auth_user_config(self):
        return self._read_auth_base_config('user')

    def _auth(self):
        # Reading application credentials if not read before
        if self.app_id is None \
                or self.app_secret is None \
                or self.auth_url is None:
            try:
                app_auth = self._read_auth_app_config()
            except ValueError as err:
                logging.error("Error on reading ~/{0}: {1}".format(self.BASE_APP_CONFIG_PATH, err))
                return False
            # App credential ok
            self.auth_url = app_auth['auth']['auth_url']
            self.app_id = app_auth['auth']['application_credential_id']
            self.app_secret = app_auth['auth']['application_credential_secret']
        if self._session is None:
            new_session = self._get_new_session()
            if new_session is None:
                logging.error("No session")
                return False
            else:
                self._session = new_session
        return True

    def _get_new_session(self):
        try:
            auth = keystoneidentity.ApplicationCredential(
                auth_url=self.auth_url,
                application_credential_secret=self.app_secret,
                application_credential_id=self.app_id,
            )
        except KeyError as err:
            logging.error("Error reading application credentials: {}".format(err))
            return None
        return keystonesession.Session(auth=auth, timeout=self.DEFAULT_TIMEOUT)
