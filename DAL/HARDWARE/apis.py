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


class CallBox_TriggerTask(ApiBase):
    urls = ("/trigger",)

    def __init__(self) -> None:
        self.__dal = DALServer()
        self.db_cfg = self.__dal.get_db_cfg()
        self.__token_value = self.__dal.get_token_bearer()

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
        data_ = self.jsonParser(args, args)
        mission_info_ = self.get_mission(data_)
        # print("mission_info_", mission_info_)
        self.__dal.trigger_mission(data_, mission_info_)
        return ApiBase.createResponseMessage({})

    def get_mission(self, data_request_):
        request_body = data_request_
        try:
            res = requests.patch(
                self.__url_db + self.__action_callbox,
                headers=self.__token_value,
                json=request_body,
                timeout=6,
            )
            reponse = res.json()
            return reponse
        except Exception as e:
            print("erroor 404")


class PDA_TriggerTask(ApiBase):
    urls = ("/pda/trigger",)

    def __init__(self) -> None:
        self.__dal = DALServer()
        self.db_cfg = self.__dal.get_db_cfg()
        self.__token_value = self.__dal.get_token_bearer()

        # Config
        self.__url_db = self.db_cfg["url"]
        self.__callbox_info = self.db_cfg["callbox_info"]
        self.__action_callbox = self.db_cfg["action"]
        return super().__init__()

    @ApiBase.exception_error
    def post(self):
        """
        ```
        request: {
            "location": str
            "sectors": int
            "status": int
        }

        ```
        """
        args = ["location", "sectors", "status", "user"]
        data = self.jsonParser(args, args)
        pda_info_ = self.get_pda(data)
        print("pda_info_", pda_info_)
        # print("data", data)
        if pda_info_ is not None:
            request_pda = {
                "gateway_id": pda_info_["metaData"][0]["gateway_id"],
                "plc_id": pda_info_["metaData"][0]["plc_id"],
                "object_call": "PDA_{}".format(data["user"]),
                "tasks": [
                    {
                        "button_id": pda_info_["metaData"][0]["deviceId"],
                        "action": data["status"],
                    }
                ],
            }
            mission_info_ = self.get_mission(request_pda)
            self.__dal.trigger_mission(request_pda, mission_info_)
            return ApiBase.createResponseMessage({})

    def get_pda(self, data_request_):
        request_body = {
            "limit": 1,
            "filter": {
                "location": data_request_["location"],
                "sectors": data_request_["sectors"],
            },
        }

        try:
            res = requests.post(
                self.__url_db + self.__callbox_info,
                headers=self.__token_value,
                json=request_body,
                timeout=6,
            )
            reponse = res.json()
            # print("pda", reponse)
            return reponse
        except Exception as e:
            print("erroor 404")

    def get_mission(self, request_body):
        try:
            res = requests.patch(
                self.__url_db + self.__action_callbox,
                headers=self.__token_value,
                json=request_body,
                timeout=6,
            )
            reponse = res.json()
            # print("reponse", reponse)
            return reponse
        except Exception as e:
            print("erroor 404")
