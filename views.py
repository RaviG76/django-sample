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
from app.api.models import *
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
import datetime
from pprint import pprint # to remove later
from freshdesk_api import contacts, tickets
import ast
from freshdesk_api.tickets import *
from django.core.mail import send_mail
methods_allowed = ['GET','POST']

from geopy.geocoders import Nominatim
from geopy.geocoders import GoogleV3
from geopy.distance import great_circle

from djstripe.models import *

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User
    
''' lead listening service '''
def process_request(request, method, **args):
    try:			
        path = request.path
        client_ip =request.META['REMOTE_ADDR']
        content =str(request.GET["data"]).encode('utf8')
        content =content.replace('%25253a', ':')
        content =content.replace('%25252b', ' ')
        content =content.replace('%252b', ' ')
        content =content.replace('%253a', ':')
        content =content.replace('%3a', ':')
        content =content.replace('%2b', ' ')
        response = {}    
        # validate request method only post allowed
        if request.META['REQUEST_METHOD'] not in methods_allowed:
            result = {'status':'403','data':'request method not allowed'}
            return HttpResponse(json.dumps(result), content_type='application/json')
        else:
            slashparts = path.split('/')
            basename = '/'.join(slashparts[:3]) + '/'
            dirname = '/'.join(slashparts[:-1]) + '/'
            if slashparts[5]=='listen':
                content =ast.literal_eval(str(content).encode('utf8'))
                DriversLicense      =content['LeadRequest']['DriversLicense']
                Email               =content['LeadRequest']['Email']
                SSN                 =content['LeadRequest']['SSN']
                # call desision service pass lead flash request data
                status_code,data  = decision(client_ip,DriversLicense,SSN,Email,content,**args)
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
def decision(client_ip,License,ssn,email,content):
    try:
        #print "here"
        #check value in lead table
        Email           =content['LeadRequest']['Email']
        Firstname       =content['LeadRequest']['Firstname']
        Lastname        =content['LeadRequest']['Lastname']
        CellPhone       =content['LeadRequest']['CellPhone']
        #print "here 1"
        ''' Make sure we haven?t purchased the lead 3 times consecutive times where each time we did not sell the lead.
            * get what is the status of offered_to column in leads table offered_to column should be null for email, ssn.
            * calculate distance of current location [ calculate distance by comparing longitute and lattitute with all existing lenders. ]
            * if it is less than 5 miles add lead to database.
        '''
        print "here 2"        
        if lender_in_5_miles(content):
            ''' query string to check if lead exists in database ''' 
            lead = Leads.objects.filter(social_security=ssn, drivers_license=License, Email=Email)
            if lead is not None:
                for data in lead:
                    print data.offered_to
                
                if data.offered_to:
                    ''' Lead already exists, rejected, call decisioning rejection() function '''
                    return 0, 'lead exists and sold'
                else:
                    ''' check how many cosecutive times lead has entries in '''
                    
                    ''' check subscription of closest lender to this lead and push the lead into lead table with lender ID in its affered_to column '''
                    return 0, 'Lead rejected, already in database and sold.'
            else:
                ''' * lead is fresh new and will go into database
                    * check subscription of closest lender to this lead and push the lead into lead table with lender ID in its affered_to column
                '''
                
            return 0,'hello'
        else:
            lead = Leads.objects.filter(social_security=ssn, drivers_license=License, offered_to__isnull=False)
            ''' Lead rejected, not in lenders store range, call decisioning rejection() function '''
            return 0,'Lead rejected, not in lenders store range, call decisioning rejection() function'
    except Exception,e:
        res = str(e)
        data = {'error': res}
        return HttpResponse(json.dumps(data), content_type='application/json')
    
