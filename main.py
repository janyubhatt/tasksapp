#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
import re
from models import userModel
import hashlib
import hmac
import string
import utils
#Initializes templating features of Jinja2 framework
template_dir = os.path.join(os.path.dirname(__file__))
jinja_environment = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)


#Base handler contains basic templating functions 
class BaseHandler(webapp2.RequestHandler):
    # Writes string  
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
        
    #returns template from string path with string substitution parameters in mapping called params
    def render_str(self,template, **params):
        template = jinja_environment.get_template(template)
        return template.render(params)

    #takes string template path and mapping of template paramters and renders them
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    #combines mapping of errors and fields into mapping called template_values. 
    #template_values is returned to be used as value of all fields for rendering
    def createTemplate_values(self,errors,fields):
        template_values= {'fields':fields,
                         'errors':errors}
        return template_values    

    #creates a session cookie based on user id
    def createSessionCookie(self,userId):
        userHash = utils.make_hash(userId,userId)
        self.response.headers.add_header("Set-Cookie", "userId = %s; Path = /" %userHash)
        return userHash

#checks if hashed session cookie is an actual hash generated by my hashing method
#if session cookie works, then it returns the userId. If not, returns false
    def validateSessionCookie(self,userIdHash):
        userId = userIdHash.split("|")[0]
        if(utils.valid_hash(userId,userIdHash)):
            return userId
        else:
            return False    

    #called at the beginning of each get function. Verifies cookies, and loads correct template with errors if any.
    def renderStart(self,template, errors = {}, fields = {}):
        userIdCookie_str = self.request.cookies.get("userId")
        if userIdCookie_str:
            if self.validateSessionCookie(userIdCookie_str):
                self.redirect('/homepage')
        template_values = self.createTemplate_values(errors,fields)
        self.render(template,**template_values)

    def getUserFromCookie(self):
        userIdCookie_str = self.request.cookies.get("userId")
        if userIdCookie_str:
            userId = self.validateSessionCookie(userIdCookie_str)
            if userId:
                return userModel.User.get_by_id(int(userId))




class FormHandler(BaseHandler):

    def validatePassword(self, password, hashedPass):
        passValid = utils.valid_hash(password,hashedPass)
        return passValid

    #this method takes a password and hashes it using hashing functions in the utils file.
    def hashPass(self, password):
        hashedPass = utils.make_hash(password)
        return hashedPass


#Called by post method of form. Checks if input submitted in fields is proper and applicable
#depends on validation functions in utils.py. If validation conditions needed to be adjusted, must edit validation functions
#in utils.py
    def validateFields(self):
        validation = {'valid': True}
        username = self.request.get('fields.username')
        password = self.request.get('fields.password')
        verifyPass = self.request.get('fields.verifyPass')
        email = self.request.get('fields.email')      
        fields = {'username':username,
                  'password':password,
                  'verifyPass':verifyPass,
                  'email':email}
        errors = {}
        validation['fields']=fields              
        
        if not utils.valid_username(username):
            validation['valid'] = False
            errors['error_username'] = "That's not a valid username"
            validation['errors'] = errors
            return validation  
    
        if not utils.valid_password(password):
            validation['valid'] = False
            errors['error_password'] = "That wasn't a valid password."
            validation['errors'] = errors
            return validation  

        elif verifyPass != password:
            validation['valid'] = False
            errors['error_verify'] = "Passwords do not match"
            validation['errors'] = errors
            return validation  

        if not utils.valid_email(email):
            validation['valid'] = False
            errors['error_email'] = "That's not a valid email."
            validation['errors'] = errors
            return validation  

            
        validation['errors'] = errors
        return validation  


    #Check Users function is the generic database confirmation that the fields provived correspond to a certain user.
    #Supposed to be called by the validate fields function and accepts the 'fields' mapping variable to check the database.
    #Returns the mapping 'userSearch' contain 'User' account Model object for password verification 
    def validateUser(self,fields,password):
        userSearch = {'userFound':False}
        email = fields['email']
        password = password
        allUsers = userModel.User.all()
        matchingUsers = allUsers.filter("email =", email)
        if matchingUsers.count() == 1:
            passHashed = matchingUsers.get().passHashed
            passValid = self.validatePassword(password,passHashed)
            userSearch = {'userFound':True,
                          'user':matchingUsers.get(),
                          'userId': matchingUsers.get().key().id()}
        return userSearch




