#! /usr/bin/env python
# -*- coding: utf-8 -*-

from utils.logger import Logger
from utils.threadpool import ThreadPool
from utils.storage import StorageH
from utils.vntime import VnDateTime
from app.database.handle import DatabaseHandle
from app.database.model.user import USER_ROLE
from DAL.main import DALServer
from DAL.gateway.handle import GatewayHandle
from DAL.gateway.apis import API_TriggerTask
from app import FlaskApp
import requests
import yaml
from yaml.loader import BaseLoader
from iot_config import THIS_PC_MAC_ID


import os
from time import sleep


class CallboxServer:
    def __init__(self, name, *args, **kwargs):
        self.init_variable(*args, **kwargs)
        # LICENSE
        import uuid

        if uuid.getnode() != THIS_PC_MAC_ID or self.token_key is None:
            exit(code=-1)

        ThreadPool(7)
        self.flask = FlaskApp()
        self.__dal = DALServer(
            self.flask.app,
            self.token_key,
            self.config["CFG_DB"],
            self.config["CFG_RCS"],
        )
        self.__gateway = GatewayHandle(
            self.flask.app,
            # self.__db,
            self.token_key,
            self.config["CFG_DB"],
            self.config["CFG_MQTT"],
        )

        # self.createAdmin()

    def init_variable(self, *args, **kwargs):
        config_file = kwargs["config_file"]
        self.logfile = kwargs["log_file"]
        self.config = self.load_config(config_file)
        self.token_key = self.get_token(self.config["CFG_DB"])
        log_path = os.path.join(
            self.logfile, "{:%Y-%m-%d}.log".format(VnDateTime.now())
        )
        if not os.path.isfile(log_path):
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w"):
                pass
        Logger("debug", False, True, log_path)

    def load_config(self, path):
        config = {}
        with open(path, "r") as stream:
            try:
                d = yaml.load(stream, Loader=yaml.FullLoader)
                for key, val in d.items():
                    config[key] = val
                return config
            except yaml.YAMLError as e:
                print(e)

    def get_token(self, cfg: dict):
        request_body = {"name": cfg["name"], "password": cfg["pass"]}
        try:
            res = requests.post(cfg["url"] + cfg["login"], json=request_body, timeout=3)
            response = res.json()
            token_request = {
                "Authorization": "Bearer {}".format(
                    response["metaData"]["access_token"]
                )
            }
            return token_request
        except Exception as e:
            pass

    def start(self):
        """
        Serve forever
        """
        while True:
            try:
                self.flask.start(self.config["CFG_SERVER"])
            except Exception as e:
                Logger().error(str(e))
            try:
                sleep(3)
            except KeyboardInterrupt:
                print("EXIT")
                return


def parse_opts():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option(
        "-d",
        "--ros_debug",
        action="store_true",
        dest="log_debug",
        default=False,
        help="log_level=rospy.DEBUG",
    )
    parser.add_option(
        "-c",
        "--config_file",
        dest="config_file",
        default=os.path.join(
            os.getcwd(),
            "config.yaml",
        ),
    )

    parser.add_option(
        "-l",
        "--log_file",
        dest="log_file",
        default=os.path.join(
            os.getcwd(),
            "logs",
        ),
    )

    (options, args) = parser.parse_args()
    print("Options:\n{}".format(options))
    print("Args:\n{}".format(args))
    return (options, args)


def main():
    (options, args) = parse_opts()
    log_level = None
    if options.log_debug:
        log_level = "rospy.DEBUG"
    describe = "call box processing "
    server = CallboxServer(describe, **vars(options))
    server.start()


if __name__ == "__main__":
    main()
