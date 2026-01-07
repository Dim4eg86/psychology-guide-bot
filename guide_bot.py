import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, FSInputFile

# Настройки
BOT_TOKEN = "8578897112:AAHp20pdVSXTVjxmhxN82CubuKybx-MnNco"
YOOKASSA_TOKEN = "live_ghw_QjfPTHOz06kkElqJGHqCZqAHxO9EtS1vdABx8BU"

# Цена гайда
GUIDE_PRICE = 390  # рублей
GUIDE_FILE_PATH = "/home/claude/guide.pdf"

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Приветственное сообщение"""
    await message.answer(
        "👋 Привет!\n\n"
        "🌸 **7 дней к внутреннему спокойствию в отношениях**\n\n"
        "Одна практика в день. 10-15 минут. Неделя на то, чтобы "
        "перестать жить его жизнью и вернуться к своей.\n\n"
        "💰 **Цена:** 390₽\n\n"
        "Нажми /buy для покупки",
        parse_mode="Markdown"
    )


@dp.message(Command("buy"))
async def cmd_buy(message: types.Message):
    """Отправка счёта на оплату"""
    try:
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="7 дней к внутреннему спокойствию",
            description="Гайд с практиками для работы с тревогой в отношениях. "
                       "7 дней, по одной практике в день.",
            payload="guide_payment",
            provider_token=YOOKASSA_TOKEN,
            currency="RUB",
            prices=[
                LabeledPrice(label="Гайд по психологии", amount=GUIDE_PRICE * 100)
            ],
            # Дополнительные параметры для красоты
            photo_url="https://i.imgur.com/placeholder.jpg",  # можно добавить картинку
            photo_width=800,
            photo_height=450,
            need_email=False,
            need_phone_number=False,
            is_flexible=False
        )
        logger.info(f"Счёт отправлен пользователю {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке счёта: {e}")
        await message.answer(
            "😔 Произошла ошибка при создании счёта. Попробуй позже или напиши в поддержку."
        )


@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Подтверждение платежа перед оплатой"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    logger.info(f"Pre-checkout подтверждён для {pre_checkout_query.from_user.id}")


@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    """Обработка успешного платежа и отправка гайда"""
    try:
        # Логируем успешную оплату
        payment_info = message.successful_payment
        logger.info(
            f"Успешный платёж от {message.from_user.id}: "
            f"{payment_info.total_amount / 100} {payment_info.currency}"
        )
        
        # Отправляем подтверждение
        await message.answer(
            "✅ **Оплата прошла успешно!**\n\n"
            "Спасибо за покупку! Отправляю тебе гайд...",
            parse_mode="Markdown"
        )
        
        # Отправляем файл
        guide_file = FSInputFile(GUIDE_FILE_PATH)
        await bot.send_document(
            message.chat.id,
            guide_file,
            caption=(
                "📖 **7 дней к внутреннему спокойствию в отношениях**\n\n"
                "Начинай с первого дня и делай по одной практике в день.\n"
                "Не пропускай дни — каждая практика важна!\n\n"
                "Удачи на пути к себе 💛"
            ),
            parse_mode="Markdown"
        )
        
        logger.info(f"Гайд отправлен пользователю {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке гайда: {e}")
        await message.answer(
            "😔 Произошла ошибка при отправке файла. "
            "Напиши в поддержку, мы решим проблему!"
        )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Справка"""
    await message.answer(
        "ℹ️ **Помощь**\n\n"
        "/start - Начать\n"
        "/buy - Купить гайд\n"
        "/help - Эта справка\n\n"
        "По всем вопросам пиши @your_support",
        parse_mode="Markdown"
    )


async def main():
    """Запуск бота"""
    logger.info("Бот запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
