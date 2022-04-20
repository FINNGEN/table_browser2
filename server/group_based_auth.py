from flask import redirect, request, url_for, session
from flask_login import current_user
import threading
import imp
import json
import requests
from collections import defaultdict
from rauth import OAuth2Service

from googleapiclient.discovery import build
from google.oauth2 import service_account

try:
    _conf_module = imp.load_source('config', 'config.py')
except Exception:
    print('Could not load config.py from the current directory')
    quit()
config = {key: getattr(_conf_module, key)
          for key in dir(_conf_module) if not key.startswith('_')}

if config["authentication"]:
    group_names = config['group_auth']["GROUPS"]
    service_account_file = config['group_auth']["SERVICE_ACCOUNT_FILE"]
    delegated_account = config['group_auth']["DELEGATED_ACCOUNT"]

    service_account_scopes = [
        "https://www.googleapis.com/auth/admin.directory.group.readonly",
        "https://www.googleapis.com/auth/admin.directory.user.readonly",
        "https://www.googleapis.com/auth/admin.directory.group.member.readonly",
    ]

    # set credentials
    creds = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=service_account_scopes
    )
    delegated_creds = creds.with_subject(delegated_account)
    services = defaultdict(
        lambda: build("admin", "directory_v1", credentials=delegated_creds)
    )

    whitelist = config["login"]["whitelist"] if "whitelist" in config["login"].keys() else [
                                                                                    ]

else:
    group_names = []
    service_account_file = None
    delegated_account = None
    service_account_scopes = None
    creds = None
    delegated_creds = None
    services = None
    whitelist = None


def get_all_members(group_names):
    members = []
    for name in group_names:
        all = services[threading.get_ident()].members().list(
            groupKey=name).execute()
        members.extend(all["members"])
    return members


def get_member_status(username):
    allmembers = get_all_members(group_names)

    for m in allmembers:
        user = m["email"]
        if "gserviceaccount" in user:  # service accounts are excluded
            continue
        if user == username:
            return m["status"]


def verify_membership(username):

    if username in whitelist:
        return True
    # auth service .hasMember will only work for accounts of the domain
    elif not username.endswith("@finngen.fi"):
        return False
    else:
        for name in group_names:
            r = (
                services[threading.get_ident()]
                .members()
                .hasMember(groupKey=name, memberKey=username)
                .execute()
            )
            if r["isMember"] is True:
                return True
    # default to false
    return False


def before_request():
    if not config['authentication']:
        print('anonymous visited {!r}'.format(request.path))
        return None
    elif current_user is None or not hasattr(current_user, 'email'):
        return redirect(url_for('get_authorized',
                                _scheme='https',
                                _external=True))
    elif not verify_membership(current_user.email):
        print('{} is unauthorized and visited {!r}'.format(
            current_user.email, request.path))
        session['original_destination'] = request.path
        return redirect(url_for('get_authorized',
                                _scheme='https',
                                _external=True))
    else:
        print('{} visited {!r}'.format(current_user.email, request.path))
        return None


class GoogleSignIn(object):
    def __init__(self, current_app):
        google_params = self._get_google_info()
        self.service = OAuth2Service(
            name='google',
            client_id=config['login']['GOOGLE_LOGIN_CLIENT_ID'],
            client_secret=config['login']['GOOGLE_LOGIN_CLIENT_SECRET'],
            authorize_url=google_params.get('authorization_endpoint'),
            base_url=google_params.get('userinfo_endpoint'),
            access_token_url=google_params.get('token_endpoint')
        )

    def _get_google_info(self):
        r = requests.get(
            'https://accounts.google.com/.well-known/openid-configuration')
        r.raise_for_status()
        return r.json()

    def authorize(self):
        return redirect(self.service.get_authorize_url(
            scope='email',
            response_type='code',
            prompt='select_account',
            redirect_uri=self.get_callback_url())
        )

    def get_callback_url(self):
        return url_for('oauth_callback_google',
                       _scheme='https',
                       _external=True)

    def callback(self):
        if 'code' not in request.args:
            return (None, None)
        # The following two commands pass **kwargs to requests.
        oauth_session = self.service.get_auth_session(
                data={'code': request.args['code'],
                      'grant_type': 'authorization_code',
                      'redirect_uri': self.get_callback_url()
                      },
                decoder=lambda x: json.loads(x.decode('utf-8'))
        )
        me = oauth_session.get('').json()
        return (me['name'] if 'name' in me else me['email'],
                me['email'])