''' calculate if local lenders is available in 5 miles area to this lead '''
def lender_in_5_miles(content):
    ''' Calculate distance and longi latti from zip code '''
    geolocator = GoogleV3()
    location = geolocator.geocode(content['LeadRequest']['EmploymentInfo']['Zip'])
    if location:
        cust_loc = (location.longitude,location.latitude)        
        lenders  = User.objects.filter(group='Lenders')
        for lender in lenders:
            #print lender.username
            lend_loc =(lender.longitude,lender.latitude)
            distance = great_circle(cust_loc, lend_loc).miles
            print "distance check"
            if distance <= 5000000:            
                print lender.id
                customer = Customer.objects.filter(user_id=lender.id) # extarct data here
                for cust in customer:
                    subscription = CurrentSubscription.objects.filter(customer_id=cust.id, status='active') # extarct data here
                    if subscription is not None:
                        print "yes"
                    else:
                        print "NO"
                    #print distance
                return True
            else:
                return False
    return False
    
''' lead value check '''
def leadstatus(client_ip,ssn,content):
    try:
        print "leadstatus working",ssn
        leaddesicion=LeadDecisioning.objects.filter(social_security=ssn)
        if leaddesicion:
            for lead in leaddesicion:
                print lead.id
            data="Already Exist ssn"
            result = {'status':101,'data':data}
            return HttpResponse(json.dumps(result), content_type='application/json')
        else:
            data="Accepted"
            return data
    except Exception,e:
            res = str(e)
            data = {'error': res}
            return HttpResponse(json.dumps(data), content_type='application/json')

''' lead accept function got triggerred '''
def leadAccetp(client_ip):
    try:
        print "client_ip",ip_address
        LeadDecisioning.objects.create(
            ip_address=client_ip,
            social_security=ssn,
            Decision_status='Accept',
            decisioning_data=content
            )
        result = {'status':200,'data':LeadDecisioning}
        return HttpResponse(json.dumps(result), content_type='application/json')
    except Exception,e:
            res = str(e)
            data = {'error': res}
            return HttpResponse(json.dumps(data), content_type='application/json')  
    
'''add lead in user tabel'''    
def UserCreate(email,content):
    try:
        HomeState           =content['LeadRequest']['HomeState']
        DriversLicenseState =content['LeadRequest']['DriversLicenseState']
        DriversLicense      =content['LeadRequest']['DriversLicense']
        DOB                 =content['LeadRequest']['DOB']
        WorkPhone           =content['LeadRequest']['WorkPhone']
        HomeAddress         =content['LeadRequest']['HomeAddress']
        Username            =content['LeadRequest']['Username']
        Firstname           =content['LeadRequest']['Firstname']
        Lastname            =content['LeadRequest']['Lastname']
        Email               =content['LeadRequest']['Email']
        HomeCity            =content['LeadRequest']['HomeCity']
        Password            =content['LeadRequest']['Password']
        Language            =content['LeadRequest']['Language']
        CellPhone           =content['LeadRequest']['CellPhone']
        HomePhone           =content['LeadRequest']['HomePhone']
        State               =content['LeadRequest']['EmploymentInfo']['State']
        Zip                 =content['LeadRequest']['EmploymentInfo']['Zip']
        City                =content['LeadRequest']['EmploymentInfo']['City']       
        user=User.objects.filter(email=email)
        if user:
            for userdata in user:
                print userdata
                userid=userdata.id
        else:
            empty=None
            User.objects.create(            
                    entityname  =Firstname,
                    first_name  =Firstname,
                    last_name   =Lastname,
                    password    =Password,
                    email       =Email,
                    ownerName   =Firstname+Lastname,
                    ownerEmail  =Email,
                    #storeName  =storeName,
                    storeAddress=HomeAddress,
                    group       ='Customers',
                    state       =State,
                    phone_number=CellPhone,
                    zip_code    =Zip,
                    managerName =empty,
                    managerEmail=empty,
                    service     =empty,
                    product_at_store='Null',
                    #longitude  =longitude,
                    #latitude   =latitude,
                    is_active   =0,
                    city        =City,
                    username    =Username
                    )
            new_user=User.objects.filter(email=email)
            for user in new_user:
                userid=user.id                
            print "userid",userid           
        return userid
    except Exception,e:
            res = str(e)
            data = {'error': res}
            return HttpResponse(json.dumps(data), content_type='application/json')    

