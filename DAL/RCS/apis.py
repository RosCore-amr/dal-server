from app.rest_api import ApiBase
from DAL.RCS.config import CFG_RCS_PATH
from DAL.main import DALServer
from flask_babel import _


class API_RCSCallback(ApiBase):
    urls = ("/agv",)

    def __init__(self) -> None:
        self.__dal = DALServer()
        return super().__init__()

    # @ApiBase.exception_error
    def post(self):
        """
        ```
        data: {
            "method": str
            "agv": str
            "taskCode": str
        }
        ```
        """
        args = ["method", "robotCode", "taskCode"]
        data = self.jsonParser(args, args)
        self.__dal.onRcsCallback(data)
        print("data call", data)

        return ApiBase.createResponseMessage({})
