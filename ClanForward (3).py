__version__ = (1, 0, 3)

# ======================================================================
# Название модуля: [ClanForward]
# Версия: [1.0.3]
# Описание: [Модуль для перессылкиклановой афиши в бфг чатах.]
# Автор: Heroku_Guard
# Канал и контакты: @heroku_Guard, https://t.me/heroku_Guard
# Дата создания: [30.01.2026]
# ======================================================================
#
# Лицензия: MIT License
# Copyright (c) 2025 Heroku_Guard
#
# Для подробной информации о лицензии см. файл LICENSE:
# https://raw.githubusercontent.com/vbhhhgfddhy/Heroku_model/refs/heads/main/LICENSE
#
# Эта программа предоставляется "как есть", без каких-либо гарантий, явных
# или подразумеваемых, включая, но не ограничиваясь, гарантии товарной
# пригодности и пригодности для конкретной цели. В случае возникновения
# убытков или проблем с программой, авторы или владельцы авторских прав
# не несут ответственности.
# ======================================================================
# meta developer: @heroku_Guard

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from telethon.tl.types import Message
from .. import loader, utils

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))


@loader.tds
class ClanForwardMod(loader.Module):
    """
    модуль для пересылки афиши от heroku_guard
    """

    strings = {
        "name": "ClanForward",
        "enabled": "✅ <b>Модуль Clan включён</b>",
        "disabled": "⛔ <b>Модуль Clan выключен</b>",
        "no_reply": "❗ <b>Команду нужно использовать ответом на сообщение с афишей</b>",
        "saved": "📌 <b>Афиша сохранена и рассылка запущена</b>",
        "log_title": "📊 <b>Лог пересылки</b>\n\n",
        "log_empty": "Лог пуст.",
        "logs_cleared": "🗑 <b>Логи очищены</b>",
        "all_cleared": "🗑 <b>Все данные сброшены</b>",
    }

    config = loader.ModuleConfig(
        loader.ConfigValue(
            "interval1", 30,
            "КД для 1 чата (в минутах)",
            validator=loader.validators.Integer(minimum=1)
        ),
        loader.ConfigValue(
            "interval2", 30,
            "КД для 2 чата (в минутах)",
            validator=loader.validators.Integer(minimum=1)
        ),
        loader.ConfigValue("chat1", "https://t.me/bforgame_chat", "Чат №1"),
        loader.ConfigValue("chat2", "https://t.me/bforgame_chat_two", "Чат №2"),
    )

    def __init__(self):
        self.enabled = False
        self.tasks = {}
        self.running = set()

    async def client_ready(self, client, db):
        self.client = client
        self._db = db
        self.enabled = self.db_get("enabled", False)

        if self.enabled:
            await self.restore_tasks()

    # ================= DB =================

    def db_get(self, key, default=None):
        try:
            return self._db.get(self.name, key, default)
        except Exception:
            logger.exception("DB get error")
            return default

    def db_set(self, key, value):
        try:
            self._db.set(self.name, key, value)
        except Exception:
            logger.exception("DB set error")

    # ================= CORE =================

    async def forward_ad(self, idx: int):
        src_chat = self.db_get("forward_chat")
        msg_id = self.db_get("forward_msg")

        if not src_chat or not msg_id:
            return

        target = self.config[f"chat{idx}"]

        await self.client.forward_messages(
            entity=target,
            messages=msg_id,
            from_peer=src_chat
        )

        now = datetime.now(MSK).strftime("%d.%m.%Y %H:%M:%S")
        logs = self.db_get(f"logs_{idx}", [])
        logs.insert(0, f"Чат {idx} | {now}")
        self.db_set(f"logs_{idx}", logs[:20])
        self.db_set(f"last_sent_{idx}", datetime.now(timezone.utc).isoformat())

    async def send_loop(self, idx: int, delay: float):
        if idx in self.running:
            return

        self.running.add(idx)
        try:
            await asyncio.sleep(delay)

            while self.enabled:
                try:
                    await self.forward_ad(idx)
                except Exception:
                    logger.exception(f"Ошибка пересылки chat{idx}")

                await asyncio.sleep(self.config[f"interval{idx}"] * 60)

        except asyncio.CancelledError:
            pass
        finally:
            self.running.discard(idx)

    async def restore_tasks(self):
        now = datetime.now(timezone.utc)

        for idx in (1, 2):
            last = self.db_get(f"last_sent_{idx}")
            interval = self.config[f"interval{idx}"] * 60

            if last:
                last = datetime.fromisoformat(last)
                delay = max(0, interval - (now - last).total_seconds())
            else:
                delay = interval

            self.tasks[idx] = asyncio.create_task(
                self.send_loop(idx, delay)
            )

    # ================= COMMANDS =================

    async def clancmd(self, message: Message):
        '''Включает пересылку афиши (запуск через replay'''
        if self.enabled:
            self.enabled = False
            self.db_set("enabled", False)

            for task in self.tasks.values():
                task.cancel()
            self.tasks.clear()

            await utils.answer(message, self.strings["disabled"])
            return

        if not message.is_reply:
            await utils.answer(message, self.strings["no_reply"])
            return

        reply = await message.get_reply_message()

        self.db_set("forward_chat", reply.chat_id)
        self.db_set("forward_msg", reply.id)

        self.enabled = True
        self.db_set("enabled", True)

        await self.restore_tasks()
        await utils.answer(message, self.strings["saved"])

    async def logclancmd(self, message: Message):
        '''показывает логи афиши'''
        logs1 = self.db_get("logs_1", [])
        logs2 = self.db_get("logs_2", [])

        if not logs1 and not logs2:
            await utils.answer(message, self.strings["log_empty"])
            return

        text = self.strings["log_title"]

        if logs1:
            text += "<b>1 чат:</b>\n" + "\n".join(logs1) + "\n\n"
        if logs2:
            text += "<b>2 чат:</b>\n" + "\n".join(logs2)

        await utils.answer(message, text)

    async def uplogscmd(self, message: Message): 
        '''очищяет логи афиши'''
        self.db_set("logs_1", [])
        self.db_set("logs_2", [])
        await utils.answer(message, self.strings["logs_cleared"])

    async def nulliscmd(self, message: Message): 
        '''обнуляется запуск офиши и логи клана'''
        for k in (
            "enabled", "forward_chat", "forward_msg",
            "last_sent_1", "last_sent_2"
        ):
            self.db_set(k, None)

        self.db_set("logs_1", [])
        self.db_set("logs_2", [])

        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()

        await utils.answer(message, self.strings["all_cleared"])