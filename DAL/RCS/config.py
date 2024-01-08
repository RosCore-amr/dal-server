class CFG_RCS_PATH(object):
    CALLBACK    = "/agv/callback"
    
class RCS_TASK_CODE:
    """
    UPSTAIR:    From storage to elevator, to 1st line
    ON_FLOOR:   From line to line
    DOWNSTAIR:  From last line to scanner, to storage
    """
    UPSTAIR     = "F081"
    ON_FLOOR    = "F01"
    DOWNSTAIR   = "F011"

class RCS_PRIOR_CODE:
    """
    NORMAL:     For normal task
    PRIOR:      For prior task
    """
    NORMAL      = 1
    PRIOR       = 127