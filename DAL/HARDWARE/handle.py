from iot_config import CFG_MQTT_TOPIC
from utils.mqtt import MqttMessage
from utils.pattern import Singleton

from flask import Flask
from flask_mqtt import Mqtt, MQTT_ERR_SUCCESS, MQTT_ERR_NO_CONN
import paho.mqtt.client as mqtt_client
import paho.mqtt.client as mqtt
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

        # print("mqtt")

        # Subscribe on connect
        @self.on_connect()
        def onConnect(client, userdata, flags, rc):
            print("MQTT ready")
            self.subscribe(CFG_MQTT_TOPIC.ERROR)
            self.subscribe(CFG_MQTT_TOPIC.UPTIME)

        # Trigger function on receive message
        @self.on_message()
        def onMessage(
            client: mqtt_client.Client, userdata, msg: mqtt_client.MQTTMessage
        ):
            topic = msg.topic
            message = msg.payload.decode()
            # print("message", message)
            if topic == CFG_MQTT_TOPIC.ERROR:
                self.__onError(message)
            elif topic == CFG_MQTT_TOPIC.UPTIME:
                self.__onUptime(message)

        app.config["MQTT_BROKER_URL"] = mqtt_cfg["host"]
        app.config["MQTT_BROKER_PORT"] = mqtt_cfg["port"]
        app.config["MQTT_USERNAME"] = mqtt_cfg["user"]
        app.config["MQTT_PASSWORD"] = mqtt_cfg["pass"]
        app.config["MQTT_KEEPALIVE"] = 5  # seconds
        app.config["MQTT_TLS_ENABLED"] = False
        while not self.connected:
            try:
                self.init_app(app)
            except Exception as e:
                # Logger().error(f"[{ERROR_MODULE.BROKER}] {e}")
                pass
            sleep(3)

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
        # request_body = uptime_msg
        device_ = {
            "1": uptime_msg["button1"],
            "2": uptime_msg["button2"],
            "3": uptime_msg["button3"],
            "4": uptime_msg["button4"],
        }
        request_body = []
        # print("num_device ", num_device)
        for key, val in device_.items():
            if val == 1:
                device_ = {
                    "gateway_id": uptime_msg["gateway_id"],
                    "plc_id": uptime_msg["deviceId"].split("_")[1],
                    "deviceId": key,
                }
                request_body.append(device_)
        # print("config", request_body)
        try:
            res = requests.patch(
                self.__url_db + self.__status,
                headers=self.__token_value,
                json=request_body,
                timeout=6,
            )
            reponse = res.json()

            # print("updata status ", reponse)
        except Exception as e:
            print("error status DB")
