import asyncio
import logging
import os
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from yookassa import Configuration, Payment
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

# Настройки из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
PORT = int(os.getenv("PORT", "8080"))

# Настройка YooKassa
if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY
    print("✅ YooKassa configured")
else:
    print("⚠️ YooKassa credentials not found")

# Цена и файл гайда
GUIDE_PRICE = 390  # рублей
GUIDE_FILE_PATH = "/app/guide.pdf"

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Храним pending платежи в памяти (payment_id -> user_id)
pending_payments = {}


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Приветственное сообщение"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить за 390₽", callback_data="buy_guide")]
    ])
    
    await message.answer(
        "👋 Привет!\n\n"
        "🌸 <b>7 дней к внутреннему спокойствию в отношениях</b>\n\n"
        "Одна практика в день. 10-15 минут. Неделя на то, чтобы "
        "перестать жить его жизнью и вернуться к своей.\n\n"
        "💰 <b>Цена: 390₽</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "buy_guide")
async def callback_buy_guide(callback: types.CallbackQuery):
    """Обработчик нажатия кнопки Купить"""
    await callback.answer()
    
    try:
        user_id = callback.from_user.id
        
        # Создаем уникальный ID платежа
        idempotence_key = str(uuid.uuid4())
        
        # Создаем платеж в YooKassa
        payment = Payment.create({
            "amount": {
                "value": str(GUIDE_PRICE),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/psychology_guidebot"
            },
            "capture": True,
            "description": "Гайд: 7 дней к внутреннему спокойствию",
            "metadata": {
                "user_id": str(user_id),
                "product": "guide"
            }
        }, idempotence_key)
        
        # Сохраняем платеж
        pending_payments[payment.id] = user_id
        
        # Получаем ссылку на оплату
        confirmation_url = payment.confirmation.confirmation_url
        
        # Создаем кнопку для оплаты
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить 390₽", url=confirmation_url)],
            [InlineKeyboardButton(text="❓ Проверить оплату", callback_data=f"check_{payment.id}")]
        ])
        
        await callback.message.answer(
            "💳 <b>Оплата гайда</b>\n\n"
            f"Стоимость: <b>{GUIDE_PRICE}₽</b>\n\n"
            "Нажми кнопку ниже для оплаты.\n"
            "После оплаты нажми <b>\"Проверить оплату\"</b> чтобы получить гайд.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        logger.info(f"Платёж создан для пользователя {user_id}: {payment.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при создании платежа: {e}")
        await callback.message.answer(
            "😔 Произошла ошибка при создании платежа. Попробуй позже."
        )


@dp.message(Command("buy"))
async def cmd_buy(message: types.Message):
    """Создание платежа через YooKassa"""
    try:
        user_id = message.from_user.id
        
        # Создаем уникальный ID платежа
        idempotence_key = str(uuid.uuid4())
        
        # Создаем платеж в YooKassa
        payment = Payment.create({
            "amount": {
                "value": str(GUIDE_PRICE),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/psychology_guidebot"
            },
            "capture": True,
            "description": "Гайд: 7 дней к внутреннему спокойствию",
            "metadata": {
                "user_id": str(user_id),
                "product": "guide"
            }
        }, idempotence_key)
        
        # Сохраняем платеж
        pending_payments[payment.id] = user_id
        
        # Получаем ссылку на оплату
        confirmation_url = payment.confirmation.confirmation_url
        
        # Создаем кнопку для оплаты
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить 390₽", url=confirmation_url)],
            [InlineKeyboardButton(text="❓ Проверить оплату", callback_data=f"check_{payment.id}")]
        ])
        
        await message.answer(
            "💳 <b>Оплата гайда</b>\n\n"
            f"Стоимость: <b>{GUIDE_PRICE}₽</b>\n\n"
            "Нажми кнопку ниже для оплаты.\n"
            "После оплаты нажми <b>\"Проверить оплату\"</b> чтобы получить гайд.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        logger.info(f"Платёж создан для пользователя {user_id}: {payment.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при создании платежа: {e}")
        await message.answer(
            "😔 Произошла ошибка при создании платежа. Попробуй позже."
        )


@dp.callback_query(F.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery):
    """Проверка статуса платежа"""
    try:
        payment_id = callback.data.split("_")[1]
        user_id = callback.from_user.id
        
        # Проверяем платеж в YooKassa
        payment = Payment.find_one(payment_id)
        
        if payment.status == "succeeded":
            # Платёж успешен - отправляем гайд
            await callback.message.answer(
                "✅ <b>Оплата прошла успешно!</b>\n\n"
                "Спасибо за покупку! Отправляю тебе гайд...",
                parse_mode="HTML"
            )
            
            # Отправляем файл
            guide_file = FSInputFile(GUIDE_FILE_PATH)
            await bot.send_document(
                user_id,
                guide_file,
                caption=(
                    "📖 <b>7 дней к внутреннему спокойствию в отношениях</b>\n\n"
                    "Начинай с первого дня и делай по одной практике в день.\n"
                    "Не пропускай дни — каждая практика важна!\n\n"
                    "Удачи на пути к себе 💛"
                ),
                parse_mode="HTML"
            )
            
            # Удаляем из pending
            if payment_id in pending_payments:
                del pending_payments[payment_id]
            
            logger.info(f"Гайд отправлен пользователю {user_id}")
            await callback.answer("✅ Гайд отправлен!")
            
        elif payment.status == "pending":
            await callback.answer("⏳ Платёж ещё обрабатывается. Подожди немного.", show_alert=True)
        elif payment.status == "canceled":
            await callback.answer("❌ Платёж был отменён.", show_alert=True)
        else:
            await callback.answer("❓ Платёж не найден или ещё не оплачен.", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при проверке платежа: {e}")
        await callback.answer("😔 Ошибка при проверке платежа", show_alert=True)


async def yookassa_webhook_handler(request):
    """Обработчик webhook от YooKassa"""
    try:
        data = await request.json()
        logger.info(f"Получен webhook от YooKassa: {data}")
        
        event = data.get('event')
        payment_obj = data.get('object', {})
        payment_id = payment_obj.get('id')
        status = payment_obj.get('status')
        
        if event == 'payment.succeeded' and status == 'succeeded':
            # Получаем user_id из metadata
            metadata = payment_obj.get('metadata', {})
            user_id = metadata.get('user_id')
            
            if user_id and payment_id in pending_payments:
                user_id = int(user_id)
                
                # Отправляем гайд
                try:
                    await bot.send_message(
                        user_id,
                        "✅ <b>Оплата успешно завершена!</b>\n\n"
                        "Отправляю гайд...",
                        parse_mode="HTML"
                    )
                    
                    guide_file = FSInputFile(GUIDE_FILE_PATH)
                    await bot.send_document(
                        user_id,
                        guide_file,
                        caption=(
                            "📖 <b>7 дней к внутреннему спокойствию в отношениях</b>\n\n"
                            "Начинай с первого дня и делай по одной практике в день.\n"
                            "Не пропускай дни — каждая практика важна!\n\n"
                            "Удачи на пути к себе 💛"
                        ),
                        parse_mode="HTML"
                    )
                    
                    # Удаляем из pending
                    del pending_payments[payment_id]
                    
                    logger.info(f"✅ Гайд отправлен через webhook пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка отправки гайда через webhook: {e}")
        
        return web.Response(status=200)
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return web.Response(status=500)


async def main():
    """Запуск бота"""
    logger.info("=" * 60)
    logger.info("🚀 Запуск бота...")
    logger.info("=" * 60)
    
    WEBHOOK_URL = os.getenv('RAILWAY_PUBLIC_DOMAIN')
    
    if WEBHOOK_URL:
        if not WEBHOOK_URL.startswith('http'):
            WEBHOOK_URL = f"https://{WEBHOOK_URL}"
        
        webhook_path = "/webhook"
        webhook_full_url = f"{WEBHOOK_URL}{webhook_path}"
        
        logger.info(f"🌐 Webhook URL: {webhook_full_url}")
        
        # Удаляем старый webhook
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Устанавливаем новый webhook
        await bot.set_webhook(webhook_full_url)
        logger.info("✅ Webhook установлен")
        
        # Создаем веб-приложение
        app = web.Application()
        
        # Регистрируем YooKassa webhook
        app.router.add_post('/yookassa-webhook', yookassa_webhook_handler)
        logger.info("✅ YooKassa webhook: /yookassa-webhook")
        
        # Регистрируем Telegram webhook
        webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_handler.register(app, path=webhook_path)
        
        # Запускаем сервер
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        
        logger.info("=" * 60)
        logger.info("✅ BOT SUCCESSFULLY STARTED!")
        logger.info("=" * 60)
        logger.info(f"🌐 Telegram Webhook: {webhook_full_url}")
        logger.info(f"💳 YooKassa webhook: {WEBHOOK_URL}/yookassa-webhook")
        logger.info(f"🔌 Port: {PORT}")
        logger.info("=" * 60)
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("⛔ Остановка...")
        finally:
            await bot.delete_webhook()
            await runner.cleanup()
            logger.info("✅ Бот остановлен")
    else:
        logger.info("🔄 Запуск в polling режиме...")
        try:
            await dp.start_polling(bot)
        finally:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
