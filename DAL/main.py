from utils.pattern import Singleton
from utils.threadpool import Worker
from .RCS.processing_handle import ProcessHandle
from utils.vntime import VnTimestamp, VnDateTime
from .RCS.config import MissionStatus, TaskStatus, MainState
from flask import Flask
from typing import List, Dict
from time import sleep
import requests

GATEWAY_SLEEP_ALLOW_SECOND = 90


class DALServer(metaclass=Singleton):
    """
    A singleton handle DAL logic
    """

    def __init__(
        self,
        app: Flask,
        token_bearer: str,
        token_base64: str,
        gw_cfg: dict,
        db_cfg: dict,
        rcs_cfg: dict,
        server_cfg: dict,
    ):
        """
        rcs_cfg:
            "type"      : "RCS",
            "url"       : "http://172.10.10.10:5000/rcms/services/rest/hikRpcService",
            "task"      : "/genAgvScheduleTask",
            "query"     : "/queryPodBerthAndMat",
            "continue"  : "/continueTask",
            "stop"      : "/stopRobot",
            "resume"    : "/resumeRobot"
        """
        self.__app = app
        # self.__db = db_handle
        # self.__rcs: Dict[str, MissionHandle] = {}
        self.__rcs_cfg = rcs_cfg
        self.__gw_cfg = gw_cfg
        self.__rack_on_use = []
        self.__token_db = token_bearer
        self.__token_gw = token_base64
        self.__db_cfg = db_cfg
        self.__server_cfg = server_cfg
        self.__url_db = self.__db_cfg["url"]
        self.__callbox_info = self.__db_cfg["callbox_info"]
        self.__mission_info = self.__db_cfg["mission_info"]
        self.__query_status_task = self.__rcs_cfg["query_status"]
        self.__mission_history = self.__db_cfg["mission_change"]
        self.__list_task = self.__rcs_cfg["mockup_list"]

        self.__url_rcs = self.__rcs_cfg["url"]
        # print("self.__db_cfg", self.__rcs_cfg)

        self.checkMission()

    @Worker.employ
    def checkMission(self):
        """
        * If mission enough, create handler
        * If mission done, pop
        """
        while True:
            mission_list = self.get_mission_info(MissionStatus.PENDING, 20)
            if not mission_list:
                pass
            else:
                query = self.query_task_status(mission_list)
                # print("query", query)
                # for i in range(0, len(query) + 1):
                #     print("i", query[0]["taskCode"])
                self.process_task_rcs(query["taskCode"], query["taskStatus"])

            sleep(10)

    def process_task_rcs(self, misson_code_, status_rcs_):
        print("misson_code_", misson_code_)
        mission_status_ = MissionStatus.PENDING
        if status_rcs_ == TaskStatus.COMPLETE:
            mission_status_ = MissionStatus.DONE
        elif status_rcs_ == TaskStatus.EXECUTING:
            mission_status_ = MissionStatus.PROCESS
        else:
            mission_status_ = MissionStatus.CANCEL
        print("mission_status_", mission_status_)
        self.updateStatusMission(misson_code_, mission_status_)

    def get_mission_info(self, type_mission, number):
        list_task_rcs = []
        request_body = {"filter": {"current_state": type_mission}, "limit": number}
        try:
            res = requests.post(
                self.__url_db + self.__mission_info,
                headers=self.__token_db,
                json=request_body,
                timeout=6,
            )
            response = res.json()
            for index in range(0, len(response["metaData"])):
                list_task_rcs.append(response["metaData"][0]["mission_rcs"])
            return list_task_rcs
        except Exception as e:
            return None

    def query_task_status(self, list_task):
        request_body = {
            "reqCode": int(VnTimestamp.now()),
            "taskCodes": list_task,
        }
        try:
            res = requests.post(
                self.__url_rcs + self.__list_task, json=request_body, timeout=3
            )
            response = res.json()
            if not response:
                return None
            # print("response", response)
            return response["data"]
        except Exception as e:
            return None

    def updateStatusMission(self, misson_code_, status_):
        request_body = {
            "filter": {"mission_code": misson_code_},
            "current_state": status_,
        }
        # print("request_body this ", request_body)
        try:
            res = requests.patch(
                self.__url_db + self.__mission_history,
                headers=self.__token_db,
                json=request_body,
                timeout=6,
            )
            response = res.json()
            if response["code"] != "0":
                return None
            # print("reponse updateStatusMission", response)
            return response["code"]
        except Exception as e:
            print("error update status mission")

    def get_token_bearer(self):
        return self.__token_db

    def get_db_cfg(self):
        return self.__db_cfg

    def get_server_cfg(self):
        return self.__server_cfg

    def trigger_mission(self, object_call_: dict, mission_info: dict):
        # print("mission_info", mission_info)
        trigger_handle = ProcessHandle(
            self.__app,
            object_call_,
            mission_info,
            self.__server_cfg,
            self.__rcs_cfg,
            self.__token_db,
            self.__token_gw,
            self.__gw_cfg,
            self.__db_cfg,
            self.__rack_on_use,
        )
