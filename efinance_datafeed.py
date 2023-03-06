
import time
from datetime import timedelta, datetime
from json import encoder
from typing import List, Optional
from pytz import timezone
from math import isnan
from pandas import DataFrame
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest,TickData

from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.database import BaseDatabase, get_database

import efinance as ef

CHINA_TZ = timezone("Asia/Shanghai")

EXCHANGE_MAP = {
    Exchange.CFFEX: "8",
    Exchange.SHFE: "113",
    Exchange.DCE: "114",
    Exchange.CZCE: "115",
    Exchange.INE: "142",
    Exchange.SSE: "1",
    Exchange.SZSE: "0",
}

INTERVAL_MAP = {
    Interval.MINUTE:    1,
    Interval.HOUR:      60,
    Interval.DAILY:     101,
    Interval.TICK:      0,
}


def to_ef_symbol(symbol, exchange) -> Optional[str]:
    """将交易所代码转换为ef_symbol:quote_id_mode"""
    # 股票
    if exchange in [Exchange.SSE, Exchange.SZSE]:
        ef_symbol = f"{EXCHANGE_MAP[exchange]}.{symbol}"
    # 期货
    elif exchange in [
        Exchange.CFFEX,
        Exchange.SHFE,
        Exchange.DCE,
        Exchange.CZCE,
        Exchange.INE
    ]:
        ef_symbol = f"{EXCHANGE_MAP[exchange]}.{symbol}".upper()
    else:
        return None
    return ef_symbol


class EfinanceDatafeed(BaseDatafeed):
    """efinance数据服务接口"""

    def init(self) -> bool:
        """初始化"""
        self.inited = True


    def query_data_history(self, req: HistoryRequest) -> Optional[List[BarData]]:
        """查询数据"""
        if req.interval == Interval.TICK:
            return self.query_tick_history(req)
        else:
            return self.query_bar_history(req)    

    def query_bar_history(self, req: HistoryRequest) -> Optional[List[BarData]]:
        if req.interval == Interval.MINUTE:
            return self.query_bar_1m_history(req)    
        else:
            return self.query_bar_1dh_history(req)


    def query_bar_1m_history(self, req: HistoryRequest) -> Optional[List[BarData]]:
        """查询1min-kline数据 by get_latest_ndays_quote"""
        # 查询最大5d
        symbol      = req.symbol
        exchange    = req.exchange
        interval    = req.interval

        ndays       = (req.end-req.start).days
        ndays       = min(5,ndays)
        ef_symbol   = to_ef_symbol(symbol, exchange)

        df = ef.common.get_latest_ndays_quote(
            ef_symbol, 
            ndays,
            quote_id_mode=True
            )

        data: List[BarData] = []
        if df is not None:
            for ix, row in df.iterrows():
                if row['开盘'] is None:
                    continue

                dt = row["日期"]
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M")
                dt = CHINA_TZ.localize(dt)

                bar = BarData(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    datetime=dt,
                    open_price=row["开盘"],
                    high_price=row["最高"],
                    low_price=row["最低"],
                    close_price=row["收盘"],
                    volume=row["成交量"],
                    turnover=row.get("成交额", 0),
                    open_interest=0,
                    gateway_name="ef"
                )

                data.append(bar)
        data = sorted(data,key=lambda x:x.datetime,reverse=False)
        return data


    def query_bar_1dh_history(self, req: HistoryRequest) -> Optional[List[BarData]]:
        """查询hour/daily-kline数据 by get_quote_history"""
        symbol      = req.symbol
        exchange    = req.exchange
        interval    = req.interval
        start       = req.start.strftime("%Y%m%d")
        end         = req.end.strftime("%Y%m%d")

        ef_symbol   = to_ef_symbol(symbol, exchange)
        ef_interval = INTERVAL_MAP.get(interval)
        if not ef_interval:return None

        df = ef.common.get_quote_history(
            ef_symbol,
            start,
            end,
            klt=ef_interval,
            fqt=0,
            quote_id_mode=True
            )

        data: List[BarData] = []
        if df is not None:
            for ix, row in df.iterrows():
                if row['开盘'] is None:
                    continue

                dt = row["日期"]
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M") if interval==Interval.HOUR else datetime.strptime(dt, "%Y-%m-%d")
                dt = CHINA_TZ.localize(dt)

                bar = BarData(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    datetime=dt,
                    open_price=row["开盘"],
                    high_price=row["最高"],
                    low_price=row["最低"],
                    close_price=row["收盘"],
                    volume=row["成交量"],
                    turnover=row.get("成交额", 0),
                    open_interest=0,
                    gateway_name="ef"
                )

                data.append(bar)
        return data


    def query_tick_history(self, req: HistoryRequest) -> Optional[List[TickData]]:
        """"""
        return []
    
    ######################################################################################################################
    ######################################################################################################################

    def query_today_trade(self,symbol,exchange,max_count= 1000000):
        """获取当日成交"""
        ef_symbol   = to_ef_symbol(symbol, exchange)
        df = ef.common.get_deal_detail(ef_symbol,max_count)
        return df
    


# 这个暂时先这样，后面研究一下东方财富的接口，然后自己写一个，把需要的信息完善好
