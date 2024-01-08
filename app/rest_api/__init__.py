"""
Deploy all rest apis for the Flask application

Everytables is assumed to have ```id``` column in it
"""

from app.database import *
from app.database.handle import DatabaseHandle
from app.database.model.user import USER_ROLE
from utils.logger import Logger

from flask_restful import Api, Resource, request, reqparse
from flask_babel import _
from flask_jwt_extended import  jwt_required, get_jwt, get_jwt_identity
from flask_jwt_extended.exceptions import RevokedTokenError
from typing import Callable

class ApiBase(Resource):
    urls = ()

    def requestParser(self, args: list, required_args: list):
        """
        Parser data from request

        Return -> Namespace (dict)
        """
        if not request.data:
            return {}
        
        parser = reqparse.RequestParser()
        for arg in args:
            if arg in required_args:
                parser.add_argument(arg, help = _('This field cannot be blank'), required = True)
            else:
                parser.add_argument(arg, required = False)
        data = parser.parse_args()
        return data
    
    @staticmethod
    def limitDict(data: dict, *args) -> dict:
        """
        Return -> dict only contain args
        """
        new_data = {}
        for arg in args:
            if arg in data:
                new_data[arg] = data[arg]
        return new_data
    
    @staticmethod
    def checkRequirement(data: dict, *args) -> list:
        """
        Check if data contains all required args

        Return -> list of missing args
        """
        missing_args = []
        for arg in args:
            if arg not in data:
                missing_args.append(arg)
        return missing_args

    def __checkJson(self, data: dict, required_args: list):
        """
        Validate Json data by required arguments,
        add messages to 'response_message'

        Returns: response_message
        """
        if type(data) != dict:
            data = {}

        response_message = []
        for arg in self.checkRequirement(data, *required_args):
            response_message.append(arg)
        return response_message

    def jsonParser(self, required_args: list = (), limit_args: list = ()):
        """
        Parser Json data from request body and param

        Returns -> (json) data
        """
        data = {}
        if request.args:
            data.update(request.args.to_dict())
        if request.data:
            data.update(request.get_json(force=True))

        missing_args = self.checkRequirement(data, *required_args)
        response_message = []
        for arg in missing_args:
            response_message.append(f"Không được để trống {arg}")
        assert not response_message, (2020, response_message, 409)
        
        if limit_args:
            data = self.limitDict(data, *limit_args)
            
        return data
    
    @staticmethod
    def createResponseMessage(data: object, message: str = "Succeeded", response_code: int = 200, error_code: int = 0):
        """
        Return response for rest request
        ```
        {
            "code": int(error_code, 0-no error)
            "msg": str(message)
            "response": object(data)
        }, response_code
        ```
        """
        response = ({
            'code': error_code,
            'msg': message,
            'response': data
        }, response_code)
        return response
    
    @staticmethod
    def createNotImplement():
        """
        Return "Not implemented" response for rest request
        ```
        {
            "code": 2018
            "msg": "Not implemented"
            "response": {}
        }, 501
        ```
        """
        return ApiBase.createResponseMessage(None, _("Not implemented"), 501, 2018)

    @staticmethod
    def createNoAuthority():
        """
        Return "No authority" response for rest request
        ```
        {
            "code": 2021
            "msg": "No authority"
            "response": {}
        }, 401
        ```
        """
        return ApiBase.createResponseMessage(None, _("No authority"), 401, 2021)

    @staticmethod
    def createConflict(msg: str):
        """
        Return "Data conflict" response for rest request
        ```
        {
            "code": 2022
            "msg": (str) description
            "response": {}
        }, 409
        ```
        """
        return ApiBase.createResponseMessage(None, msg, 409, 2022)

    @staticmethod
    def createInvalid(msg: str):
        """
        Return "Request invalid" response for rest request
        ```
        {
            "code": 2023
            "msg": (str) description
            "response": {}
        }, 409
        ```
        """
        return ApiBase.createResponseMessage(None, msg, 409, 2023)

    @staticmethod
    def createServerFailure(msg: str):
        """
        Return "Server failure" response for rest request
        ```
        {
            "code": 2024
            "msg": (str) description
            "response": {}
        }, 500
        ```
        """
        return ApiBase.createResponseMessage(None, msg, 500, 2024)

    @classmethod
    def exception_error(cls, func):
        """
            DECORATOR FOR TRY AND EXCEPTION ERROR
        """
        def inner(cls):
            msg = _("An error occurred")
            code = 2019
            res_code = 503
            try:
                return func(cls)
            except AssertionError as e:
                code, msg, res_code = eval(str(e))
            except IntegrityError as e:
                code, msg = e.orig.args
            except DataError as e:
                code, msg = e.orig.args
            except InvalidRequestError as e:
                msg = str(e)
            except RevokedTokenError as e:
                msg = str(e)
            except Exception as e:
                msg += f": {e}"
            
            Logger().error(msg)
            return ApiBase.createResponseMessage({}, msg, res_code, code)
            
        return inner

