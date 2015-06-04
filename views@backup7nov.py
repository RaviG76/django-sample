from django.template import Context,loader
from django.http import HttpResponse, StreamingHttpResponse
from django.core.context_processors import csrf
from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.middleware.csrf import get_token

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth import authenticate

from django.contrib.auth.models import User    
from django.views.generic.base import TemplateView
import json

from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import *
import re
from django.core.mail import send_mail, BadHeaderError
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context
import httplib2
import requests
http = httplib2.Http()
from django.utils.encoding import iri_to_uri
from django.utils.http import urlquote
import hashlib
import hmac
import time
from pprint import pprint # to remove later
from freshdesk_api import contacts, tickets
import ast
methods_allowed = ['GET','POST']

# lead listening service
def process_request(request, method, **args):
    path = request.path
    content = str(request.GET["data"]).encode('utf8')
    content = content.replace('%25253a', ':')
    content = content.replace('%25252b', ' ')
    content = content.replace('%252b', ' ')
    content = content.replace('%253a', ':')
    content = content.replace('%3a', ':')
    content = content.replace('%2b', ' ')
    response = {}    
    try:
        # validate request method only post allowed
        if request.META['REQUEST_METHOD'] not in methods_allowed:
            result = {'status':'403','data':'request method not allowed'}
            return HttpResponse(json.dumps(result), content_type='application/json')
        else:
            slashparts = path.split('/')
            #print slashparts
            basename = '/'.join(slashparts[:3]) + '/'
            dirname = '/'.join(slashparts[:-1]) + '/'
            #content = ast.literal_eval(str(content).encode('utf8'))
            #content = json.loads(content)
            if slashparts[5]=='listen':
                content         = ast.literal_eval(content)
                Username        = content['LeadRequest']['Username']
                DriversLicense  = content['LeadRequest']['DriversLicense']
                ClientIpAddress = content['LeadRequest']['ClientIpAddress']
                SSN             = content['LeadRequest']['SSN']
                Email           = content['LeadRequest']['Email']
                # call functions of the modules as per dynamic methods from request
                status_code, data = decision(list(DriversLicense,SSN,Email), **args)
            else:
                result = {'status':400,'data':'Bad request, missing method type attribute !!'}
                return HttpResponse(json.dumps(result), content_type='application/json')
            result = {'status':status_code,'data':data}
            return HttpResponse(json.dumps(result), content_type='application/json')
    except Exception,e:
            res = str(e)
            data = {'error': res}
            return HttpResponse(json.dumps(data), content_type='application/json')

# lead decisioning service
def decision(content):    
    return {101, content}