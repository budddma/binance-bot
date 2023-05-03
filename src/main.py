import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from market_data import MarketData
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import BotCommand

logger = logging.getLogger(__name__)

TOKEN = "5897946500:AAFfjQZnAbD_AoXLfosJrTfjoXUnbY4yQno"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


class MarketDataWrapper(StatesGroup):
    asking_pair = State()
    asking_timeframe = State()
    asking_indicators = State()
    available_timeframes = ("1 минута", "1 час", "1 день", "1 неделя", "1 месяц")
    available_indicators = [
        "SMA",
        "EMA",
        "RSI",
        "SO",
        "MACD",
        "WMA",
        "KST",
        "KAMA",
        "PPO",
        "ROC",
        "AD",
        "CMF",
        "CFO",
        "ATR",
        "BB",
    ]
    pair = None
    indicators = []
    obj = MarketData()


md = MarketDataWrapper()


async def process_start(message: types.Message):
    start_message = """
    Приветствую, уважаемый! Этот бот построит вам график свечей и индикаторов для выбранной валютной пары
    """
    await message.reply(start_message)


async def ask_pair(message: types.Message, state: FSMContext):
    await message.answer("Для начала отправьте мне валютную пару в формате: \nBTC USDT")
    await state.set_state(MarketDataWrapper.asking_pair.state)


async def ask_timeframe(message: types.Message, state: FSMContext):
    input_pair = message.text.upper().strip().split()
    pairs_list = md.obj.get_possible_pairs()

    if input_pair[0] + input_pair[1] not in pairs_list:
        await message.reply("Неправильно введена пара")
        return

    md.pair = input_pair

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for timeframe in md.available_timeframes:
        keyboard.add(timeframe)

    await message.answer("Выберите таймфрейм:", reply_markup=keyboard)
    await state.set_state(MarketDataWrapper.asking_timeframe.state)


async def ask_indicators(message: types.Message, state: FSMContext):
    input_timeframe = message.text.lower().strip()
    if input_timeframe not in md.available_timeframes:
        await message.reply("Выберите таймфрейм из списка ниже")
        return

    time_dict = {
        "1 минута": "1m",
        "1 час": "1h",
        "1 день": "1d",
        "1 неделя": "1w",
        "1 месяц": "1M",
    }
    md.obj.init_candle_df(md.pair, time_dict[input_timeframe])

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Я ВСЕ")
    for timeframe in md.available_indicators:
        keyboard.add(timeframe)

    await message.answer("Выберите до 5 индикаторов:", reply_markup=keyboard)
    await state.set_state(MarketDataWrapper.asking_indicators.state)


async def plot_chart(message: types.Message, state: FSMContext):
    input_indicator = message.text.upper().strip()

    if input_indicator != "Я ВСЕ":
        if input_indicator not in md.available_indicators:
            await message.reply("Выберите индикаторы из списка ниже")
            return

        if input_indicator in md.indicators:
            await message.reply("Уже было")
            return

        md.indicators.append(input_indicator)
        await message.answer(f"Вы выбрали {input_indicator}")

    if input_indicator == "Я ВСЕ" or len(md.indicators) == 5:
        md.obj.init_indicators_df(md.indicators)

        str_indicators = ", ".join(md.indicators)
        await message.answer(
            f"Вы выбрали {str_indicators}", reply_markup=types.ReplyKeyboardRemove()
        )

        charts_list = md.obj.get_charts_list()
        for chart in charts_list:
            await message.answer_photo(chart.to_image(format="png"))
        await state.finish()


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(process_start, commands="start", state="*")
    dp.register_message_handler(ask_pair, commands="plot_chart", state="*")
    dp.register_message_handler(ask_timeframe, state=MarketDataWrapper.asking_pair)
    dp.register_message_handler(
        ask_indicators, state=MarketDataWrapper.asking_timeframe
    )
    dp.register_message_handler(plot_chart, state=MarketDataWrapper.asking_indicators)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="стартуем"),
        BotCommand(command="/plot_chart", description="график рисуем"),
    ]
    await bot.set_my_commands(commands)


async def main():
    logging.basicConfig(level=logging.INFO)

    register_handlers(dp)
    await set_commands(bot)
    await dp.skip_updates()
    await dp.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
