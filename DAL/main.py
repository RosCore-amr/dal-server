from utils.pattern import Singleton
from utils.threadpool import Worker
from .RCS.processing_handle import ProcessHandle
from utils.vntime import VnTimestamp, VnDateTime
from .RCS.config import MissionStatus

from flask import Flask
from typing import List, Dict
from time import sleep
import requests

GATEWAY_SLEEP_ALLOW_SECOND = 90


class DALServer(metaclass=Singleton):
    """
    A singleton handle DAL logic
    """

    def __init__(self, app: Flask, token_key: str, db_cfg: dict, rcs_cfg: dict):
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
        self.__rack_on_use = []
        self.__token_value = token_key
        self.__db_cfg = db_cfg
        self.__url_db = self.__db_cfg["url"]
        self.__callbox_info = self.__db_cfg["callbox_info"]
        self.__mission_info = self.__db_cfg["mission_info"]
        self.__query_status_task = self.__rcs_cfg["query_status"]
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
            mission_list = self.get_mission_info(MissionStatus.DONE, 20)
            if not mission_list:
                pass

            sleep(30)

    def get_mission_info(self, type_mission, number):
        list_task_rcs = []
        request_body = {"filter": {"current_state": type_mission}, "limit": number}
        try:
            res = requests.post(
                self.__url_db + self.__mission_info,
                headers=self.__token_value,
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

            return response["data"]
        except Exception as e:
            return None

    def get_token_key(self):
        return self.__token_value

    def get_db_cfg(self):
        return self.__db_cfg

    def trigger_mission(self, data: dict):
        trigger_handle = ProcessHandle(
            self.__app,
            data,
            self.__rcs_cfg,
            self.__token_value,
            self.__db_cfg,
            self.__rack_on_use,
        )
