from enum import Enum


class CFG_RCS_PATH(object):
    CALLBACK = "/agv/callback"


class RCS_TASK_CODE:
    """
    UPSTAIR:    From storage to elevator, to 1st line
    ON_FLOOR:   From line to line
    DOWNSTAIR:  From last line to scanner, to storage
    """

    UPSTAIR = "F081"
    ON_FLOOR = "F01"
    DOWNSTAIR = "F011"


class RCS_PRIOR_CODE:
    """
    NORMAL:     For normal task
    PRIOR:      For prior task
    """

    NORMAL = 1
    PRIOR = 127


class MainState(Enum):
    NONE = -1
    INIT = 0
    CREATE_TASK = 1
    WAIT_PROCESS = 2
    PROCESSING = 3
    CANCEL = 4
    PROCESS_CANCEL = 5
    DONE = 6


class TaskStatus:
    EXCEPTION = "0"
    CREATE = "1"
    EXECUTING = "2"
    SENDING = "3"
    CANCEL = "4"
    RESENDING = "6"
    COMPLETE = "9"


class SignalCallbox:
    NONE = 0
    SIGN_SUCCESS = 1
    SIGN_ERROR = 2
    CANCEL_SUCCESS = 3
    CANCEL_ERROR = 4


class MissionStatus:
    SIGN = "registered"
    PROCESS = "processing"
    CANCEL = "cancel"
    DONE = "accomplished"