class ApiCommon(ApiBase):
    """
    API BASE included : GET, POST, PATCH, DELETE
    """
    def __init__(self, model_type: Type["DbBaseModel"], disable: list = []):
        """
        :disable: Not allow some api
            ["get", "post", "patch", "delete"]
        """
        self.model_type = model_type
        self.disable = disable

    @ApiBase.exception_error
    @jwt_required()
    def get(self):
        """
        GET: With normal filter
        Some extra filter: column, order, sort, time, pagination
        * column: get list value without duplication of a column
        * order: reorder the records follow some rules
        * time: sort by time duration
        * pagination: (as the name)

        Request param:
        ```
        {
            <property>: <value> | (list) values,
            ... ,
            "columnFilt": (list) column names,
            "orderFilt": (list) column names,
            "timeFilt": <column_name>,<start>,<stop>
            "pagination": <skip>,<limit>
        }
        ```
        With:
            "name": (str) timestamp column name,
            "start": (str) start date-time,
            "stop": (str) stop date-time,
            "skip": (int) order number of page (starting at 1),
            "limit": (int) number of records in 1 page

        Response:
        ```
        "code": (int),
        "msg": (str),
        "response": {
            "data": (list) records,
            "total": (int) number of records,
            "page": {
                "skip": (int) order number of current page (starting at 1),
                "limit": (int) number of records in 1 page
            }
        } response_code
        ```
        """
        if "get" in self.disable:
            return ApiBase.createNotImplement()

        # Validate request body
        filters : dict = self.jsonParser()
        
        # Query by request body
        response_data = self.createFilteredResponse(filters)
        return ApiBase.createResponseMessage(response_data)
    
    def createGetResponse(self, records: object, skip: int, limit: int):
        """
        ```
        {
            "data": (str) records in json,
            "total": (int) number of records,
            "page": {
                "skip": (int) order number of current page (starting at 1),
                "limit": (int) number of records in 1 page
            }
        }
        ```
        """
        return {
            "data": self.model_type.toJson(records),
            "total": self.model_type.getTotal(),
            "page": {
                "skip": skip,
                "limit": limit
            }
        }

    def createFilteredResponse(self, filters: dict):
        """
        Create response with filtered data
        """
        # Extract extra filter
        extra_filter = {}
        if "columnFilt" in filters:
            extra_filter.update({
                "column": filters.pop("columnFilt").split(",")
            })
        if "orderFilt" in filters:
            extra_filter.update({
                "order": filters.pop("orderFilt").split(",")
            })
        if "timeFilt" in filters:
            time_filter = filters.pop("timeFilt").split(",")
            extra_filter.update({
                "time": [{
                    "name": time_filter[0],
                    "start": float(time_filter[1]),
                    "stop": float(time_filter[2]),
                }]
            })
        if "pagination" in filters:
            pagination = list(map(int, filters.pop("pagination").split(",")))
            extra_filter.update({
                "pagination": {
                    "skip": pagination[0],
                    "limit": pagination[1]
                }
            })

        # Apply normal filter
        query = self.model_type.find()
        query = self.model_type.normalFilter(query, filters)

        # Apply extra filter
        skip = 1
        limit = 100
        column_names = []
        if extra_filter:
            if "column" in extra_filter:
                query, column_names =\
                    self.model_type.columnFilter(query, extra_filter["column"])
            if "order" in extra_filter:
                query = self.model_type.orderFilter(query, extra_filter["order"])
            if "time" in extra_filter:
                query = self.model_type.durationFilter(query, extra_filter["time"])
            if "pagination" in extra_filter:
                pagination : dict = extra_filter["pagination"]
                if "skip" in pagination:
                    skip = pagination["skip"]
                if "limit" in pagination:
                    limit = pagination["limit"]
        data = self.model_type.pagination(query, skip, limit).all()

        # Fix data for column filter
        if column_names:
            data_len = data.__len__()
            for i in range(data_len):
                data[i] = {column_names[j]: data[i][j] for j in range(column_names.__len__())}
        return self.createGetResponse(data, skip, limit)
        
    @ApiBase.exception_error
    @jwt_required()
    def post(self):
        """
        POST: If id in request body, id must not exist
        """
        if "post" in self.disable:
            return ApiBase.createNotImplement()

        data : dict = self.jsonParser()
        self.model_type.addByDict(data)
        return ApiBase.createResponseMessage(data, "Thêm thành công")
    
    @ApiBase.exception_error
    @jwt_required()
    def patch(self):
        """
        PATCH: Update one record only by id
        """
        if "patch" in self.disable:
            return ApiBase.createNotImplement()

        data : dict = self.jsonParser(["id"])

        result = self.model_type.updateByDict(data, id=data["id"])
        if result != 0:
            return ApiBase.createConflict(
                _("%(table)s id %(id)d not found",
                  table=self.model_type.__tablename__,
                  id=data["id"]))
        
        data = self.model_type.toJson(
            self.model_type.findById(data["id"])
        )
        return ApiBase.createResponseMessage(data, "Cập nhật thành công")

    @ApiBase.exception_error
    @jwt_required()
    def delete(self):
        """
        DELETE: Delete some records by list of ids
        """
        if "delete" in self.disable:
            return ApiBase.createNotImplement()

        ids = self.jsonParser(["id"]).pop("id")
        if type(ids) != list:
            ids = [ids]

        result = self.model_type.delete(self.model_type.id.in_(ids))
        if not result:
            return ApiBase.createConflict(
                _("%(table)s id not found in %(ids)s",
                  table=self.model_type.__tablename__,
                  ids=ids))
        
        return ApiBase.createResponseMessage(result, "Xoá thành công")

