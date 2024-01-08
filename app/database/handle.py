from app.database import *

class DatabaseHandle:
    def __init__(self):
        self.callbox = DB_Callbox
        self.mission = DB_Mission
        self.task = DB_Task
        self.setting = DB_Setting
        self.error = DB_Error
        self.user = DB_User