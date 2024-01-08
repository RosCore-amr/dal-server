from utils.pattern import Custom_Enum
from app.database import *

class PRODUCT_TYPE(Custom_Enum):
    HEAVY = "Heavy"
    LIGHT = "Light"

class TASK_MODE(Custom_Enum):
    BUTTON  = "Button"
    WEB     = "Web"

class DB_Setting(db.Model, DbBaseModel):
    __tablename__ = 'setting'
    id = Column(Integer, primary_key=True, nullable=False)
    racks_number = Column(Integer, nullable=False)
    tasks_in_mission = Column(Integer, nullable=False)
    changed_at = Column(
        DateTime(True),
        default=func.now(),
        onupdate=func.now())

class DB_Callbox(db.Model, DbBaseModel):
    __tablename__ = 'callbox'
    id = Column(Integer, primary_key=True, nullable=False)
    gateway_id = Column(String(255), nullable=False)
    plc_id = Column(String(255), nullable=False)
    button_id = Column(String(255), nullable=False)
    name = Column(String(255), unique=True, nullable=False)
    line_id = Column(String(255), unique=True, nullable=False)
    line_name = Column(String(255), unique=True, nullable=False)
    floor = Column(String(100), nullable=False)
    connected = Column(Boolean, nullable=False, default=False)
    rcs_id = Column(String(255), comment='position id on RCS', nullable=False)
    product_type = Column(
        String(100),
        comment=f'{PRODUCT_TYPE.list()}',
        nullable=False,
        default=PRODUCT_TYPE.HEAVY.value)
    update_at = Column(DateTime(True), default=func.now(), onupdate=func.now())
    
    @classmethod
    def updateConnectStatus(cls, gateway_id: str, gateway_stt: bool,
                            plc_id: str = None, plc_stt: bool = True):
        """
        Update callboxes status by gateway (and plc) status
        """
        if plc_id != None:
            callboxes = cls.find(gateway_id=gateway_id, plc_id=plc_id).all()
        else:
            callboxes = cls.find(gateway_id=gateway_id).all()
        
        for callbox in callboxes:
            callbox.connected = gateway_stt and plc_stt
            cls.addObject(callbox)