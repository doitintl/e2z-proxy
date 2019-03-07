import logging

import json
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
import webapp2
import google.auth.transport.requests
import requests_toolbelt.adapters.appengine
import zendesk


requests_toolbelt.adapters.appengine.monkeypatch()
HTTP_REQUEST = google.auth.transport.requests.Request()


with open('config.json', 'r') as f:
    data = f.read()
config = json.loads(data)

with open('safe_senders.json', 'r') as f:
   data = f.read()
safe_senders=json.loads(data)

zd = zendesk.ZenDesk(config['ZENDESK_TOKEN'])

def get_sender_addr(addr):
    ind = addr.find('<')
    if ind ==-1:
        return addr
    return addr[ind+1:-1]

def validate_mail(addr):
    for s in safe_senders['senders']:
        if get_sender_addr(addr) == s:
            return True
    for s in safe_senders['reply_to']:
        if get_sender_addr(addr) == s:
            return True
    return False

def get_user_from_body(body):
    lines = body.splitlines()
    found = 0
    for l in lines:
        if found == 2:
            return l
        if found == 1:
            found = 2
        if l == 'Contact Email':
            found = 1
    return ""



class LogSenderHandler(InboundMailHandler):
    def receive(self, mail_message):
        user = ""
        tag = ""
        if not validate_mail(mail_message.sender):
            logging.warning("Non Auth sender %s ", mail_message.sender)
            return
        if hasattr(mail_message, 'reply_to'):
            for r in safe_senders['reply_to']:
                if get_sender_addr(mail_message.sender) == r:
                    user = get_sender_addr(mail_message.reply_to)
                    tag = r
                    break
        for s in safe_senders['senders']:
            if hasattr(mail_message, 'reply_to'):
                user = get_sender_addr(mail_message.reply_to)
                tag = s
                break
            else:
                if get_sender_addr(mail_message.sender) == s:
                    user = get_sender_addr(mail_message.sender)
                    tag = s
                    break
        if hasattr(mail_message, 'subject'):
            subject = mail_message.subject
        else:
            subject= "No Subject"
        plaintext_bodies = mail_message.bodies('text/plain')
        body_parts = ""
        for content_type, body in plaintext_bodies:
            body_parts = body_parts + body.decode()
        #HACK
        if user == "":
            user = get_user_from_body(body_parts)
        logging.info("User  %s", user)
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