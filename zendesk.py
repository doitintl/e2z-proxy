

import requests
import logging
import google.auth.transport.requests
import requests_toolbelt.adapters.appengine
from google.appengine.api import urlfetch

urlfetch.set_default_fetch_deadline(60)

requests_toolbelt.adapters.appengine.monkeypatch()
HTTP_REQUEST = google.auth.transport.requests.Request()


class ZenDesk(object):

    def __init__(self,token):
        self.token=token
        self.user = 'help@doit-intl.com/token'
        self.base_url = 'https://doitintl.zendesk.com/api/v2/'


    def api_call_get(self, call):
        url = self.base_url + call
        response = requests.get(url, auth=(self.user, self.token))
        return response

    def api_call_post(self, call,data):
        url = self.base_url + call
        response = requests.post(url,json=data, auth=(self.user, self.token))
        return response


    def ticket_create(self, data):
        api_path = "tickets.json"
        return self.api_call_post(api_path, data=data)

    def get_user_id(self, email, name):
        resp = self.api_call_get('users/search.json?query='+email)
        if (len(resp.json()['users'])) <1:
            return self.create_user(email, name)
        return resp.json()['users'][0]['id']

    def create_user(self, email, name):
        new_user =  {"user": {"name": email, "email": email}}
        resp = self.api_call_post('users.json' , new_user)
        if resp.status_code != 201:
            logging.error("Couldn't create user %s %s %s", email, str(resp.status_code), resp.json()['error'])
            return -1
        logging.info("New user created %s", email)
        return resp.json()['user']['id']


    def upload(self, filename,contents):
        api_path = "uploads.json?filename="+filename
        headers = {"Content-Type": "application/octet-stream"}
        resp = requests.post(self.base_url + api_path, auth=(self.user, self.token), data=contents, headers=headers, timeout=60)
        if resp.status_code != 201:
            logging.error("Couldn't upload file %s %s %s ", filename,
                          str(resp.status_code), resp.json()['error'])
            return None
        token = resp.json()['upload']['token']
        return token
