import requests
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go


class BinanceException(Exception):
    def __init__(self, status_code):
        self.status_code = status_code
        super().__init__()


class MarketData:
    __pair = None
    __cndl_df = None
    __ind_df = None
    input_indicators = []

    @staticmethod
    def get_possible_pairs():
        url = "https://api.binance.com/api/v3/exchangeInfo"
        req = requests.get(url)
        exchange_info = req.json()

        symbols_list = []
        if req.status_code == 200:
            for s in exchange_info["symbols"]:
                symbols_list.append(s["symbol"])
        else:
            raise BinanceException(req.status_code)
        return symbols_list

    @classmethod
    def init_candle_df(cls, pair, timeframe):
        cls.__pair = pair

        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": cls.__pair,
            "interval": timeframe,
            "limit": 300,
        }

        req = requests.get(url, params=params)

        if req.status_code == 200:
            cndl_df = pd.DataFrame(req.json()).iloc[:, :6]
            cndl_df.columns = ["open_time", "open", "high", "low", "close", "volume"]
            cndl_df["open_time"] = pd.to_datetime(cndl_df["open_time"], unit="ms")
            cndl_df[cndl_df.columns[1:6]] = cndl_df[cndl_df.columns[1:6]].astype(float)
            cls.__cndl_df = cndl_df
        else:
            raise BinanceException(req.status_code)

    @classmethod
    def init_indicators_df(cls):
        ind_df = pd.DataFrame()
        ind_dict = {
            "SMA": ta.sma,  # close
            "EMA": ta.ema,  # close
            "RSI": ta.rsi,  # close
            "SO": ta.stoch,  # high low close
            "MACD": ta.macd,  # close
            "WMA": ta.wma,  # close
            "KST": ta.kst,  # close
            "KAMA": ta.kama,  # close
            "PPO": ta.ppo,  # close
            "ROC": ta.roc,  # close
            "AD": ta.ad,  # high low close volume
            "CMF": ta.cmf,  # high low close volume
            "CFO": ta.cfo,  # close
            "ATR": ta.atr,  # high low close
            "BB": ta.bbands,  # close
        }

        for ind in cls.input_indicators:
            ind_func = ind_dict[ind]
            if ind in {"SO", "ATR"}:
                args = [
                    cls.__cndl_df["high"],
                    cls.__cndl_df["low"],
                    cls.__cndl_df["close"],
                ]
            elif ind in {"AD", "CMF"}:
                args = [
                    cls.__cndl_df["high"],
                    cls.__cndl_df["low"],
                    cls.__cndl_df["close"],
                    cls.__cndl_df["volume"],
                ]
            else:
                args = [cls.__cndl_df["close"]]

            func_val = ind_func(*args)
            if isinstance(func_val, pd.DataFrame):
                for column in func_val.columns:
                    ind_df[column] = func_val[column]
            else:
                ind_df[ind] = ind_func(*args)

        cls.__ind_df = ind_df

    @classmethod
    def get_charts_list(cls):
        figures = {
            "candlestick": go.Figure(),
            "high": go.Figure(),
            "medium": go.Figure(),
            "low": go.Figure(),
        }

        figures["candlestick"].add_trace(
            go.Candlestick(
                x=cls.__cndl_df["open_time"],
                open=cls.__cndl_df["open"],
                high=cls.__cndl_df["high"],
                low=cls.__cndl_df["low"],
                close=cls.__cndl_df["close"],
                name="Свеча",
            )
        )

        min_price = cls.__cndl_df["low"].min()
        indicators = {"candlestick": [], "high": [], "medium": [], "low": []}

        for ind in cls.__ind_df.columns:
            if ind == "AD":
                figures[ind], indicators[ind] = go.Figure(), [ind]
                figures[ind].add_trace(
                    go.Scatter(
                        x=cls.__cndl_df["open_time"], y=cls.__ind_df[ind], name=ind
                    )
                )

            elif (
                ind == "CFO"
                or ind == "CMF"
                or ind.startswith("BBP")
                or ind.startswith("PPO")
            ):
                figures["low"].add_trace(
                    go.Scatter(
                        x=cls.__cndl_df["open_time"], y=cls.__ind_df[ind], name=ind
                    )
                )
                indicators["low"].append(ind)

            elif ind == "ATR" or ind.startswith("MACD"):
                figures["medium"].add_trace(
                    go.Scatter(
                        x=cls.__cndl_df["open_time"], y=cls.__ind_df[ind], name=ind
                    )
                )
                indicators["medium"].append(ind)

            elif cls.__ind_df[ind].max() < min_price:
                figures["high"].add_trace(
                    go.Scatter(
                        x=cls.__cndl_df["open_time"], y=cls.__ind_df[ind], name=ind
                    )
                )
                indicators["high"].append(ind)

            else:
                figures["candlestick"].add_trace(
                    go.Scatter(
                        x=cls.__cndl_df["open_time"], y=cls.__ind_df[ind], name=ind
                    )
                )
                indicators["candlestick"].append(ind)

        str_indicators = {}
        for key, value in indicators.items():
            str_indicators[key] = ", ".join(value)

        for key, value in figures.items():
            if key == "candlestick":
                value.update_layout(
                    title_text=f"{cls.__pair}",
                    title_font_size=20,
                )
                if len(str_indicators["candlestick"]):
                    value.update_layout(
                        title_text=f"{cls.__pair} и {str_indicators[key]}"
                    )

            elif len(value.data):
                value.update_layout(
                    title_text=f"{str_indicators[key]}", title_font_size=20
                )

            value.update_layout(
                yaxis_title="Стоимость",
                xaxis_rangeslider_visible=False,
                plot_bgcolor="rgba(210,210,210,1)",
            )

        figures_list = []
        for fig in figures.values():
            if len(fig.data):
                figures_list.append(fig)
        return figures_list