''' lead add in lead tabel '''
def leadregister(userid,content):
        print "leadregister",userid
        try:
            HomeState           =content['LeadRequest']['HomeState']
            DriversLicenseState =content['LeadRequest']['DriversLicenseState']
            DriversLicense      =content['LeadRequest']['DriversLicense']
            DOB                 =content['LeadRequest']['DOB']
            MailCity            =content['LeadRequest']['MailCity']
            ClientIpAddress     =content['LeadRequest']['ClientIpAddress']
            WorkPhone           =content['LeadRequest']['WorkPhone']
            HomeAddress         =content['LeadRequest']['HomeAddress']
            MailZip             =content['LeadRequest']['MailZip']
            Username            =content['LeadRequest']['Username']
            WorkPhoneExt        =content['LeadRequest']['WorkPhoneExt']
            Firstname           =content['LeadRequest']['Firstname']
            Lastname            =content['LeadRequest']['Lastname']
            Email               =content['LeadRequest']['Email']
            HomeCity            =content['LeadRequest']['HomeCity']
            Password            =content['LeadRequest']['Password']
            HomeZip             =content['LeadRequest']['HomeZip']
            TimeAtAddress       =content['LeadRequest']['TimeAtAddress']
            BankInfo            =content['LeadRequest']['BankInfo']
            Language            =content['LeadRequest']['Language']
            CellPhone           =content['LeadRequest']['CellPhone']
            Gender              =content['LeadRequest']['Gender']
            Fax                 =content['LeadRequest']['Fax']
            BestTimeToCall      =content['LeadRequest']['BestTimeToCall']
            LoanInfo            =content['LeadRequest']['LoanInfo']
            MailState           =content['LeadRequest']['MailState']
            RefID               =content['LeadRequest']['RefID']
            SSN                 =content['LeadRequest']['SSN']
            References          =content['LeadRequest']['References']
            MailAddress         =content['LeadRequest']['MailAddress']
            HomePhone           =content['LeadRequest']['HomePhone']            
            '''Employinfo'''
            EmploymentLength    =content['LeadRequest']['EmploymentInfo']['EmploymentLength']
            City                =content['LeadRequest']['EmploymentInfo']['City']
            Supervisor          =content['LeadRequest']['EmploymentInfo']['Supervisor']
            PhoneExt            =content['LeadRequest']['EmploymentInfo']['PhoneExt']
            Zip                 =content['LeadRequest']['EmploymentInfo']['Zip']
            PayrollType         =content['LeadRequest']['EmploymentInfo']['PayrollType']
            Shift               =content['LeadRequest']['EmploymentInfo']['Shift']
            PayFrequency        =content['LeadRequest']['EmploymentInfo']['PayFrequency']
            MonthlyIncome       =content['LeadRequest']['EmploymentInfo']['MonthlyIncome']
            Phone               =content['LeadRequest']['EmploymentInfo']['Phone']
            State               =content['LeadRequest']['EmploymentInfo']['State']
            IncomeType          =content['LeadRequest']['EmploymentInfo']['IncomeType']
            Address             =content['LeadRequest']['EmploymentInfo']['Address']
            SecondNextPayDay    =content['LeadRequest']['EmploymentInfo']['SecondNextPayDay']
            Employer            =content['LeadRequest']['EmploymentInfo']['Employer']
            NextPayDay          =content['LeadRequest']['EmploymentInfo']['NextPayDay']
            Occupation          =content['LeadRequest']['EmploymentInfo']['Occupation']            
            '''Bank info'''
            AbaNumber           =content['LeadRequest']['BankInfo']['AbaNumber']
            AccountLength       =content['LeadRequest']['BankInfo']['AccountLength']
            CheckingAccount     =content['LeadRequest']['BankInfo']['CheckingAccount']
            AccountToUse        =content['LeadRequest']['BankInfo']['AccountToUse']
            BankName            =content['LeadRequest']['BankInfo']['BankName']
            '''Loan'''
            Amount              =content['LeadRequest']['LoanInfo']['Amount']
            DueDate             =content['LeadRequest']['LoanInfo']['DueDate']
            '''Reefrence'''
            ref_Lastname        =content['LeadRequest']['References']['Reference']['Lastname']
            ref_Relation        =content['LeadRequest']['References']['Reference']['Relation']
            ref_Firstname       =content['LeadRequest']['References']['Reference']['Firstname']
            ref_Phone           =content['LeadRequest']['References']['Reference']['Phone']            
            currenttime=datetime.datetime.now().replace(microsecond=0)
            print "datat",currenttime        
            addlead=leadtable= Leads.objects.create(
                                first_name      =Firstname,
                                last_name       =Lastname,
                                street_addr1    =HomeAddress,
                                #street_addr2=MailAddress,
                                city            =HomeCity,
                                state           =HomeState,
                                Zip             =HomeZip,
                                social_security =SSN,
                                phone_home      =HomePhone,
                                phone_cell      =CellPhone,
                                phone_work      =WorkPhone,
                                phone_work_ext  =WorkPhoneExt,
                                Email           =Email,
                                birth_date      =DOB,
                                employer_name   =Employer,
                                pay_frequency   =PayFrequency,
                                mailadress      =MailAddress,
                                mailcity        =MailCity,
                                mailstate       =MailState,
                                mailzip         =MailZip,
                                timeataddress   =TimeAtAddress,
                                besttimetocall  =BestTimeToCall,
                                fax             =Fax,
                                checkingaccount =CheckingAccount,
                                accounttouse    =AccountToUse,
                                accountlength   =AccountLength,
                                payrolltype     =PayrollType,
                                pay_day1        =NextPayDay,
                                pay_day2        =SecondNextPayDay,
                                bank_aba        =AbaNumber,
                                bank_account    =CheckingAccount,
                                bank_name       =BankName,
                                income_monthly  =MonthlyIncome,
                                Occupation      =Occupation,
                                Shift           =Shift,
                                employmentlength=EmploymentLength,
                                emp_address     =Address,
                                emp_city        =City,
                                emp_State       =State,
                                emp_zip         =Zip,
                                emp_Supervisor  =Supervisor,
                                emp_phone       =Phone,
                                emp_phoneext    =PhoneExt,
                                references_firstname=ref_Firstname,
                                references_lastname =ref_Lastname,
                                references_phone    =ref_Phone,
                                references_relation =ref_Relation,
                                IncomeType      =IncomeType,
                                employer        =Employer,
                                loan_amount     =Amount,
                                loan_duedate    =DueDate,
                                #own_home=data['own_home'],
                                drivers_license =DriversLicense,
                                drivers_license_st  =DriversLicenseState,
                                #client_url_root=data['client_url_root'],
                                client_ip_address   =ClientIpAddress,
                                #email_alternate=data['email_alternate'],
                                #months_employed=data['months_employed'],
                                income_type     =IncomeType,
                                #is_military=data['is_military'],
                                user_id         =userid,
                                #bank_account_type=data['bank_account_type'],
                                #requested_amount=data['requested_amount'],
                                #months_at_address=data['months_at_address'],
                                #months_at_bank=data['months_at_bank'],
                                created_on      =currenttime
                                )
            print "die",addlead
            return addlead
        except Exception,e:
                res = str(e)
                return {101,res}

