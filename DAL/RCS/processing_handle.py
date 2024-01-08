from utils.threadpool import Worker
from utils.vntime import VnTimestamp, VnDateTime
from utils.logger import Logger
from app.database.handle import DatabaseHandle
from app.database.model.history import (
    DB_Mission,
    MISSION_STATUS,
    TASK_STATUS,
    ERROR_MODULE,
)
from app.database.model.setting import PRODUCT_TYPE
from .config import RCS_TASK_CODE, RCS_PRIOR_CODE
from .config import MainState, TaskStatus, SignalCallbox, MissionStatus

from flask import Flask
import requests

# from time import sleep
import time
from typing import List


class ProcessHandle:
    def __init__(
        self,
        app: Flask,
        misssion: DB_Mission,
        cfg: dict,
        token_key: str,
        db_cfg: dict,
        rack_on_use: list,
    ) -> None:
        """
        :app: (Flask) handle session to communicate with database
        :mission_id: (int) mission_id
        :database: (DatabaseHandle) database class container
        :cfg: (dict)
            "type"      : "RCS",
            "url"       : "http://172.10.10.10:5000/rcms/services/rest/hikRpcService",
            "task"      : "/genAgvScheduleTask",
            "query"     : "/queryPodBerthAndMat",
            "continue"  : "/continueTask",
            "stop"      : "/stopRobot",
            "resume"    : "/resumeRobot"
        """
        # Config
        self.__url = cfg["url"]
        self.__task_path = cfg["task"]
        self.__storage_path = cfg["query"]
        self.__stop_path = cfg["stop"]
        self.__resume_path = cfg["resume"]
        self.__continue_path = cfg["continue"]
        self.__task_cancel = cfg["cancel"]
        self.__storage_area = cfg["storage_area_code"]
        self.__rack_prefix = cfg["pod_code_prefix"]
        self.__query_status_task = cfg["query_status"]
        self.__app = app
        self.__rack_on_use = rack_on_use
        self.__mission = misssion
        self.__mission_name = self.__mission["mission_code"]

        # Init flags
        self.__agv = ""
        self.__confirm_line_id = ""
        self.__rcs_callback_task_id = ""
        self.rcs_task_id = ""
        self.line_to_confirm = ""
        self.__token_value = token_key
        self.__db_cfg = db_cfg
        self.__url_db = self.__db_cfg["url"]
        self.__mission_history = self.__db_cfg["mission_change"]
        self.__mission_info = self.__db_cfg["mission_info"]
        self.__count = 0
        self._cancel_status = False

        self.mainLoop()

    # Normal mission thread
    @Worker.employ
    def mainLoop(self):
        """
        Mission loop, call async once.
        * Call RCS api
        * Wait for rcs feedback and confirm signal from callboxes
        * Update database
        """
        _state = MainState.INIT
        _prev_state = MainState.NONE

        while _state != MainState.NONE:
            if _state != _prev_state:
                print(
                    "STATE {}: {} -> {}".format(
                        self.__mission["mission_code"], _prev_state.name, _state.name
                    )
                )
                _prev_state = _state
            self.missioncheck()

            if self._cancel_status:
                _state = MainState.PROCESS_CANCEL

            if _state == MainState.INIT:
                if (
                    self.__mission["code"] == SignalCallbox.SIGN_ERROR
                    or self.__mission["code"] == SignalCallbox.CANCEL_ERROR
                ):
                    print("msg: ", self.__mission["msg"])
                    _state = MainState.NONE

                if self.__mission["code"] == SignalCallbox.SIGN_SUCCESS:
                    _state = MainState.CREATE_TASK
                if self.__mission["code"] == SignalCallbox.CANCEL_SUCCESS:
                    _state = MainState.CANCEL
            elif _state == MainState.CREATE_TASK:
                _path = [
                    self.__mission["pickup_location"],
                    self.__mission["return_location"],
                ]
                task_code_ = self.sendTask(_path, RCS_TASK_CODE.UPSTAIR, False)
                # print("task code", task_code_)
                if task_code_ is not None:
                    print("task_code_", task_code_)
                    self.updateTaskMission(self.__mission_name, task_code_)
                    _state = MainState.WAIT_PROCESS
            elif _state == MainState.WAIT_PROCESS:
                # _processing_task = self.queryTaskStatus(task_code_)
                # print("_processing_task", _processing_task)
                # Wait for agv id
                if not self.__agv:
                    continue
                if not self.updateStatusMission(
                    self.__mission_name, MissionStatus.PROCESS
                ):
                    _state = MainState.PROCESSING

            elif _state == MainState.PROCESSING:
                _processing_task = self.queryTaskStatus(task_code_)
                if not _processing_task:
                    _state = MainState.DONE
                # if _processing_task["taskStatus"] == TaskStatus.COMPLETE :
                # if not self._cancel_status:
                #     _state = MainState.DONE
                # else:
                #     _state = MainState.CANCEL
                # _state = MainState.DONE
            elif _state == MainState.DONE:
                time.sleep(3)
                if not self.updateStatusMission(
                    self.__mission_name, MissionStatus.DONE
                ):
                    _state = MainState.NONE

            elif _state == MainState.CANCEL:
                if not self.updateStatusMission(
                    self.__mission_name, MissionStatus.CANCEL
                ):
                    _state = MainState.NONE
            elif _state == MainState.PROCESS_CANCEL:
                _state = MainState.NONE
        print("=========================================================")

    def missioncheck(self):
        response = self.checkMissionDB(self.__mission["mission_code"])
        self.__agv = response["metaData"][0]["robot_code"]
        mission_rcs = response["metaData"][0]["mission_rcs"]
        # if not mission_rcs:
        mission_status = response["metaData"][0]["current_state"]
        if mission_status == MissionStatus.CANCEL:
            self._cancel_status = True

    def checkMissionDB(self, misson_code_):
        request_body = {"filter": {"mission_code": misson_code_}}
        try:
            res = requests.post(
                self.__url_db + self.__mission_info,
                headers=self.__token_value,
                json=request_body,
                timeout=6,
            )
            response = res.json()
            return response
        except Exception as e:
            print("error check mission")
            return None

    def updateStatusMission(self, misson_code_, status_):
        request_body = {
            "filter": {"mission_code": misson_code_},
            "current_state": status_,
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
            print("error update status mission")

    def updateTaskMission(self, misson_code_, task_rcs_):
        # request_body = {"mission_code": misson_code_, "mission_rcs": task_rcs_}
        request_body = {
            "filter": {"mission_code": misson_code_},
            "mission_rcs": task_rcs_,
        }
        try:
            res = requests.patch(
                self.__url_db + self.__mission_history,
                headers=self.__token_value,
                json=request_body,
                timeout=6,
            )
            response = res.json()
        except Exception as e:
            print("error update task mission")

    def queryTaskStatus(self, task_code_):
        request_body = {
            "reqCode": self.__getRequestCode("query_Task"),
            "taskCodes": task_code_,
        }
        try:
            res = requests.post(
                self.__url + self.__query_status_task, json=request_body, timeout=3
            )
            response = res.json()
            if not response:
                # self.logError("Send task failed with no response",
                #               Request=request_body, Status=res.status_code)
                return None
            if response["code"] != "0" or response["data"][0]["taskCode"] != task_code_:
                # self.logError("Send task failed",
                #               Request=request_body,
                #               Response=response["message"])
                return None
            return response["data"][0]["taskStatus"]
        except Exception as e:
            return None

    def cancelTask(self, task_code_, matter_area_) -> str:
        request_body = {
            "reqCode": self.__getRequestCode("cancel"),
            "forceCancel": "1",
            "matterArea": matter_area_,
            "taskCode": task_code_,
        }
        try:
            res = requests.post(
                self.__url + self.__task_cancel, json=request_body, timeout=3
            )
            response = res.json()
            if not response:
                # self.logError("Send task failed with no response",
                #               Request=request_body, Status=res.status_code)
                return None
            if response["code"] != "0":
                # self.logError("Send task failed",
                #               Request=request_body,
                #               Response=response["message"])
                return None

            return response["reqCode"]
        except Exception as e:
            return None

    def sendTask(self, position_codes_: List[str], task_code_: str, prior: bool) -> str:
        """
        Send agv task to RCS

        Input:
        :start_pos: postion code (1F0 -> 3F35)
        :stop_pos: position code (1F0 -> 3F35)
        :prior: int

        Response:
        ```
        {
            "code": error_code (0-normal),
            "message": error description,
            "data": task_id,
            "reqCode": (as request)
        }
        ```

        Return:
        * None if failed
        * Task id if succeeded
        """
        path_codes = []
        for code in position_codes_:
            path_codes.append({"positionCode": code, "type": "00"})
        request_body = {
            "reqCode": self.__getRequestCode("task"),
            "taskTyp": task_code_,
            "positionCodePath": path_codes,
            "podCode": "",
            "podDir": "",
            "priority": RCS_PRIOR_CODE.PRIOR if prior else RCS_PRIOR_CODE.NORMAL,
            "agvCode": "self.__agv",
        }
        # print("task ", self.__url + self.__task_path)
        try:
            res = requests.post(
                self.__url + self.__task_path, json=request_body, timeout=3
            )
            response = res.json()
            # print("response", response)
            if not response:
                # self.logError("Send task failed with no response",
                #               Request=request_body, Status=res.status_code)
                return None
            if response["code"] != "0":
                # self.logError("Send task failed",
                #               Request=request_body,
                #               Response=response["message"])
                return None

            return response["data"]

        except Exception as e:
            # self.logError(str(e), Request=request_body)
            return None

    def __getRequestCode(self, api_name: str):
        """
        Generate identical request code for rcs api
        """
        return f"iot-{api_name}-{self.__mission_name}-{int(VnTimestamp.now())}"

    def onRcsCallback(self, rcs_task_id: str, agv_code: str):
        """
        Receive stop task callback from agv
        """
        if not self.__agv:
            self.__agv = agv_code
        self.__rcs_callback_task_id = rcs_task_id
