import json, asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Use environment variable for token
TOKEN = os.getenv("BOT_TOKEN", "8373893020:AAFMidK_4Ey7t30rhIXpWA-N0R5Tnyo0Qzo")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

with open("questions.json", "r", encoding="utf-8") as f:
    groups = json.load(f)

user_state = {}
user_results = {}
user_timers = {}  # Store timer tasks

@dp.message_handler(commands=["start"])
async def start_quiz(message: types.Message):
    user_id = message.from_user.id
    await cancel_timer(user_id)  # Cancel any existing timer
    user_state.pop(user_id, None)
    user_results.pop(user_id, None)
    await message.answer("Salom! 👋 Qaysi guruhni tanlaysiz?\n(1–7)")

@dp.message_handler(commands=["stop"])
async def stop_quiz(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_state:
        await message.answer("❌ Hozirda faol test yo'q!")
        return

    await cancel_timer(user_id)  # Cancel the timer
    results = user_results.get(user_id, {"correct": 0, "total": 0})
    await message.answer(
        f"📊 Test to'xtatildi!\n\n"
        f"✅ To'g'ri javoblar: {results['correct']}\n"
        f"❌ Noto'g'ri javoblar: {results['total'] - results['correct']}\n"
        f"📝 Jami ishlangan: {results['total']}"
    )
    
    # Clear user data
    cleanup_user_data(user_id)

@dp.message_handler(lambda m: m.text.isdigit() and 1 <= int(m.text) <= 7)
async def start_group(message: types.Message):
    user_id = message.from_user.id
    group_num = int(message.text) - 1
    
    # Initialize user state and results
    user_state[user_id] = {"group": group_num, "index": 0}
    user_results[user_id] = {"correct": 0, "total": 0}
    
    # Start the quiz
    await send_question(message.chat.id, user_id)

async def cancel_timer(user_id):
    if user_id in user_timers:
        timer = user_timers.pop(user_id)
        timer.cancel()
        try:
            await timer
        except asyncio.CancelledError:
            pass

def cleanup_user_data(user_id):
    user_state.pop(user_id, None)
    user_results.pop(user_id, None)
    user_timers.pop(user_id, None)

async def question_timer(chat_id, user_id, current_idx):
    await asyncio.sleep(30)
    if user_id in user_state and user_state[user_id]["index"] == current_idx:
        user_state[user_id]["index"] += 1
        await send_question(chat_id, user_id)

async def send_question(chat_id, user_id):
    if user_id not in user_state:
        return
        
    state = user_state[user_id]
    group = groups[state["group"]]
    idx = state["index"]

    if idx >= len(group):
        results = user_results[user_id]
        await bot.send_message(
            chat_id,
            f"✅ Test yakunlandi!\n\n"
            f"📊 Natijangiz:\n"
            f"✅ To'g'ri javoblar: {results['correct']}\n"
            f"❌ Noto'g'ri javoblar: {results['total'] - results['correct']}\n"
            f"📝 Jami ishlangan: {results['total']}"
        )
        cleanup_user_data(user_id)
        return

    try:
        q = group[idx]
        buttons = [[types.InlineKeyboardButton(text=opt, callback_data=str(i))] 
                  for i, opt in enumerate(q["options"])]
        markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)

        await bot.send_message(
            chat_id, 
            f"❓ {idx+1}-savol\n\n{q['question']}", 
            reply_markup=markup
        )

        # Start new timer
        timer = asyncio.create_task(question_timer(chat_id, user_id, idx))
        await cancel_timer(user_id)  # Cancel previous timer if exists
        user_timers[user_id] = timer
        
    except Exception as e:
        await bot.send_message(
            chat_id,
            "❌ Xatolik yuz berdi. /start buyrug'ini qayta bosing."
        )
        cleanup_user_data(user_id)

@dp.callback_query_handler(lambda c: c.data.isdigit())
async def handle_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_state:
        await callback.answer("Test yakunlangan!")
        return

    await cancel_timer(user_id)  # Cancel the timer when answer is received

    state = user_state[user_id]
    group = groups[state["group"]]
    idx = state["index"]
    q = group[idx]

    chosen = int(callback.data)
    user_results[user_id]["total"] += 1
    
    if chosen == q["correct"]:
        text = "✅ To'g'ri!"
        user_results[user_id]["correct"] += 1
    else:
        text = f"❌ Noto'g'ri! To'g'ri javob: {q['options'][q['correct']]}"

    await callback.message.edit_text(f"{q['question']}\n\n{text}")

    user_state[user_id]["index"] += 1
    await send_question(callback.message.chat.id, user_id)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
