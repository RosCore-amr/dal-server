"""
TODO: Import active url resources here
"""
from ..rest_api import api

from .setting.apis import API_Setting, API_Callbox

api.addClassResource(API_Setting)
api.addClassResource(API_Callbox)

from .log.apis import API_Mission, API_Task, API_Error

api.addClassResource(API_Mission)
api.addClassResource(API_Task)
api.addClassResource(API_Error)

from .user.apis import (
    API_User,
    API_Login,
    API_Logout,
    API_ChangePassword,
    API_RefreshToken,
)

api.addClassResource(API_User)
api.addClassResource(API_Login)
api.addClassResource(API_Logout)
api.addClassResource(API_ChangePassword)
api.addClassResource(API_RefreshToken)

from DAL.RCS.apis import API_RCSCallback
from DAL.HARDWARE.apis import CallBox_TriggerTask, PDA_TriggerTask

api.addClassResource(API_RCSCallback)
api.addClassResource(CallBox_TriggerTask)
api.addClassResource(PDA_TriggerTask)
