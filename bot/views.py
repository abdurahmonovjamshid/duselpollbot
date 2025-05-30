import json
import traceback
import telebot

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from conf.settings import HOST, TELEGRAM_BOT_TOKEN, ADMINS, CHANNELS
from .models import Poll, PollOption, PollVote, TgUser

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)


@csrf_exempt
def telegram_webhook(request):
    try:
        if request.method == 'POST':
            update_data = request.body.decode('utf-8')
            update_json = json.loads(update_data)
            update = telebot.types.Update.de_json(update_json)

            if update.message:
                tg_user = update.message.from_user
                telegram_id = tg_user.id
                first_name = tg_user.first_name
                last_name = tg_user.last_name
                username = tg_user.username
                is_bot = tg_user.is_bot
                language_code = tg_user.language_code

                deleted = False

                tg_user_instance, _ = TgUser.objects.update_or_create(
                    telegram_id=telegram_id,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'username': username,
                        'is_bot': is_bot,
                        'language_code': language_code,
                        'deleted': deleted,
                    }
                )

            try:
                if update.my_chat_member.new_chat_member.status == 'kicked':
                    telegram_id = update.my_chat_member.from_user.id
                    user = TgUser.objects.get(telegram_id=telegram_id)
                    user.deleted = True
                    user.save()
            except:
                pass

            bot.process_new_updates(
                [telebot.types.Update.de_json(request.body.decode("utf-8"))])

        return HttpResponse("ok")
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        return HttpResponse("error")


@bot.message_handler(commands=['start'])
def start_handler(message):
    try:
        response_message = f"Salom, {message.from_user.full_name}!"

        if message.chat.type == 'private':
            # Send welcome message in private
            bot.send_photo(
                chat_id=message.chat.id,
                photo='https://daryo.uz/static/2023/12/29/photo_2023-12-27_15-10-45.jpg',
                caption=response_message
            )
        else:
            # Send to group: mention user and group name
            group_message = (
                f"👤 User: {message.from_user.full_name} (ID: {message.from_user.id})\n"
                f"💬 Guruh: {message.chat.title} (ID: {message.chat.id})"
            )
            bot.send_message(chat_id=message.chat.id, text=group_message)
    except Exception as e:
        print("⚠️ Error in /start handler:")
        print(e)


def send_polls_to_channels():
    from .models import Poll

    polls = Poll.objects.all()  # example: first 2 polls

    for channel_id in CHANNELS:
        for poll in polls:
            markup = telebot.types.InlineKeyboardMarkup()
            for option in poll.options.all():
                callback_data = f"vote:{poll.id}:{option.id}"
                markup.add(telebot.types.InlineKeyboardButton(text=option.text, callback_data=callback_data))

            bot.send_message(
                chat_id=channel_id,
                text=f"📊 {poll.question}",
                reply_markup=markup
            )


@bot.message_handler(commands=['send_poll'])
def send_poll_command(message):
    if message.from_user.id not in ADMINS:
        return bot.send_message(message.chat.id, "Faqat adminlar yubora oladi.")
    send_polls_to_channels()
    bot.send_message(message.chat.id, "So'rovnoma kanalga yuborildi.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("vote:"))
def handle_vote(call):
    try:
        _, poll_id, option_id = call.data.split(":")
        user = call.from_user
        telegram_id = user.id
        chat_id = call.message.chat.id

        # Ensure user is saved
        tg_user, _ = TgUser.objects.update_or_create(
            telegram_id=telegram_id,
            defaults={
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'is_bot': user.is_bot,
                'deleted': False,
            }
        )

        poll = Poll.objects.get(id=poll_id)
        option = PollOption.objects.get(id=option_id, poll=poll)

        existing_vote = PollVote.objects.filter(
            poll=poll, option=option, telegram_id=telegram_id
        ).first()

        if existing_vote:
            bot.answer_callback_query(call.id, "Siz bu variantga allaqachon ovoz bergansiz.")
        else:
            try:
                chat_info = bot.get_chat(chat_id)
                channel_title = chat_info.title or ""
            except Exception:
                channel_title = ""

            PollVote.objects.create(
                poll=poll,
                option=option,
                telegram_id=telegram_id,
                user=tg_user,
                chat_id=chat_id,
                channel_title=channel_title
            )
            bot.answer_callback_query(call.id, "Ovoz qabul qilindi ✅")

    except Exception as e:
        print("Vote error:", e)
        bot.answer_callback_query(call.id, "Xatolik yuz berdi.")


@bot.message_handler(commands=['results'])
def show_results(message):
    if message.from_user.id not in ADMINS:
        return bot.send_message(message.chat.id, "Bu buyruq faqat adminlar uchun.")

    from .models import Poll
    response = ""

    for poll in Poll.objects.all()[:2]:
        response += f"📊 {poll.question}\n"
        for option in poll.options.all():
            count = option.pollvote_set.count()  # counts votes from ALL channels combined
            response += f" - {option.text}: {count} ta ovoz\n"
        response += "\n"

    bot.send_message(message.chat.id, response or "Hozircha hech qanday natija yo‘q.")


bot.set_webhook(url="https://" + HOST + "/webhook/")
