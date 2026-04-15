import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import json
import io

from free_god_eye import FreeGodEye

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    waiting_for_username = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_ip = State()
    waiting_for_search = State()
    waiting_for_ai_prompt = State()
    waiting_for_image_prompt = State()

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Поиск по нику", callback_data="menu_username")],
        [InlineKeyboardButton(text="📧 Поиск по email", callback_data="menu_email")],
        [InlineKeyboardButton(text="📞 Анализ телефона", callback_data="menu_phone")],
        [InlineKeyboardButton(text="🌐 Анализ IP", callback_data="menu_ip")],
        [InlineKeyboardButton(text="🔍 Поиск в интернете", callback_data="menu_search")],
        [InlineKeyboardButton(text="🤖 Спросить ИИ", callback_data="menu_ai")],
        [InlineKeyboardButton(text="🎨 Сгенерировать картинку", callback_data="menu_image")],
        [InlineKeyboardButton(text="🛡️ Проверить текст на утечки", callback_data="menu_sensitive")],
    ])

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👁️ *БЕСПЛАТНЫЙ ГЛАЗ БОГА*\n\n"
        "Абсолютно бесплатный OSINT-инструмент.\n"
        "Использует только открытые API.\n\n"
        "Выбери действие:",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )

# ========== ОБРАБОТЧИКИ МЕНЮ ==========
@dp.callback_query(lambda c: c.data == "menu_username")
async def menu_username(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_username)
    await callback.message.edit_text(
        "👤 Отправь никнейм для поиска.\n"
        "Я проверю 50+ платформ бесплатно."
    )

@dp.callback_query(lambda c: c.data == "menu_email")
async def menu_email(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_email)
    await callback.message.edit_text(
        "📧 Отправь email для проверки.\n"
        "Найду утечки, соцсети и Gravatar."
    )

@dp.callback_query(lambda c: c.data == "menu_phone")
async def menu_phone(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_phone)
    await callback.message.edit_text(
        "📞 Отправь номер телефона.\n"
        "Определю оператора, регион и страну."
    )

@dp.callback_query(lambda c: c.data == "menu_ip")
async def menu_ip(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_ip)
    await callback.message.edit_text("🌐 Отправь IP-адрес для анализа.")

@dp.callback_query(lambda c: c.data == "menu_search")
async def menu_search(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_search)
    await callback.message.edit_text("🔍 Что будем искать в интернете?")

@dp.callback_query(lambda c: c.data == "menu_ai")
async def menu_ai(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_ai_prompt)
    await callback.message.edit_text(
        "🤖 Задай вопрос бесплатному ИИ.\n"
        "Использую DeepSeek / Groq."
    )

@dp.callback_query(lambda c: c.data == "menu_image")
async def menu_image(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_image_prompt)
    await callback.message.edit_text("🎨 Опиши картинку для генерации (бесплатный Flux).")

@dp.callback_query(lambda c: c.data == "menu_sensitive")
async def menu_sensitive(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🛡️ Отправь текст — я найду в нём:\n"
        "• Email адреса\n"
        "• Номера телефонов\n"
        "• IP адреса\n"
        "• Номера карт\n"
        "• Паспортные данные"
    )

