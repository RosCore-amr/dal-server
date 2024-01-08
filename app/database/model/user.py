from utils.pattern import Custom_Enum
from app.database import *

from sqlalchemy.orm import validates
from datetime import timedelta
from passlib.hash import pbkdf2_sha256 as sha256
import re

class USER_ROLE(Custom_Enum):
    ADMIN       = "Admin"
    OPERATOR    = "Operator"

class CFG_EXPIRE(object):
    ACCESS      = timedelta(days=30)
    REFRESH     = timedelta(days=90)

class DB_User(db.Model, DbBaseModel):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False, default=None)
    __password = Column("password", String(255), nullable=False)
    name = Column(String(255), unique=True, nullable=False, default=None)
    position = Column(String(255), comment='in company')
    email = Column(String(255))
    phone = Column(String(20))
    language = Column(String(3), default = "vi")
    role = Column(
        String(100),
        comment=f"{USER_ROLE.list()}",
        default=USER_ROLE.OPERATOR.value)
    created_at = Column(DateTime(True), default=func.now())
    changed_at = Column(DateTime(True), default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(True), default=None)

    @validates('email')
    def validateEmail(self, key, address: str):
        assert '@' in address, (2020, "Địa chỉ email phải có dấu @", 409)
        return address
    
    @validates('phone')
    def validatePhone(self, key, phone: str):
        assert len(phone) >= 9 and phone.isdigit(),\
            (2020, "Số điện thoại không đúng", 409)
        return phone
    
    @property
    def password(self):
        return self.__password

    @password.setter
    def password(self, password: str):
        """
        Hash password before set
        """
        self.__password = sha256.hash(password)

    @staticmethod
    def validatePassword(password: str):
        """
        Validate password format
        """
        if len(password) < 8:
            return 'Chiều dài kí tự phải lớn hơn 8'
        
        if not any(char.isupper() for char in password):
            return 'Mật khẩu phải có ít nhất 1 kí tự viết hoa'
        
        if not any(char.islower() for char in password):
            return 'Mật khẩu phải có ít nhất 1 kí tự viết hoa'
        
        if not any(char.isdigit() for char in password):
            return 'Mất khẩu phải có ít nhất 1 kí chữ số'
        
        special_characters = re.compile('[@_!#$%^&*()<>?/\|}{~:]')
        if not special_characters.search(password):
            return 'Mất khẩu phải có ít nhất 1 kí tự đặc biệt $@#'
        
        return "Valid"

    def verifyPassword(self, password):
        """verify password for user

        Args:
            password (String): string input

        Returns:
            True/False: correct password
        """
        return sha256.verify(password, self.password)

class DB_RevokedToken(db.Model, DbBaseModel):
    __tablename__ = "revoked_token"
    jti = Column(String(500), primary_key=True, nullable=False)