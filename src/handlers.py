from aiogram import Dispatcher, types
from market_data import MarketData, BinanceException
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from database import get_usernames, insert_into_table, get_user_data

AVAILABLE_TIMEFRAMES = ("1 минута", "1 час", "1 день", "1 неделя", "1 месяц")
AVAILABLE_INDICATORS = (
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
)


class DialogStates(StatesGroup):
    choose_data = State()
    process_pair = State()
    process_timeframe = State()
    process_indicators = State()


async def process_start(message: types.Message, state: FSMContext):
    await state.reset_state()
    MarketData.input_indicators = []
    start_message = """
    Приветствую, уважаемый! Этот бот построит вам график свечей и индикаторов для выбранной валютной пары. Запросы каждого пользователя сохраняются и могут быть восстановлены при попытке построить новый график командой /new_chart
    """
    await message.answer(
        start_message,
        reply_markup=types.ReplyKeyboardRemove(),
    )


async def process_new_chart(message: types.Message, state: FSMContext):
    await state.reset_state()
    MarketData.input_indicators = []
    await state.set_state(DialogStates.process_pair.state)
    await check_user(message, state)


async def check_user(message: types.Message, state: FSMContext):
    username = message.from_user.username
    async with state.proxy() as data:
        data["username"] = username

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = ["МОЖЕМ ПОВТОРИТЬ", "Введу заново"]
    keyboard.add(*buttons)

    if username in get_usernames():
        user_data = get_user_data(message.from_user.username)
        await message.answer(
            f"Давно тебя не было в уличных гонках, {username}. Использовать последние введённые данные?\n"
            f"Пара: {user_data[0]}\n"
            f"Таймфрейм: {user_data[1]}\n"
            f"Индикаторы: {user_data[2]}",
            reply_markup=keyboard,
        )
        await state.set_state(DialogStates.choose_data.state)

    else:
        await message.answer(
            "Для начала отправьте мне валютную пару в формате: \nBTCUSDT",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        await state.set_state(DialogStates.process_pair.state)


async def choose_data(message: types.Message, state: FSMContext):
    if message.text.upper().strip() == "МОЖЕМ ПОВТОРИТЬ":
        await plot_charts(message, state)

    else:
        await message.answer(
            "Для начала отправьте мне валютную пару в формате: \nBTCUSDT",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        await state.set_state(DialogStates.process_pair.state)


async def plot_charts(message: types.Message, state: FSMContext):
    time_dict = {
        "1 минута": "1m",
        "1 час": "1h",
        "1 день": "1d",
        "1 неделя": "1w",
        "1 месяц": "1M",
    }

    args = get_user_data(message.from_user.username)

    try:
        MarketData.init_candle_df(args[0], time_dict[args[1]])
    except BinanceException as e:
        print(f"🚨 Запрос к Binance API завершился с ошибкой {e.status_code}")

    if args[2]:
        MarketData.input_indicators = args[2].split(", ")
        MarketData.init_indicators_df()

        for chart in MarketData.get_charts_list():
            await message.answer_photo(chart.to_image(format="png"))

    else:
        await message.answer_photo(
            MarketData.get_only_candlestick().to_image(format="png")
        )

    MarketData.input_indicators = []
    await state.reset_state()


async def process_pair(message: types.Message, state: FSMContext):
    input_pair = message.text.upper().strip()
    possible_pairs = []
    try:
        possible_pairs = MarketData.get_possible_pairs()
    except BinanceException as e:
        print(f"🚨 Запрос к Binance API завершился с ошибкой {e.status_code}")

    if input_pair not in possible_pairs:
        await message.reply("Такой пары не существует")
        return

    async with state.proxy() as data:
        data["pair"] = input_pair

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    row = []
    for button in AVAILABLE_TIMEFRAMES:
        row.append(button)

        if len(row) == 2:
            keyboard.add(*row)
            row.clear()

    if row:
        keyboard.add(*row)

    await message.answer(
        "Выберите таймфрейм (временной интервал одной свечи):", reply_markup=keyboard
    )
    await state.set_state(DialogStates.process_timeframe.state)


async def process_timeframe(message: types.Message, state: FSMContext):
    input_timeframe = message.text.lower().strip()

    if input_timeframe not in AVAILABLE_TIMEFRAMES:
        await message.reply("Клавиатура для лохов?")
        return

    async with state.proxy() as data:
        data["timeframe"] = input_timeframe

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Я закончил выбирать индикаторы")

    row = []
    for button in AVAILABLE_INDICATORS:
        row.append(button)

        if len(row) == 3:
            keyboard.add(*row)
            row.clear()

    if row:
        keyboard.add(*row)

    await message.answer("Выберите до 5 индикаторов:", reply_markup=keyboard)
    await state.set_state(DialogStates.process_indicators.state)


async def process_indicators(message: types.Message, state: FSMContext):
    input_indicator = message.text.upper().strip()

    if not input_indicator.startswith("Я ЗАКОНЧИЛ"):
        if input_indicator not in AVAILABLE_INDICATORS:
            await message.reply("Клавиатура для лохов?")
            return

        if input_indicator in MarketData.input_indicators:
            await message.reply("Повторяешься")
            return

        MarketData.input_indicators.append(input_indicator)
        await message.answer(f"Вы выбрали {input_indicator}")

    if (
        input_indicator.startswith("Я ЗАКОНЧИЛ")
        or len(MarketData.input_indicators) == 5
    ):
        str_indicators = ", ".join(MarketData.input_indicators)

        async with state.proxy() as data:
            data["indicators"] = str_indicators

        ans = (
            f"Вы выбрали {str_indicators}"
            if str_indicators
            else "Вы не выбрали индикаторов"
        )

        await message.answer(ans, reply_markup=types.ReplyKeyboardRemove())

        await insert_into_table(state)
        await plot_charts(message, state)


async def send_goida(message: types.Message):
    sticker_id = (
        "CAACAgIAAxkBAAEI7N9kWpMHrwxSnoCv97Wj7Xr8N04EoQACJRMAAkKvaQABFKxDSf9OkD8vBA"
    )
    await message.reply_sticker(sticker=sticker_id)


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(process_start, commands="start", state="*")
    dp.register_message_handler(process_new_chart, commands="new_chart", state="*")
    dp.register_message_handler(choose_data, state=DialogStates.choose_data)
    dp.register_message_handler(process_pair, state=DialogStates.process_pair)
    dp.register_message_handler(process_timeframe, state=DialogStates.process_timeframe)
    dp.register_message_handler(
        process_indicators, state=DialogStates.process_indicators
    )
    dp.register_message_handler(send_goida, commands="goida")
