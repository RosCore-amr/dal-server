from utils.pattern import Singleton
from utils.threadpool import Worker
from utils.vntime import VnTimestamp
from app.database.handle import DatabaseHandle
from app.database.model.history import DB_Task, DB_Mission, MISSION_STATUS
from app.database.model.setting import DB_Callbox

# from .RCS.handle import MissionHandle, MISSION_PROCESS
from .RCS.processing_handle import ProcessHandle

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

        # self.checkGateway()
        # self.checkMission()

    # # Support method
    # def resolveUndoneTask(self):
    #     """
    #     Continue to do undone tasks from the last session
    #     """
    #     with self.__app.app_context():
    #         missions : List[DB_Mission] = self.__db.mission.find(
    #             status=MISSION_STATUS.PROCESS.value
    #         ).all()
    #         for mission in missions:
    #             self.__rcs[mission.id] = MissionHandle(
    #                 self.__app, mission, self.__db, self.__rcs_cfg, self.__rack_on_use)

    # Minor thread

    @Worker.employ
    def checkMission(self):
        """
        * If mission enough, create handler
        * If mission done, pop
        """
        # self.resolveUndoneTask()
        print("DAL ready")

        # request_body = {
        #     "reqCode": f"iot-query-bin",
        #     "areaCode": "self.__storage_area"
        # }
        # try:
        #     res = requests.post(self.__url_db , headers= self.__token_value, json=request_body, timeout= 6)
        #     reponse = res.json()
        #     # print("reponse" , reponse)
        # except Exception as e :
        #     print("erroor 404")

        while True:
            # with self.__app.app_context():
            #     missions: List[DB_Mission] = self.__db.mission.find(
            #         status=MISSION_STATUS.ENOUGH.value
            #     ).all()
            #     for mission in missions:
            #         if mission.id not in self.__rcs:
            #             self.__rcs[mission.id] = MissionHandle(
            #                 self.__app,
            #                 mission,
            #                 self.__db,
            #                 self.__rcs_cfg,
            #                 self.__rack_on_use,
            #             )

            # mission_ids = list(self.__rcs.keys())
            # for mission_id in mission_ids:
            #     if self.__rcs[mission_id].process == MISSION_PROCESS.DONE:
            #         self.__rcs.pop(mission_id)
            sleep(3)

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
