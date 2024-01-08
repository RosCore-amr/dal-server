from utils.logger import Logger
from utils.vntime import VnDateTime, VnTimestamp

from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.model import Model
from sqlalchemy import (and_, func, Column, ForeignKey,
    String, Integer, Uuid, DateTime, Unicode, Boolean)
from sqlalchemy.orm import (Query,
    relationship, DeclarativeBase, backref)
from sqlalchemy.exc import IntegrityError, InvalidRequestError, DataError
from typing import Type

import json
from json import JSONEncoder
from datetime import datetime, date, time
from uuid import UUID
    
class CustomJsonEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (time, date, datetime)):
            return int(VnTimestamp.getTimestamp(obj))
        if isinstance(obj, UUID):
            return obj.__str__()
        if isinstance(obj, Model):
            record = dict(obj.__dict__)
            for key in record.copy():
                if key.startswith("_"):
                    record.pop(key)
            return record

db = SQLAlchemy()

class DbBaseModel(Model):
    """
        Add some database class method for SQLAlchemy
    """
    def toDict(self):
        """
        Return this record as dict
        """
        record = dict(self.__dict__)
        for key in record.copy():
            if key.startswith("_"):
                record.pop(key)
        return record

    @classmethod
    def fromDict(cls, record: dict) -> Type["DbBaseModel"]:
        """
        Create new object with dict data input
        """
        output = cls()
        for key in record:
            if hasattr(output, key) and key != "_sa_instance_state":
                setattr(output, key, record[key])
        return output

    @staticmethod
    def toJson(record: Type["list[DbBaseModel]|DbBaseModel"]) -> dict:
        """
        record: (record | list of records)

        Return (record | list of records) in dictionary (serializable)
        """
        return json.loads(
            json.dumps(record, cls=CustomJsonEncoder),
        )
    
    @staticmethod
    def addObject(record: Type["DbBaseModel"]):
        """
        Add a new record to db .
        If record exists, update record
        """
        db.session.add(record)
        db.session.commit()
        
    @classmethod
    def addByDict(cls, record: dict):
        """
        Add new record to table by dict.
        Make sure record has all needed attributions
        """
        cls.addObject(cls.fromDict(record))
    
    @classmethod
    def delete(cls, *filter, **filter_by) -> list:
        """
        Delete some records in database.
        Return list of deleted records in serialization

        *filter:
            DB_class.delete(DB_class.id == 1, DB_class.name == "abc")
        **filter_by (recommended):
            DB_class.delete(id = 1, name = "abc")
        Mixed:
            DB_class.delete(DB_class.id.in_([1, 2]), name = "abc")

        Return -> (list) list of records in json
        """
        finders = cls.find(*filter, **filter_by)
        if finders.count() == 0:
            return []
        
        records = cls.toJson(finders.all())
        finders.delete(synchronize_session=False)
        db.session.commit()
        return records
    
    @classmethod
    def deleteObject(cls, record: Type["DbBaseModel"]):
        """
        Delete a record in database
        """
        db.session.delete(record)
        db.session.commit()

    @classmethod
    def updateByDict(cls, record: dict, *filter, **filter_by) -> int:
        """
        Update a record with dict data input
        ---

        *filter:
            DB_class.update(record, DB_class.id == 1, DB_class.name == "abc")
        **filter_by (recommended):
            DB_class.update(record, id = 1, name = "abc")
        Mixed:
            DB_class.update(record, DB_class.id.in_([1, 2]), name = "abc")
        
        Return -> Result code
        ---
        * 0 if succeeded
        * 1 if record does not exist
        * 2 if more than 1 record found
        """
        num_finder = cls.getSubTotal(*filter, **filter_by)
        if num_finder == 0:
            return 1
        if num_finder > 1:
            return 2
        
        finder = cls.find(*filter, **filter_by).first()
        for key in record:
            if hasattr(finder, key) and\
                    key not in filter_by and\
                    key != "_sa_instance_state":
                setattr(finder, key, record[key])
        db.session.add(finder)
        db.session.commit()
        return 0

    @classmethod
    def update(cls, record: Type["DbBaseModel"], *filter, **filter_by):
        """
        Update a record in database
        * Return None if record does not exist
        * Return {} if more than 1 record found
        * Return record if succeeded
        """
        return cls.updateByDict(record.toDict(), *filter, **filter_by)
    
    @classmethod
    def find(cls, *filter, **filter_by) -> Query:
        """
        Find records in dabtabase
        
        *filter:
            DB_class.update(record, DB_class.id == 1, DB_class.name == "abc")
        **filter_by (recommended):
            DB_class.update(record, id = 1, name = "abc")
        Mixed:
            DB_class.update(record, DB_class.id.in_([1, 2]), name = "abc")
        """
        finders = cls.query
        if filter:
            finders = finders.filter(*filter)
        if filter_by:
            finders = finders.filter_by(**filter_by)

        return finders
    
    @classmethod
    def findById(cls, id) -> Type["DbBaseModel"]:
        """
        Faster way to search for record
        """
        return cls.query.get(id)
    
    @classmethod
    def getQuery(cls, *args, **kwargs):
        return db.session.query(*args, **kwargs)

    @classmethod
    def getAllAttr(cls) -> list:
        """
        Return list of column name
        """
        return [c.name for c in cls.__table__.columns]
    
    @classmethod
    def getColumn(cls, name: str) -> Column:
        """
        Return model property by name (or table column, not its data)
        """
        return cls.__table__.columns[name]

    @classmethod
    def getTotal(cls, primary_key: str = "id"):
        """
        Return number of records in a table
        (using primary key for faster query)
        """
        column = cls.getColumn(primary_key)
        return db.session.query(func.count(column)).scalar()
    
    @classmethod
    def getSubTotal(cls, *filters, **filter_by) -> int:
        """
        Return number of records in filted table
        """
        query = cls.query.filter(*filters).filter_by(**filter_by)
        return query.count()
        
    @classmethod
    def normalFilter(cls, query: Query, filters: dict) -> Query:
        """
        filters:
        ```
        {
            <property>: value | (list) values
        }
        ```

        Return -> sorter to add to model query
        ```
        query.filter(*filter_args).filter_by(**filter_kwargs) -> Query
        ```
        """
        filter_args = ()
        filter_kwargs = {}
        for column_name in filters:
            value = filters[column_name]
            column = cls.getColumn(column_name)
            if type(value) == list:
                filter_args = *filter_args, column.in_(value)
            else:
                filter_kwargs[column_name] = value
        return query.filter(*filter_args).filter_by(**filter_kwargs)

    @classmethod
    def orderFilter(cls, query: Query, filters: list) -> Query:
        """
        filters: (list) column names

        Return -> orders to add to model query
        ```
        query.order_by(*orders) -> Query
        ```
        """
        columns = ()
        if type(filters) != list:
            filters = [filters]

        for name in filters:
            columns = *columns, cls.getColumn(name).desc()
        return query.order_by(*columns)

    @classmethod
    def durationFilter(cls, query: Query, filters: list) -> Query:
        """
        filters:
        ```
        [
            {
                "name": (str) column name,
                "start": (float) start timestamp,
                "stop": (float) stop timestamp
            }
        ]
        ```
        Date-time format: "DD-MM-YYYY HH:mm:ss"

        Return -> time filters to add to model query
        ```
        query.filter(*filters) -> Query
        ```
        """
        if type(filters) != list:
            filters = [filters]

        time_filters = ()
        for time_filter in filters:
            time_col = cls.getColumn(time_filter["name"])
            start_time = VnDateTime.fromTimeStamp(time_filter["start"])
            stop_time = VnDateTime.fromTimeStamp(time_filter["stop"])
            time_filters = *time_filters, time_col.between(start_time, stop_time)
        return query.filter(*time_filters)
        
    @classmethod
    def columnFilter(cls, query: Query, filters: list) -> Query:
        """
        filters: (list) column names

        Return -> list of column values without duplication to model query
        ```
        query.with_entities(*columns).distinct() -> Query, column_names
        ```
        """
        columns = ()
        if type(filters) != list:
            filters = [filters]

        for name in filters:
            columns = *columns, cls.getColumn(name)
        return query.with_entities(*columns).distinct(), filters
    
    @classmethod
    def pagination(cls, query: Query, skip: int, limit: int) -> Query:
        """
        skip: (int) order number of page (starting at 1),
        limit: (int) number of records in 1 page

        Return -> pagination filter to add to model query
        ```
        query.limit(limit).offset(skip*limit) -> Query, skip, limit
        ```
        """
        skip = skip - 1
        return query.limit(limit).offset(skip * limit)
    

from .import_all import *