from app.rest_api import *
from app.rest_api.user.apis import API_Authentication

class API_Setting(ApiCommon):
    urls = ("/configs", )

    def __init__(self):
        super().__init__(DB_Setting, disable=["add", "delete"])

class API_Callbox(ApiCommon):
    urls = ("/callboxes", )

    def __init__(self):
        super().__init__(DB_Callbox)
    
    @ApiBase.exception_error
    @jwt_required()
    @API_Authentication.adminRequire
    def get(self):
        return super().get()
    
    @ApiBase.exception_error
    @jwt_required()
    @API_Authentication.adminRequire
    def post(self):
        return super().post()
    
    @ApiBase.exception_error
    @jwt_required()
    @API_Authentication.adminRequire
    def patch(self):
        return super().patch()
    
    @ApiBase.exception_error
    @jwt_required()
    @API_Authentication.adminRequire
    def delete(self):
        return super().delete()