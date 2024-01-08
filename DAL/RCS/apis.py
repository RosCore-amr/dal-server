from app.rest_api import ApiBase
from DAL.RCS.config import CFG_RCS_PATH
from DAL.main import DALServer
from flask_babel import _
import requests


class API_RCSCallback(ApiBase):
    urls = ("/agv",)

    def __init__(self) -> None:
        self.__dal = DALServer()
        self.__db_cfg = self.__dal.get_db_cfg()
        self.__token_value = self.__dal.get_token_key()

        # Config
        self.__url_db = self.__db_cfg["url"]
        self.__callbox = self.__db_cfg["callbox"]
        self.__action_callbox = self.__db_cfg["action"]
        self.__mission_history = self.__db_cfg["mission_change"]

        return super().__init__()

    # @ApiBase.exception_error
    def post(self):
        """
        ```
        data: {
            "method": str
            "robotCode": str
            "taskCode": str
        }
        ```
        """
        args = ["method", "robotCode", "taskCode"]
        data = self.jsonParser(args, args)
        if not self.update_agv(data["taskCode"], data["robotCode"]):
            return ApiBase.createResponseMessage({})

    def update_agv(self, mission_rcs, robotCode):
        request_body = {
            "filter": {"mission_rcs": mission_rcs},
            "robot_code": robotCode,
        }
        try:
            res = requests.patch(
                self.__url_db + self.__mission_history,
                headers=self.__token_value,
                json=request_body,
                timeout=6,
            )
            response = res.json()
            if response["code"] != "0":
                return None

            return response["code"]
        except Exception as e:
            print("error update AGV")