class ApiFeConfigure(ApiBase):
    """
    Base API for configuring FE UI

    Implement:
    * GET: getFilter, getPost, getPatch, getTable, getExcel
    * POST: setFilter, setPost, setPatch, setTable
    """
    def getFilter(self):
        """
        Get config of filter UI
        """
        return _("Not implemented")

    def getPost(self):
        """
        Get config of add new UI
        """
        return _("Not implemented")

    def getPatch(self):
        """
        Get config of update UI
        """
        return _("Not implemented")

    def getTable(self):
        """
        Get config of table UI
        """
        return _("Not implemented")

    def getExcel(self):
        """
        Get all tables in a excel file
        """
        return _("Not implemented")

    def setFilter(self):
        """
        Set filter UI config
        """
        return _("Not implemented")

    def setPost(self):
        """
        Set add new UI config
        """
        return _("Not implemented")

    def setPatch(self):
        """
        Set update UI config
        """
        return _("Not implemented")

    def setTable(self):
        """
        Set table UI config
        """
        return _("Not implemented")

    def get(self):
        """
        Redirect to other get functions
        """
        if '/filter' in request.path:
            data =  self.getFilter()
        elif '/post' in request.path:
            data =  self.getPost()
        elif '/patch' in request.path:
            data =  self.getPatch()
        elif '/table' in request.path: 
            data =  self.getTable()
        elif '/export' in request.path: 
            data =  self.getExcel()
        else:
            return ApiBase.createResponseMessage(_("Wrong path '{request.path}'"), 404)
        return data

    def post(self):
        """
        Redirect to other set functions
        """
        response_code = 200
        if '/filter' in request.path:
            response_message = self.setFilter()
        elif '/post' in request.path:
            response_message = self.setPost()
        elif '/patch' in request.path:
            response_message = self.setPatch()
        elif '/table' in request.path:
            response_message = self.setTable()
        else:
            response_message = _(f"Wrong path '{request.path}'")
            response_code = 404
        return ApiBase.createResponseMessage(response_message, response_code)

class CustomApi(Api):
    def addClassResource(self, api_class: Type["ApiBase"]):
        self.add_resource(api_class, *api_class.urls)
api = CustomApi()

from .import_all import *