class FrontPageHandler(BaseHandler):
    def get(self):
        self.renderStart("/templates/index.html")


class LoginHandler(FormHandler):
    #ovewriting default validation method to check if login information is an actual account
    #still need to check database on this.
    def validateFields(self):
        validation = {'valid': True}
        email = self.request.get('fields.email')
        password = self.request.get('fields.password')      
        fields = {'email' : email}
        errors = {}
        validation['fields'] = fields              
                      
        if not utils.valid_email(email):
            errors['error_email'] = "That's not a valid email."
            validation['valid'] = False
            validation['errors'] = errors
            return validation    
            

        if not utils.valid_password(password):
            errors['error_password'] = "That wasn't a valid password."
            validation['valid'] = False
            validation['errors'] = errors
            return validation    

        user = self.validateUser(fields,password)
        if not user['userFound']:
            errors['error_db'] = "Invalid email/password"
            validation['valid'] = False
            validation['errors'] = errors
            return validation


        validation['errors'] = errors
        validation['fields']['userId'] = user['userId']
        return validation 

    def get(self):
        self.renderStart("/templates/login.html")


    def post(self):
        validation = self.validateFields()
        if validation['valid'] == False:
            template_values = self.createTemplate_values(validation['errors'], validation['fields'])
            self.render("/templates/login.html", **template_values)
        else:
            self.createSessionCookie(validation['fields']['userId'])
            self.redirect('/')

class LogoutHandler(FormHandler):

    def get(self):
        self.response.headers.add_header("Set-Cookie", "userId =; Path = /")
        self.redirect('/')




class RegisterHandler(FormHandler):

#Ovewrites validateUser in form handler to check if email or username is currently used already in the database
#if either email or username are taken,returns a mapping with user found true and the which match was made.
    def validateUser(self,fields):
        email = fields['email']
        allUsers = userModel.User.all()
        matchingUsers = allUsers.filter("email =", email)
        if matchingUsers.count() == 1:
            userSearch = {'userFound':True,
                          'user':matchingUsers.get()}
        else:
            userSearch = {'userFound':False}
        return userSearch        

#Ovewriting the validateFields method of formhandler to check database if this user is already registered
    def validateFields(self):
        validation = {'valid': True}
        username = self.request.get('fields.username')
        password = self.request.get('fields.password')
        verifyPass = self.request.get('fields.verifyPass')
        email = self.request.get('fields.email')      
        fields = {'username':username,
                  'password':password,
                  'verifyPass':verifyPass,
                  'email':email}
        errors = {}
        validation['fields']=fields              
        user  = self.validateUser(fields)
        if  user['userFound']:
            validation['valid'] = False
            errors['error_email'] = "This email is already registered"
            validation['errors'] = errors
            return validation


        if not utils.valid_email(email):
            validation['valid'] = False
            errors['error_email'] = "That's not a valid email."
            validation['errors'] = errors
            return validation  
 

        if not utils.valid_username(username):
            validation['valid'] = False
            errors['error_username'] = "That's not a valid username"
            validation['errors'] = errors
            return validation  
    
        if not utils.valid_password(password):
            validation['valid'] = False
            errors['error_password'] = "That wasn't a valid password."
            validation['errors'] = errors
            return validation  

        elif verifyPass != password:
            validation['valid'] = False
            errors['error_verify'] = "Passwords do not match"
            validation['errors'] = errors
            return validation  

            
        validation['errors'] = errors
        return validation  

    def get(self):
        self.renderStart("/templates/register.html")

    def post(self):

        validation = self.validateFields()
        if validation['valid'] == False:
            template_values = self.createTemplate_values(validation['errors'], validation['fields'])
            self.render("/templates/register.html",**template_values)
        else:
            userId = self.registerUser(validation['fields'])
            self.createSessionCookie(userId)
            self.redirect('/homepage')

    #def registerUser(self,fields):
    def registerUser(self,fields):
        email = fields['email']
        username = fields['username']
        password = fields['password']
        passHashed = self.hashPass(password)
        newUser = userModel.User(email=email, username=username, passHashed=passHashed)
        newUser.put()
        userId = newUser.key().id()
        return  userId


app = webapp2.WSGIApplication([('/', FrontPageHandler),
                                ('/login', LoginHandler),
                                ('/logout',LogoutHandler),
                                ('/register', RegisterHandler)
                                ], debug=True)

