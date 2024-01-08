import arrow
from datetime import timedelta, datetime
from typing import Type

class VnCommonFormat:
	FULL		= 'DD-MM-YYYY HH:mm:ss'
	INV_FULL	= "HH:mm:ss DD-MM-YYYY"
	DATE 		= "DD-MM-YYYY"
	TIME 		= "HH:mm:ss"
	CLOCK 		= "HH:mm"
	CLOCK_DATE 	= "HH:mm/DD-MM-YYYY"
	DATE_MONTH 	= "DD/MM"

class VnTimestamp:
	@staticmethod
	def today_8am():
		dateNow = arrow.utcnow().date()
		hourNow = arrow.utcnow().time().hour
		if hourNow >=8:
			return(arrow.get(dateNow).shift(hours=8).timestamp - 25200)
		else:
			return(arrow.get(dateNow).shift(hours=-16).timestamp - 25200)
	
	@staticmethod
	def tomorrow_8am():
		tomorrow = VnTimestamp.today_8am() +  86400
		return tomorrow

	@staticmethod
	def now() -> float:
		"""
		Return current timestamp
		"""
		return arrow.get(arrow.utcnow().shift(hours=7), locale="vi-vn").timestamp()

	@staticmethod
	def work_start(date):
		"""
		Lấy ngày theo giờ hiện tại
		"""
		hourNow = arrow.utcnow().time().hour
		if hourNow >= 8:
			return arrow.get(date + ' 01:00:00', VnCommonFormat.FULL).timestamp()
		else: 
			return arrow.get(date + ' 01:00:00', VnCommonFormat.FULL).shift(days=-1).timestamp()

	@staticmethod
	def work_end(date):
		work_end = VnTimestamp.work_start(date) +  86399
		return work_end
	
	@staticmethod
	def day_start(date):
		if '/' in date:
			return arrow.get(date, "DD/MM/YYYY").timestamp
		else:
			return arrow.get(date, "DD-MM-YYYY").timestamp

	@staticmethod
	def day_end(date):
		return arrow.get(date, "DD-MM-YYYY").shift(days=1).timestamp - 1

	def today_start():
		dateNow = arrow.utcnow().date()
		return(arrow.get(dateNow).timestamp - 25200)
	
	@staticmethod
	def today_end():
		return VnTimestamp.today_start() +  86399

	@staticmethod
	def month_start():
		""" Trả ra timestamp của ngày đầu tiên trong tháng
  
		"""
		now = arrow.utcnow().timestamp
		date=arrow.get(now).format("DD-MM-YYYY")
		date = "01" + date[2:]
		return arrow.get(date, "DD-MM-YYYY").timestamp

	@staticmethod
	def add_minute(strtime):
		"""
		Input: 20:00 => Return 20:01
		"""
		[hour, minute] = strtime.split(":")
		output = str(timedelta(hours=int(hour), minutes=int(minute) + 1))[-8:-3].strip()
		if len(output) == 4:
			output = "0" + output
		return output

	@staticmethod
	def get_day_by_shift(timestamp):
		""" Trả ra string HH:mm/DD-MM-YYY từ timestamp dầu vào

		"""
		time = VnTimestamp.getTimeString(timestamp, "HH")
		day = VnTimestamp.getTimeString(timestamp, "DD")
		month = VnTimestamp.getTimeString(timestamp, "MM-YYYY")
		if int(time) < 8:
			day = int(day) - 1
			if len(str(day)) == 1:
				day = f"0{day}"
		outData = f"{day}-{month}"
		return outData

	@staticmethod
	def get_date_to_timestamp(timestamp):
		""" Trả ra string HH:mm/DD-MM-YYY từ timestamp dầu vào

		"""
		timestamp = int(timestamp)
		timeDay = arrow.get(timestamp).format("DD-MM-YYYY")
		outData = arrow.get(timeDay, "DD-MM-YYYY").timestamp
		return outData
	
	@staticmethod
	def getArrow(date_time: Type["datetime | float"]) -> arrow.Arrow:
		return arrow.get(date_time, locale="vi-vn")
	
	@staticmethod
	def getTimestamp(date_time: datetime) -> float:
		"""
		date_time: datetime in Ho Chi Minh timezone

		Return -> Epoch time (second: float)
		"""
		return VnTimestamp.getArrow(date_time).timestamp()
	
	@staticmethod
	def toString(time_object: Type["datetime | float"], fmt: str = VnCommonFormat.FULL) -> str:
		"""
		Return ```date_time``` in string following format ```fmt```
		D: date; M: month; Y: year
		h: hour; m: minute; s: second
		"""
		if not time_object:
			return None
		return VnTimestamp.getArrow(time_object).format(fmt, locale="vi-vn")
	
	@staticmethod
	def fromString(date_time_string: str, fmt: str) -> float:
		"""
		Return -> Epoch time (second: float)
		"""
		return arrow.get(date_time_string, fmt).timestamp()
	
	@staticmethod
	def timePass(past: datetime) -> float:
		"""
		Return -> duration second from the past till now
		"""
		return VnTimestamp.now() - VnTimestamp.getTimestamp(past)

class VnDateTime:
	@staticmethod
	def fromString(time_string: str, fmt: str = VnCommonFormat.FULL) -> datetime:
		return arrow.get(time_string, fmt).datetime
	
	@staticmethod
	def fromTimeStamp(timestamp: float) -> datetime:
		return arrow.get(timestamp).datetime
	
	@staticmethod
	def now():
		"""
		Return the current time as datetime
		"""
		return arrow.utcnow().shift(hours=7).datetime
	
	@staticmethod
	def nowString(fmt: str = VnCommonFormat.FULL):
		"""
		Return the current time as string format (fmt)
		"""
		return VnTimestamp.toString(VnTimestamp.now(), fmt)