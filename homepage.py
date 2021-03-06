import webapp2
import jinja2
import os
import re
import hashlib
import hmac
import string
import utils
import main
from models import userModel
from models import taskModel
from google.appengine.ext import db


#Initializes templating features of Jinja2 framework
template_dir = os.path.join(os.path.dirname(__file__))
jinja_environment = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)
SortMethod ="dateCreated"

class BaseTaskHandler(main.BaseHandler):
    def getTasks(self, userId):
        tasksQuery = taskModel.Task.all()
        tasksQuery = tasksQuery.ancestor(taskModel.taskAncestorKey(userId))
        tasksQuery = tasksQuery.order(SortMethod)
        return tasksQuery

class HomePageHandler(BaseTaskHandler):
    def renderStart(self,template, errors = {}, fields = {}):
        template_values = self.createTemplate_values(errors,fields)
        self.render(template,**template_values)
        
    def get(self):
        user = self.getUserFromCookie()
        userId = user.key().id()
        userTasks = self.getTasks(userId)
        fields = {"user":user,
                  "userTasks":userTasks,
                  "sortMethod": SortMethod
                  }
        self.renderStart("/templates/homepage.html",fields=fields)

    def fixDueDate(self,dueDate):
        split1 = dueDate.partition('-')
        year = split1[0]
        split2 = split1[2].partition('-')
        month  = split2[0]
        day  = split2[2]
        if year.isdigit() and month.isdigit() and day.isdigit():
            fixedDate = month+'/'+day+'/'+year
            return fixedDate
        else:
            return None



class NewTaskHandler(HomePageHandler):
    def get(self):
        self.renderStart("/templates/newtask.html")

    def post(self):
        title = self.request.get("title")
        description = self.request.get("description")
        dueDate = self.request.get("dueDate")
        fixedDueDate = self.fixDueDate(dueDate)
        priority = self.request.get("priority")
        user = self.getUserFromCookie()
        userId = user.key().id()
        newTask = taskModel.Task(title = title,description = description, dueDate = dueDate, fixedDueDate = fixedDueDate, priority = priority,
                                 userId = userId, parent=taskModel.taskAncestorKey(userId))
        newTask.put()
        self.redirect('/homepage')                  





class DeleteTaskHandler(HomePageHandler):
    def post(self):
        taskKey = self.request.get("k")
        task = db.get(taskKey)
        task.delete()
        self.redirect('/homepage')

class TaskPageHandler(HomePageHandler):
    def get(self,taskId):
        user = self.getUserFromCookie()
        userId= user.key().id()
        task = taskModel.Task.get_by_id(int(taskId), parent = taskModel.taskAncestorKey(userId))    
        fields = {'user': user,'userTask':task}
        self.renderStart('templates/task.html',fields=fields)

class EditTaskHandler(HomePageHandler):
    def post(self):
        taskKey = self.request.get("k")
        task = db.get(taskKey)
        user = self.getUserFromCookie()
        userId= user.key().id()
        fields = {'user': user,'userTask':task}
        self.renderStart('templates/edittask.html',fields=fields)

class UpdateTaskHandler(HomePageHandler):
    def post(self):
        taskKey = self.request.get("k")
        task = db.get(taskKey)
        task.title = self.request.get("title")
        task.description = self.request.get("description")
        task.dueDate = self.request.get("dueDate")
        task.fixedDueDate = self.fixDueDate(task.dueDate)
        task.priority = self.request.get("priority")
        task.put()
        self.redirect('/homepage')

class SortTasksHandler(HomePageHandler):
    def get(self,sortFunct_str):
        sortFunct = sortFunct_str.partition('-')
        if sortFunct[0] == "duedate":
            sortby = "dueDate"
        else:
            sortby = "priority"
        if(sortFunct[2]!="asc"):
            sortby = "-"+sortby
        global SortMethod
        SortMethod = sortby
        self.redirect('/homepage')




app = webapp2.WSGIApplication([('/homepage',HomePageHandler),
                                ('/homepage/newtask',NewTaskHandler),
                                ('/homepage/deltask',DeleteTaskHandler),
                                ('/homepage/task/(\d+)',TaskPageHandler),
                                ('/homepage/edittask',EditTaskHandler),
                                ('/homepage/updatetask',UpdateTaskHandler),
                                ('/homepage/sort/((?:priority|duedate)-(?:asc|dsc))', SortTasksHandler)
                                ], debug=True)