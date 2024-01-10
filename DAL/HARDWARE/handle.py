from iot_config import CFG_MQTT_TOPIC
from utils.mqtt import MqttMessage
from utils.logger import Logger
from utils.pattern import Singleton
from app.database.handle import DatabaseHandle
from app.database.model.history import ERROR_MODULE

from flask import Flask
from flask_mqtt import Mqtt, MQTT_ERR_SUCCESS, MQTT_ERR_NO_CONN
import paho.mqtt.client as mqtt_client
from time import sleep
import requests
import json


class GatewaySyncMessage(MqttMessage):
    def __init__(self):
        super().__init__(CFG_MQTT_TOPIC.SYNC)
        self.id = 0
        self.type = "sync_machine"
        self.device_id = 0

    def setParam(self, id: int, device_id: int):
        self.id = id
        self.device_id = device_id

    def createMessage(self) -> str:
        msg = {"id": self.id, "type": self.type, "deviceId": self.device_id}
        return json.dumps(msg)


class GatewayHandle(Mqtt, metaclass=Singleton):
    def __init__(self, app: Flask, token: str, db_cfg: dict, mqtt_cfg: dict) -> None:
        """
        A singleton class to handle every gateway through mqtt
        * Read uptime message to update status in database
        * Read error message and response sync to gateway

        CFG_MQTT:
        * HOST        = '192.168.1.219'
        * USER        = 'rostek'
        * PASSWORD    = 'rostek2019'
        * PORT        = 1883
        """
        super().__init__()
        self.__app = app
        # self.__db = db_handle
        self.__token_value = token
        self.__db_cfg = db_cfg

        # Config
        self.__url_db = self.__db_cfg["url"]
        self.__callbox = self.__db_cfg["callbox"]
        self.__status = self.__db_cfg["status"]

        # Subscribe on connect
        @self.on_connect()
        def onConnect(client, userdata, flags, rc):
            # print("MQTT ready")
            self.subscribe(CFG_MQTT_TOPIC.ERROR)
            self.subscribe(CFG_MQTT_TOPIC.UPTIME)

        # Trigger function on receive message
        @self.on_message()
        def onMessage(
            client: mqtt_client.Client, userdata, msg: mqtt_client.MQTTMessage
        ):
            topic = msg.topic
            message = msg.payload.decode()
            # print("message mqtt" , message )
            # print("message" ,type(message))
            if topic == CFG_MQTT_TOPIC.ERROR:
                self.__onError(message)
            elif topic == CFG_MQTT_TOPIC.UPTIME:
                self.__onUptime(message)

    # Callback
    def __onError(self, message: str):
        pass

    def __sendSync(self, msg: GatewaySyncMessage) -> bool:
        pass

    def __onUptime(self, message: str):
        """
        On receive uptime message from gateway
        * Update gateway status in database

        Uptime message:
        {
            gateway_id (string): gateway serial number
            timestamp (int): utc time
            deviceId (string): <gateway_id>_<plc_id>
            plc_status (bool): plc connection
        }
        """
        # Read message
        uptime_msg = json.loads(message)
        request_body = uptime_msg
        # print("request_body ", request_body)
        # print("__token_value" , (self.__token_value))

        try:
            res = requests.patch(
                self.__url_db + self.__status,
                headers=self.__token_value,
                json=request_body,
                timeout=6,
            )
            reponse = res.json()

            # print("updata status " , reponse)
        except Exception as e:
            print("error status DB")
