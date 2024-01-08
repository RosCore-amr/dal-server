from utils.pattern import Custom_Enum
from utils.vntime import VnDateTime
from app.rest_api import ApiBase
from DAL.main import DALServer
import requests

from typing import Type, List
from flask_babel import _


class TRIGGER_TYPE(Custom_Enum):
    CONFIRM = "confirm"
    SIGN = "sign"
    PRIOR = "prior"


class API_TriggerTask(ApiBase):
    urls = ("/trigger",)

    def __init__(self) -> None:
        self.__dal = DALServer()
        self.db_cfg = self.__dal.get_db_cfg()

        # Config
        self.__url_db = self.db_cfg["url"]
        self.__callbox = self.db_cfg["callbox"]
        self.__action_callbox = self.db_cfg["action"]

        return super().__init__()

    @ApiBase.exception_error
    def post(self):
        """
        ```
        data: {
            "gateway_id": str
            "plc_id": str
            "timestamp": integer
            "tasks": [{
                "button_id": integer
                "action": integer
            }]
        }
        ```
        """
        args = ["gateway_id", "plc_id", "timestamp", "tasks"]
        data = self.jsonParser(args, args)
        self.__token_value = self.__dal.get_token_key()
        print("data button 1", data)
        request_body = data
        try:
            res = requests.patch(
                self.__url_db + self.__action_callbox,
                headers=self.__token_value,
                json=request_body,
                timeout=6,
            )
            reponse = res.json()
            # print("reponse api getway ", reponse)
            # mission_task = self.__dal.trigger_mission(reponse)
        except Exception as e:
            print("erroor 404")
        return ApiBase.createResponseMessage()
