from utils.pattern import Custom_Enum
from app.database import *
from app.database.model.setting import DB_Callbox, PRODUCT_TYPE

class MISSION_STATUS(Custom_Enum):
    SIGN    = "Sign"
    ENOUGH  = "Enough"
    PROCESS = "Process"
    DONE    = "Done"

class TASK_STATUS(Custom_Enum):
    SIGN    = "Sign"
    PROCESS = "Process"
    DONE    = "Done"

class ERROR_MODULE(Custom_Enum):
    SERVER      = "Server"
    PLC         = "PLC"
    GATEWAY     = "Gateway"
    RCS         = "RCS"
    BROKER      = "Broker"
    DATABASE    = "MySQL"

class DB_Mission(db.Model, DbBaseModel):
    __tablename__ = 'mission'
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    robot_id = Column(String(255))
    rack_id = Column(String(255))
    floor = Column(String(100), nullable=False)
    prior = Column(Boolean, default=False, nullable=False)
    status = Column(
        String(100),
        comment=f'{MISSION_STATUS.list()}',
        nullable=False,
        default=MISSION_STATUS.SIGN.value)
    start_at = Column(DateTime(True))
    stop_at = Column(DateTime(True))
    _tasks = relationship("DB_Task", backref='_mission', cascade="all, delete-orphan")
    
    @classmethod
    def create(cls, floor: str) -> Type["DB_Mission"]:
        """
        Create new sign mission
        """
        last_mission_id = cls.getQuery(func.max(cls.id)).scalar()
        new_id = 1
        if last_mission_id:
            new_id += last_mission_id
        record = cls()
        record.id = new_id
        record.name = f"Mission-{new_id}"
        record.floor = floor
        record.status = MISSION_STATUS.SIGN.value
        cls.addObject(record)
        
        return cls.findById(record.id)

class DB_Task(db.Model, DbBaseModel):
    __tablename__ = 'task'
    id = Column(Integer, primary_key=True, nullable=False)
    mission_id = Column(Integer, ForeignKey('mission.id'), nullable=False)
    line_id = Column(String(255), nullable=False)
    line_name = Column(String(255), nullable=False)
    product_type = Column(
        String(100),
        comment=f'{PRODUCT_TYPE.list()}',
        nullable=False,
        default=PRODUCT_TYPE.HEAVY.value)
    rcs_id = Column(String(255), comment='position id on RCS', nullable=False)
    floor = Column(String(100), nullable=False)
    prior = Column(Boolean, default=False, nullable=False)
    status = Column(
        String(100),
        comment=f'{TASK_STATUS.list()}',
        nullable=False,
        default=TASK_STATUS.SIGN.value)
    created_at = Column(DateTime(True), default=func.now())
    start_at = Column(DateTime(True))
    stop_at = Column(DateTime(True))

    @classmethod
    def fromCallbox(cls, callbox: DB_Callbox) -> Type["DB_Task"]:
        """
        Return new record from callbox
        """
        record = cls()
        record.line_id = callbox.line_id
        record.line_name = callbox.line_name
        record.product_type = callbox.product_type
        record.rcs_id = callbox.rcs_id
        record.floor = callbox.floor
        record.status = TASK_STATUS.SIGN.value
        return record

class DB_Error(db.Model, DbBaseModel):
    __tablename__ = 'error'
    id = Column(Integer, primary_key=True, nullable=False)
    code = Column(Integer, nullable=False)
    module = Column(
        String(100),
        comment=f'{ERROR_MODULE.list()}',
        nullable=False,
        default=ERROR_MODULE.SERVER.value)
    message = Column(String(255), nullable=False)
    occurred_at = Column(DateTime(True), default=func.now())