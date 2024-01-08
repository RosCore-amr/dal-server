from utils.export_excel import ImportExportExcel
from app.rest_api import *

from flask import send_file
from flask_babel import _
from typing import List

class API_Mission(ApiCommon):
    urls = ("/missions", "/missions/export")

    def __init__(self):
        super().__init__(DB_Mission, disable=["post", "patch", "delete"])

    @ApiCommon.exception_error
    @jwt_required()
    def get(self):
        if '/export' not in request.path:
            return super().get()

        # Get mission data
        missions = self.model_type.find().all()
        if not missions:
            return ApiBase.createConflict(_("No mission created"))

        # Get task data
        task_datas = []
        for mission in missions:
            tasks = DB_Task.find(mission_id=mission.id).all()
            if not tasks:
                continue
            
            for task in tasks:
                task_datas.append({
                    "#": task.id,
                    "Nhiệm vụ": mission.name,
                    "Mã chuyền": task.line_id,
                    "Tên chuyền": task.line_name,
                    "Tầng": mission.floor,
                    "Vị trí kệ": mission.rack_id,
                    "Agv": mission.robot_id,
                    "Loại hàng": task.product_type,
                    "Ưu tiên": "Ưu tiên" if task.prior else "Thường",
                    "Thời gian đăng ký": VnTimestamp.toString(task.created_at),
                    "Thời gian thực hiện": VnTimestamp.toString(task.start_at),
                    "Thời gian kết thúc": VnTimestamp.toString(task.stop_at)
                })
        if not task_datas:
            return ApiBase.createConflict(_("No task created"))

        # Export excel
        excel_buffer = ImportExportExcel.export_excel(task_datas)
        return send_file(excel_buffer, download_name='task_log.xlsx', as_attachment=True)

class API_Task(ApiCommon):
    urls = ("/tasks", )

    def __init__(self):
        super().__init__(DB_Task, disable=["post", "patch", "delete"])

    @ApiCommon.exception_error
    @jwt_required()
    def get(self):
        mission_id = self.jsonParser(["mission_id"])["mission_id"]
        tasks = self.model_type.toJson(
            self.model_type.find(mission_id=mission_id).all()
        )
        return ApiBase.createResponseMessage(tasks)

class API_Error(ApiCommon):
    urls = ("/errors", )

    def __init__(self):
        super().__init__(DB_Error, disable=["post", "patch", "delete"])