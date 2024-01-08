from utils.logger import Logger
from utils.threadpool import ThreadPool

import paho.mqtt.client as mqtt, weakref
from time import sleep
from typing import Callable, Type
from abc import ABC, abstractclassmethod

class MqttMessage(ABC):
    """
    Mqtt message class format
    """
    def __init__(self, topic: str):
        self.topic = topic

    @abstractclassmethod
    def createMessage(self) -> str:
        """
        Combine all properties to form a json string message
        """
        pass

class Mqtt_Client:
    """
    Create connection to mqtt broker to publish message to server
    """
    def __init__(self, id: str, broker: str, port: int = 1883, user: str = None, password: str = None) -> None:
        # Create mqtt client
        self.__id = id
        self.__user = user
        self.__password = password

        # Set init value
        self.__createClient()
        self.__topics = {}
        self.__callbacks = {}
        self.__callback = None
        self.__broker = broker
        self.__port = port
        self.is_connected = False
        self.__need_connect = True
        self.__logger = Logger()
    
    def __createClient(self):
        self.__client = mqtt.Client(self.__id)
        if self.__user != None and self.__password != None:
            self.__client.username_pw_set(self.__user, self.__password)
        self.__client.on_connect = self.__onConnect
        self.__client.on_message = self.__onReceive

    def startConnection(self, reconnect_interval: float = 3):
        """
        Start connection loop, call once only
        """
        weak_self = weakref.ref(self)
        ThreadPool().add_task(Mqtt_Client.__connect, weak_self, reconnect_interval)

    @staticmethod
    def __connect(weak_self: Type["Mqtt_Client"], reconnect_interval: float):
        """
        Will try to connect forever, need new thread
        """
        while True:
            # Get self from weak ref
            self = weak_self()
            if not self:
                break
            
            # Try to reconnect if necessary
            if self.__client and not self.__client.is_connected():
                self.is_connected = False
            if not self.is_connected and self.__need_connect:
                if not self.__client:
                    self.__createClient()
                else:
                    self.__client.loop_stop()
                    self.__client.disconnect()

                try:
                    self.__client.connect(self.__broker, self.__port)
                    self.__client.loop_start()
                    self.__resubscribe()
                    self.is_connected = True
                except Exception as e:
                    self.__logger.error(e)

            # Let object removeable
            self = None
            sleep(reconnect_interval)

    def __del__(self):
        self.__logger.info(f"{self.__id} is deleted")
        
    def __onConnect(self, client, userdata, flags, rc):
        self.is_connected = True

    def waitConnection(self, debug_text: str = "") -> None:
        """
        Block until connection is setup
        """
        while not self.is_connected:
            if debug_text != "":
                self.__logger.info(debug_text)
            sleep(0.5)

    def disconnect(self) -> None:
        """
        Disconnection from broker, remove client and subscriptions.
        Must call to delete object
        """
        self.__need_connect = False
        self.is_connected = False
        self.__client.loop_stop()
        self.__client.disconnect()
        self.__client = None
        self.__topics = {}
        self.__callbacks = {}
        self.__callback = None

    def reconnect(self):
        """
        Trigger to connect to broker again, no need to restart connection loop
        """
        self.__need_connect = True
    
    def publish(self, message: MqttMessage, qos: int = 0) -> int:
        """
        qos = mqtt qos
            0 - atmost 1
            1 - atleast 1
            2 - only 1
        Return -> Status:
            0 - Success
            -1 - Publish failed
            -2 - Disconnected
        """
        if not self.is_connected:
            return -2
        
        topic = message.topic
        msg = message.createMessage()
        try:
            res_info = self.__client.publish(topic, msg, qos=qos)
            res_info.wait_for_publish(2)
            return 0
        except Exception as e:
            self.__logger.error(e)
            return -1
    
    def setCommonCallback(self, func: Callable):
        """
        Callback for topics that are not implemented custom callback
        Format: func(client_id: str, topic: str, message: str)
        """
        self.__callback = func
    
    def subscribe(self, topic: str, qos: int = 0, callback: Callable = None):
        """
        :callback: callback(client_id: str, topic: str, message: str)
        """
        self.__topics[topic] = qos
        self.__callbacks[topic] = callback
    
    def __resubscribe(self):
        """
        After disconnecting from server, sub topics are lost
        """
        for topic in self.__topics:
            self.__client.subscribe(topic, qos=self.__topics[topic])

    def unsubscribe(self, topic: str):
        """
        Unsubscribe unnecessary topic
        """
        self.__topics.pop(topic)
        self.__client.unsubscribe(topic)
        self.__callbacks.pop(topic)
    
    def __onReceive(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        topic = msg.topic
        message = msg.payload.decode()

        if topic in self.__callbacks and self.__callbacks[topic]:
            self.__callbacks[topic](self.__id, topic, message)
        elif self.__callback:
            self.__callback(self.__id, topic, message)