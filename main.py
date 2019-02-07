import logging

import json
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
import webapp2
import google.auth.transport.requests
import requests_toolbelt.adapters.appengine
from google.cloud import storage
import zendesk


requests_toolbelt.adapters.appengine.monkeypatch()
HTTP_REQUEST = google.auth.transport.requests.Request()

gcs_client = storage.Client(project='e2z-proxy')
bucket = gcs_client.get_bucket("e2z-proxy-attachments")
with open('config.json', 'r') as f:
    data = f.read()
config = json.loads(data)
zd = zendesk.ZenDesk(config['ZENDESK_TOKEN'])

class LogSenderHandler(InboundMailHandler):
    def receive(self, mail_message):
        user = ""
        if hasattr(mail_message,'reply_to'):
            if mail_message.reply_to ==  "google-cloud-partner-directory@google.com":
                user = mail_message.reply_to
                tag = "google-cloud-partner-directory"
        if mail_message.sender == "no-reply@squarespace.info":
            user = mail_message.sender
            tag = "no-reply@squarespace.info"
        if user == "":
            logging.warning("Non Auth sender %s ", mail_message.sender)
            return
        if hasattr(mail_message, 'subject'):
            subject = mail_message.subject
        else:
            subject= "No Subject"
        plaintext_bodies = mail_message.bodies('text/plain')
        body_parts = ""
        for content_type, body in plaintext_bodies:
            body_parts = body_parts + body.decode()

        token = None
        for attachment in getattr(mail_message, 'attachments', []):
            token = zd.upload(attachment.filename,attachment.payload.decode())
            break
        requester_id = zd.get_user_id(user, "")
        logging.info(requester_id)
        description = ''.join(body_parts)
        submit_ticket(requester_id, subject, description, token, tag)



def submit_ticket(requester_id, subject, description,token, tag):
    new_ticket = {
        'ticket': {
            'requester_id': requester_id,
            'subject': subject,
            'description': description,
            "comment": { "body": description, "uploads":  [token] },
            "priority": 0,
            "additional_collaborators": ['ranr@doit-intl.com', 'vadim@doit-intl.com','ytc@doit-intl.com'],
            "tags": [tag],
            "group_id": 25032363
        }
    }
    resp = zd.ticket_create(new_ticket)
    if resp.status_code != 201:
        logging.error("Couldn't create a ticket for %s %s %s ", requester_id,
                      str(resp.status_code), resp.json()['error'])


class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.set_status(200)
        self.response.out.write('ok')

app = webapp2.WSGIApplication([
    LogSenderHandler.mapping(),
    webapp2.Route(r'/', handler=MainHandler, name='home')
], debug=True)