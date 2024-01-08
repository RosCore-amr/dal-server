from utils.export_excel import ImportExportExcel
from utils.vntime import VnDateTime
from app.rest_api import *
from app.database.model.user import CFG_EXPIRE, USER_ROLE

from flask_babel import _
from flask import send_file
from flask_jwt_extended import create_access_token, create_refresh_token

class API_Authentication(ApiBase):
    @staticmethod
    def getCurrentUser() -> DB_User:
        user_id = get_jwt_identity()
        return DB_User.findById(user_id)
    
    @classmethod
    def adminRequire(cls, func: Callable):
        def inner(*args, **kwargs):
            current_user = cls.getCurrentUser()
            if not current_user or current_user.role != USER_ROLE.ADMIN.value:
                return ApiBase.createNoAuthority()
            
            return func(*args, **kwargs)
        return inner

class API_User(ApiCommon):
    urls = ("/users", "/users/export")

    def __init__(self):
        """
        Only admin can handle user database
        """
        super().__init__(DB_User)
        self.model_type : DB_User

    @ApiCommon.exception_error
    @jwt_required()
    @API_Authentication.adminRequire
    def get(self):
        if '/export' not in request.path:
            return super().get()
        
        user_datas = self.model_type.find().all()
        
        for user in user_datas:
            user.created_at = VnTimestamp.toString(user.created_at)
            if user.changed_at:
                user.changed_at = VnTimestamp.toString(user.changed_at)
            if user.last_login:
                user.last_login = VnTimestamp.toString(user.last_login)
        
        excel_buffer = ImportExportExcel.export_excel(
            self.model_type.toJson(user_datas)
        )
        return send_file(excel_buffer, download_name='user_log.xlsx', as_attachment=True)

    @ApiCommon.exception_error
    @jwt_required()
    @API_Authentication.adminRequire
    def post(self):
        """
        Add new user
        """
        data = self.jsonParser(["password", "username", "name"])
        if not data["username"]:
            return self.createInvalid(f"Không được để trống tên tài khoản")
        if not data["name"]:
            return self.createInvalid(f"Không được để trống tên người dùng")

        user = self.model_type.find(username=data["username"]).first()
        if user:
            return self.createConflict(f"Tài khoản {data['username']} đã tồn tại")

        result = self.model_type.validatePassword(data["password"])
        if result != "Valid":
            return self.createInvalid(result)
        
        self.model_type.addByDict(data)
        return self.createResponseMessage(
            None, f"Tạo tài khoản {data['username']} thành công")
    
    @ApiCommon.exception_error
    @jwt_required()
    @API_Authentication.adminRequire
    def patch(self):
        """
        Update user by id
        """
        data = self.jsonParser(["id"])
        current_id = get_jwt_identity()
        current_user = self.model_type.findById(current_id)

        if "username" in data:
            if current_id == data["id"] and \
                    data["username"] != current_user.username:
                return self.createInvalid(f"Tài khoản đang được sử dụng")
            
            user = self.model_type.find(username=data["username"]).first()
            if user and user.id != data["id"]:
                return self.createConflict(f"Tên đăng nhập {data['username']} đã tồn tại")
        
        if "password" in data:
            if current_id == data["id"] and \
                    data["password"] != current_user.password:
                return self.createInvalid(f"Tài khoản đang được sử dụng")
            
            result = self.model_type.validatePassword(data["password"])
            if result != "Valid":
                return self.createInvalid(result)
        
        result = self.model_type.updateByDict(data, id=data["id"])
        if result != 0:
            return self.createConflict(_("User %(id)s not found", id=data["id"]))
        
        user_data = self.model_type.toJson(
            self.model_type.findById(data["id"])
        )
        return self.createResponseMessage(user_data, "Cập nhật thành công")
    
    @ApiCommon.exception_error
    @jwt_required()
    @API_Authentication.adminRequire
    def delete(self):
        return super().delete()

class API_Login(ApiBase):
    urls = ("/login", )
    
    @ApiBase.exception_error
    def post(self):
        data = self.jsonParser(["username", "password"])

        login_user : DB_User = DB_User.find(username=data["username"]).first()
        if not login_user:
            return self.createConflict("Sai tài khoản")
        
        if not login_user.verifyPassword(data["password"]):
            return self.createConflict("Sai mật khẩu")
        
        access_token = create_access_token(
            identity = login_user.id, expires_delta=CFG_EXPIRE.ACCESS)
        refresh_token = create_refresh_token(
            identity = login_user.id, expires_delta=CFG_EXPIRE.REFRESH)
        
        login_user_dict = DB_User.toJson(login_user)
        login_user.last_login = VnDateTime.now()
        DB_User.addObject(login_user)

        login_user_dict.update({
            'access_token': access_token,
            'refresh_token': refresh_token
        })
        return self.createResponseMessage(login_user_dict, _('Logged in as %(name)s', name=data["username"]))

class API_Logout(ApiBase):
    urls = ("/logout", )

    @ApiBase.exception_error
    @jwt_required()
    def post(self):
        jti = get_jwt()['jti']
        token = DB_RevokedToken(jti=jti)
        DB_RevokedToken.addObject(token)
        return self.createResponseMessage(
            {}, _('Access token has been revoked'))

class API_ChangePassword(ApiBase):
    urls = ("/change_password", )

    @ApiBase.exception_error
    @jwt_required()
    def patch(self):
        """
        Change current user password
        """
        data = self.jsonParser(["old_password", "new_password"])
        
        # Check old password
        user_db = API_Authentication.getCurrentUser()
        if not user_db.verifyPassword(data["old_password"]):
            return self.createConflict(_("Wrong passowrd"))
        
        # Check new password
        result = DB_User.validatePassword(data["new_password"])
        if result != "Valid":
            return self.createResponseMessage(data, result)

        # Change password
        user_db.password = data["new_password"]
        DB_User.addObject(user_db)
        return self.createResponseMessage(None, "Đổi mật khẩu thành công")

class API_RefreshToken(ApiBase):
    urls = ("/refresh_token", )

    @ApiBase.exception_error
    @jwt_required(refresh=True)
    def post(self):
        user_id = get_jwt_identity()
        access_token = create_access_token(
            identity = user_id, expires_delta=CFG_EXPIRE.ACCESS)
        return self.createResponseMessage({
            'access_token': access_token
        })