''' Dispatch email '''
def Send_email(ssn,firstname,lastname,email):
    try:
        print "email check ",email
        message1="Hi "+firstname + lastname+"\n\n"
        print "setting.site",setting.site
        message2=settings.SITE_URL+"/accounts/register/?ssn="+ssn
        message3="\n\nThanks"
        email_set=send_mail("Lead" , message1+message2+message3, email
        [email], fail_silently=False)
        return email_set
    except Exception,e:
        res = str(e)
        data = {'error': res}
        return HttpResponse(json.dumps(data), content_type='application/json')
    
''' Generate freshdesk ticket on api hit '''
def lead_ticket(firstname,lastname,phone,email):
    adminuser = User.objects.filter(is_staff=1)
    emailid=[]
    for admin in adminuser:
        emailid.append(admin.email)
    ccemail=emailid
    title="New ticket add by api"
    des1="Hi \n\n"
    des2="New Ticket add\n"
    des3="Name:"+firstname+lastname
    des4="\nEmail:"+email
    des5="\nPhone:"+phone
    des6="\n\nThanks"
    ticketsytem={'cc_email': ccemail, 'des':des1+des2+des3+des4+des5+des6, 'sub':title , 'email': email}
    statusapi=ticket_create(ticketsytem);
    print "ticket status",statusapi
    pass