# ========== ОСНОВНОЙ ОБРАБОТЧИК ==========
@dp.message()
async def handle_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if not current_state:
        await message.answer("Используй меню /start", reply_markup=get_main_menu())
        return
    
    async with FreeGodEye() as eye:
        
        # === ПОИСК ПО НИКУ ===
        if current_state == States.waiting_for_username.state:
            msg = await message.answer("🔎 Ищу профили на 50+ платформах...")
            
            results = await eye.search_username_global(message.text)
            
            if results.get("error"):
                await msg.edit_text(f"❌ Ошибка: {results['error']}")
            else:
                report = f"*📊 РЕЗУЛЬТАТЫ ПОИСКА: {message.text}*\n\n"
                report += f"Найдено: {len(results['found'])}/{results['total_checked']}\n\n"
                
                for site in results['found'][:20]:
                    report += f"✅ [{site['platform']}]({site['url']}) - {site['category']}\n"
                
                if len(results['found']) > 20:
                    report += f"\n... и ещё {len(results['found']) - 20}"
                
                await msg.edit_text(report, parse_mode="Markdown", disable_web_page_preview=True)
            
            await state.clear()
        
        # === ПОИСК ПО EMAIL ===
        elif current_state == States.waiting_for_email.state:
            msg = await message.answer("📧 Проверяю email...")
            
            results = await eye.search_email(message.text)
            
            report = f"*📧 АНАЛИЗ EMAIL: {message.text}*\n\n"
            report += f"Валидный: {'✅ Да' if results['valid'] else '❌ Нет'}\n"
            report += f"Провайдер: {results['provider'] or 'Неизвестно'}\n\n"
            
            if results['social']:
                report += "*Найденные соцсети:*\n"
                for site in results['social']:
                    report += f"• {site}\n"
            
            if results['breaches']:
                breaches = results['breaches']
                report += f"\n⚠️ *Утечки:* {breaches['total_breaches']}\n"
                for source in breaches['sources'][:5]:
                    report += f"• {source}\n"
            
            if results['gravatar']:
                report += f"\n[📸 Gravatar]({results['gravatar']})"
            
            await msg.edit_text(report, parse_mode="Markdown", disable_web_page_preview=True)
            await state.clear()
        
        # === АНАЛИЗ ТЕЛЕФОНА ===
        elif current_state == States.waiting_for_phone.state:
            msg = await message.answer("📞 Анализирую номер...")
            
            results = await eye.analyze_phone(message.text)
            
            report = f"*📞 АНАЛИЗ НОМЕРА*\n\n"
            report += f"Номер: `{results['formatted']}`\n"
            report += f"Оператор: {results['operator']}\n"
            report += f"Регион: {results['region']}\n"
            report += f"Страна: {results['country']}\n"
            
            await msg.edit_text(report, parse_mode="Markdown")
            await state.clear()
        
        # === АНАЛИЗ IP ===
        elif current_state == States.waiting_for_ip.state:
            msg = await message.answer("🌐 Анализирую IP...")
            
            results = await eye.analyze_ip(message.text)
            
            if results.get("error"):
                await msg.edit_text(f"❌ {results['error']}")
            else:
                report = f"*🌐 IP: {results['ip']}*\n\n"
                report += f"📍 {results['country']}, {results['region']}, {results['city']}\n"
                report += f"📡 Провайдер: {results['isp']}\n"
                report += f"🏢 Организация: {results['org'] or 'Не указана'}\n"
                report += f"🛡️ VPN/Прокси: {'⚠️ Да' if results['vpn_proxy'] else '✅ Нет'}\n"
                report += f"📱 Мобильный: {'Да' if results['mobile'] else 'Нет'}\n"
                report += f"\n[🗺️ Карта]({results['maps_url']})"
                
                await msg.edit_text(report, parse_mode="Markdown", disable_web_page_preview=True)
            
            await state.clear()
        
        # === ПОИСК В ИНТЕРНЕТЕ ===
        elif current_state == States.waiting_for_search.state:
            msg = await message.answer("🔍 Ищу в DuckDuckGo...")
            
            results = await eye.search_duckduckgo(message.text)
            
            report = f"*🔍 РЕЗУЛЬТАТЫ ПОИСКА: {message.text[:50]}*\n\n"
            
            for r in results[:8]:
                if r.get("title"):
                    report += f"[{r['title'][:50]}]({r['url']})\n"
                    if r.get("snippet"):
                        report += f"_{r['snippet'][:100]}..._\n\n"
            
            await msg.edit_text(report, parse_mode="Markdown", disable_web_page_preview=True)
            await state.clear()
        
        # === СПРОСИТЬ ИИ ===
        elif current_state == States.waiting_for_ai_prompt.state:
            msg = await message.answer("🤖 DeepSeek думает...")
            
            response = await eye.ask_ai(message.text, "deepseek")
            
            # Разбиваем на части если длинное
            if len(response) > 4000:
                for i in range(0, len(response), 4000):
                    await message.answer(response[i:i+4000])
                await msg.delete()
            else:
                await msg.edit_text(response)
            
            await state.clear()
        
        # === ГЕНЕРАЦИЯ КАРТИНКИ ===
        elif current_state == States.waiting_for_image_prompt.state:
            msg = await message.answer("🎨 Генерирую изображение (это может занять минуту)...")
            
            image_bytes = await eye.generate_image_free(message.text)
            
            if image_bytes:
                await msg.delete()
                await message.answer_photo(
                    types.BufferedInputFile(image_bytes, filename="generated.jpg"),
                    caption=f"🎨 *{message.text[:100]}*",
                    parse_mode="Markdown"
                )
            else:
                await msg.edit_text("❌ Ошибка генерации. Попробуй позже.")
            
            await state.clear()
        
        # === ПОИСК ЧУВСТВИТЕЛЬНЫХ ДАННЫХ ===
        elif not current_state and "утечки" in message.text.lower():
            found = eye.extract_sensitive_data(message.text)
            
            report = "*🛡️ НАЙДЕННЫЕ ДАННЫЕ:*\n\n"
            
            if found:
                for data_type, items in found.items():
                    report += f"*{data_type.upper()}:*\n"
                    for item in items[:5]:
                        # Маскируем часть данных
                        masked = item[:3] + "***" + item[-2:] if len(item) > 5 else "***"
                        report += f"• `{masked}`\n"
                    report += "\n"
            else:
                report += "✅ Чувствительных данных не найдено."
            
            await message.answer(report, parse_mode="Markdown")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
