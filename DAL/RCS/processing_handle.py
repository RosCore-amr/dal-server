from utils.threadpool import Worker
from utils.vntime import VnTimestamp, VnDateTime
from utils.logger import Logger
from app.database.model.history import (
    DB_Mission,
    MISSION_STATUS,
    TASK_STATUS,
    ERROR_MODULE,
)
from app.database.model.setting import PRODUCT_TYPE
from .config import RCS_TASK_CODE, RCS_PRIOR_CODE
from .config import MainState, TaskStatus, SignalCallbox, MissionStatus, DeviceControl

# from DAL.main import DALServer
from flask import Flask
import requests

from time import sleep
from typing import List


class ProcessHandle:
    def __init__(
        self,
        app: Flask,
        object_call: dict,
        misssion: DB_Mission,
        server_cfg: dict,
        rcs_cfg: dict,
        token_bearer: str,
        token_base64: str,
        gw_cfg: dict,
        db_cfg: dict,
        rack_on_use: list,
    ) -> None:
        # RCS Config
        self.__url_rcs = rcs_cfg["url"]
        self.__task_path = rcs_cfg["task"]
        self.__storage_path = rcs_cfg["query"]
        self.__stop_path = rcs_cfg["stop"]
        self.__resume_path = rcs_cfg["resume"]
        self.__continue_path = rcs_cfg["continue"]
        self.__task_cancel = rcs_cfg["cancel"]
        self.__storage_area = rcs_cfg["storage_area_code"]
        self.__rack_prefix = rcs_cfg["pod_code_prefix"]
        self.__query_status_task = rcs_cfg["query_status"]

        # DB Config
        self.__url_db = db_cfg["url"]
        self.__mission_history = db_cfg["mission_change"]
        self.__mission_info = db_cfg["mission_info"]

        # Server Config
        self.__url_server = server_cfg["url"]
        self.__callbox = server_cfg["trigger_callbox"]

        # Getway Config
        self.__url_gw = gw_cfg["url"]
        self.__device_control = gw_cfg["device_control"]
        self.__device = object_call["tasks"][0]["button_id"]
        self.__device_call = str(
            object_call["gateway_id"] + "_" + object_call["plc_id"] + "/"
        )

        # Mission info
        self.__mission = misssion
        self.__mission_name = self.__mission["mission_code"]

        # Init
        self.__agv = ""
        self.__name_call = "None"
        self.__token_db = token_bearer
        self.__token_gw = token_base64
        self._cancel_programe = False
        self.__object_call = object_call
        self.rcs_task_id = ""
        self.line_to_confirm = ""
        # print("__device_call", self.__device_call)
        self.main()

    @Worker.employ
    def main(self):
        """
        Mission loop, call async once.
        * Call RCS api
        * Wait for rcs feedback and confirm signal from callboxes
        * Update database
        """
        _state = MainState.INIT
        _prev_state = MainState.NONE
        _processing_task = None
        _task_code = None

        while _state != MainState.NONE:
            if _state != _prev_state:
                print(
                    "Object call {} {}: {} -> {}".format(
                        self.__name_call,
                        self.__mission["mission_code"],
                        _prev_state.name,
                        _state.name,
                    )
                )
                _prev_state = _state

            mission_status = self.query_db_mission()
            if (
                mission_status == MissionStatus.CANCEL
                or mission_status == MissionStatus.DONE
            ):
                _state = MainState.FINISH
            # elif mission_status == MissionStatus.DONE:
            #     _state = MainState.DONE
            else:
                pass

            if _state == MainState.INIT:
                # if not self.control_device(DeviceControl.OFF):
                if self.__mission["mission_rcs"]:
                    _task_code = self.__mission["mission_rcs"]
                if self.__mission["code"] == SignalCallbox.SIGN_SUCCESS:
                    _state = MainState.CREATE_TASK
                elif self.__mission["code"] == SignalCallbox.CANCEL_SUCCESS:
                    _state = MainState.PROCESS_CANCEL
                elif self.__mission["code"] == SignalCallbox.SIGN_ERROR:
                    _state = MainState.TASK_REGISTER
                else:
                    print("msg: ", self.__mission["msg"])
                    _state = MainState.NONE

            elif _state == MainState.CREATE_TASK:
                _path = [
                    self.__mission["pickup_location"],
                    self.__mission["return_location"],
                ]
                _task_code = self.sendTask(_path, RCS_TASK_CODE.UPSTAIR, False)
                if _task_code is not None:
                    self.updateTaskMission(self.__mission_name, _task_code)
                    # self.query_rcs_mission(_task_code)
                    _state = MainState.WAIT_PROCESS
            # else:
            #     _state = MainState.CANCEL
            elif _state == MainState.TASK_REGISTER:
                if _task_code is None:
                    _state = MainState.REGISTER_AGAIN
                else:
                    _processing_task = self.queryTaskStatus(
                        _task_code, TaskStatus.CANCEL
                    )
                    # print("_processing_task", _processing_task)
                    if _processing_task != TaskStatus.EXECUTING:
                        # print("_processing_task", _processing_task)
                        _state = MainState.FINISH

            elif _state == MainState.REGISTER_AGAIN:
                if not self.updateStatusMission(
                    self.__mission_name, MissionStatus.CANCEL
                ):
                    self.call_box_again(self.__object_call)
                    _state = MainState.FINISH

            elif _state == MainState.WAIT_PROCESS:
                _processing_task = self.queryTaskStatus(
                    _task_code, TaskStatus.EXECUTING
                )
                # print("_processing_task", _processing_task)

                # Wait for agv id
                if _processing_task == TaskStatus.EXECUTING:
                    _state = MainState.PROCESSING

                if self.__agv:
                    _state = MainState.PROCESSING

            elif _state == MainState.PROCESSING:
                self.updateStatusMission(self.__mission_name, MissionStatus.PROCESS)
                _processing_task = self.queryTaskStatus(_task_code, TaskStatus.COMPLETE)
                sleep(4)
                # print("_processing_task", _processing_task)
                if _processing_task == TaskStatus.COMPLETE:
                    _state = MainState.DONE_PROCESS

            elif _state == MainState.DONE_PROCESS:
                if not self.updateStatusMission(
                    self.__mission_name, MissionStatus.DONE
                ):
                    _state = MainState.FINISH

            elif _state == MainState.PROCESS_CANCEL:
                if not _task_code:
                    if not self.updateStatusMission(
                        self.__mission_name, MissionStatus.CANCEL
                    ):
                        _state = MainState.FINISH
                else:
                    if (
                        self.cancelTask(
                            self.__mission["mission_rcs"],
                            self.__mission["pickup_location"],
                        )
                        is not None
                    ):
                        self.updateStatusMission(
                            self.__mission_name, MissionStatus.CANCEL
                        )
                        _state = MainState.FINISH

                    else:
                        self.updateStatusMission(
                            self.__mission_name, MissionStatus.PENDING
                        )
                        _state = MainState.FINISH

            # elif _state == MainState.CANCEL:
            #     self._cancel_programe = True
            #     self.control_device(DeviceControl.OFF)
            #     _state = MainState.NONE

            elif _state == MainState.FINISH:
                self._cancel_programe = True
                self.control_device(DeviceControl.OFF)
                _state = MainState.NONE

        print("=========================================================")

    @Worker.employ
    def query_rcs_mission(self, mision_rcs_):
        while not self._cancel_programe:
            reponse_rcs = self.queryTaskStatus(mision_rcs_, 100)
            self.updateStatusMission(
                self.__mission_name, self.missionConvertRcsToDB(reponse_rcs)
            )
            sleep(20)

    def missionConvertRcsToDB(self, rcs_status):
        # if rcs_status == TaskStatus.SENDING:
        #     return MissionStatus.PROCESS
        # elif rcs_status == TaskStatus.CANCEL:
        #     return MissionStatus.CANCEL
        # elif rcs_status == TaskStatus.COMPLETE:
        #     return MissionStatus.DONE
        # else:
        #     return MissionStatus.PENDING
        return MissionStatus.CANCEL

    def query_db_mission(self):
        response = self.missionDB(self.__mission["mission_code"])
        self.__agv = response["metaData"][0]["robot_code"]
        mission_rcs = response["metaData"][0]["mission_rcs"]
        self.__name_call = response["metaData"][0]["object_call"]
        mission_status = response["metaData"][0]["current_state"]
        return mission_status

    def missionDB(self, misson_code_):
        request_body = {"filter": {"mission_code": misson_code_}}
        try:
            res = requests.post(
                self.__url_db + self.__mission_info,
                headers=self.__token_db,
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

    def updateTaskMission(self, misson_code_, task_rcs_):
        # request_body = {"mission_code": misson_code_, "mission_rcs": task_rcs_}
        request_body = {
            "filter": {"mission_code": misson_code_},
            "mission_rcs": task_rcs_,
        }
        try:
            res = requests.patch(
                self.__url_db + self.__mission_history,
                headers=self.__token_db,
                json=request_body,
                timeout=6,
            )
            response = res.json()
        except Exception as e:
            print("error update task mission")

    def queryTaskStatus(self, task_code_, status):
        request_body = {
            "reqCode": self.__getRequestCode("query_Task"),
            "taskCodes": task_code_,
            "typeTask": status,
        }
        try:
            res = requests.post(
                self.__url_rcs + self.__query_status_task, json=request_body, timeout=3
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
            # print("response", response)
            return response["data"][0]["taskStatus"]
        except Exception as e:
            return None
        # return None

    def cancelTask(self, task_code_, matter_area_) -> str:
        request_body = {
            "reqCode": self.__getRequestCode("cancel"),
            "forceCancel": "1",
            "matterArea": matter_area_,
            "taskCode": task_code_,
        }
        try:
            res = requests.post(
                self.__url_rcs + self.__task_cancel, json=request_body, timeout=3
            )
            response = res.json()
            if not response:
                return None
            if response["code"] != "0":
                return None
            # print("response", response)
            return response
        except Exception as e:
            return None

    def call_box_again(self, callbox_info):
        request_body = callbox_info
        # print("request_body", request_body)
        try:
            res = requests.post(
                self.__url_server + self.__callbox, json=request_body, timeout=3
            )
            response = res.json()
            # print("call box", response)
            if response["code"] != "0":
                return None
            print("response call_box_again", response)
            return response
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
        # print("task ", self.__url_rcs + self.__task_path)
        try:
            res = requests.post(
                self.__url_rcs + self.__task_path, json=request_body, timeout=3
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

    def control_device(self, status):
        device_ = "fb{}".format(self.__device)
        request_body = {device_: status}
        try:
            res = requests.post(
                self.__url_gw + self.__device_control + self.__device_call,
                headers=self.__token_gw,
                json=request_body,
                timeout=4,
            )
            response = res.json()
            print("response", response)
            if not response:
                return None

            return response
        except Exception as e:
            return None

    def __getRequestCode(self, api_name: str):
        """
        Generate identical request code for rcs api
        """
        return f"iot-{api_name}-{self.__mission_name}-{int(VnTimestamp.now())}"
