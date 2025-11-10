# -*- coding: utf-8 -*-
"""SpyTopicsMod — логирует edits/deletes в отдельную лог-группу + темы (topics).
Файл конфигурации: spybotlele.json (в той же папке модуля).
"""
from .. import loader, utils
from telethon import events, errors
from telethon.tl.functions.channels import CreateChannelRequest, GetAdminLogRequest
from telethon.tl.functions.messages import CreateForumTopicRequest
from telethon.tl.types import ChannelParticipantsAdmins
import asyncio, random, json, os, time, traceback

@loader.tds
class SpyTopicsMod(loader.Module):
    """SpyTopicsMod — создает лог-группу (если нужно), создает темы и логирует правки/удаления."""
    strings = {
        "name": "SpyTopics",
        "started": "SpyTopics загружен.",
        "no_log_chat": "Log chat not set and creation failed. Используйте .spyset <id>.",
        "created_log_chat": "Создал лог-группу: {title} ({id})",
        "topic_created": "Создал тему: {topic} (id {tid})",
        "logged_edit": "Лог записи в тему {topic}",
        "logged_delete": "Лог удаления в тему {topic}",
        "help": (
            ".spyset <id> — задать ID лог-группы вручную\n"
            ".spyinit — попытаться создать приватную лог-группу сейчас\n"
            ".spystatus — показать текущие настройки\n"
            ".spyclear — очистить внутренние кэши (topics/cache)\n"
        )
    }

    CONFIG_FILE = "spybotlele.json"
    MAX_CACHE_PER_CHAT = 1000
    MAX_TOPIC_NAME_LEN = 120

    def __init__(self):
        self._cache = {}  # {(chat_id, msg_id): {"text":..., "sender_id":..., "date":...}}
        self._topics = {} # { "изменения - <chat_title>": topic_id, "удаление - <chat_title>": topic_id }
        self.config = {}
        super().__init__()

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        # load config file (module directory)
        self.mod_dir = os.path.dirname(__file__)
        self.cfg_path = os.path.join(self.mod_dir, self.CONFIG_FILE)
        await self._load_config()
        # handlers
        client.add_event_handler(self._on_new_message, events.NewMessage(incoming=True))
        client.add_event_handler(self._on_edit, events.MessageEdited())
        client.add_event_handler(self._on_delete, events.MessageDeleted())
        return

    async def _load_config(self):
        try:
            if os.path.exists(self.cfg_path):
                with open(self.cfg_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                self.config = {}
            # ensure keys
            if "log_chat_id" not in self.config:
                self.config["log_chat_id"] = None
            if "topics" not in self.config:
                self.config["topics"] = {}
            # write back minimal file
            with open(self.cfg_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception:
            self.config = {"log_chat_id": None, "topics": {}}
            try:
                with open(self.cfg_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
            except:
                pass

    async def _save_config(self):
        try:
            with open(self.cfg_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    async def _ensure_log_chat(self):
        """Если log_chat_id нет — попытаться создать приватную супергруппу и сохранить её."""
        if self.config.get("log_chat_id"):
            return self.config["log_chat_id"]
        # попытка создать приватную супергруппу (канал-мегагруппа)
        try:
            title = f"spy-log-{int(time.time())}"
            about = "Лог группа для SpyTopicsMod. Приватная."
            res = await self.client(CreateChannelRequest(title=title, about=about, megagroup=True))
            # CreateChannelRequest возвращает объект с channgel/updates; получить id
            # Telethon возвращает result.chats[0] часто; safer: поиск по title
            # Попробуем найти созданную группу среди dialogs
            async for d in self.client.iter_dialogs():
                if getattr(d.entity, "title", None) == title:
                    chat_id = d.entity.id
                    self.config["log_chat_id"] = chat_id
                    await self._save_config()
                    # no immediate topic creation here
                    return chat_id
        except Exception as e:
            # если создание не удалось — просто вернуть None
            return None

    async def _ensure_topic(self, chat_title, kind):
        """
        Возвращает topic_id для темы kind ("изменения" или "удаление") + чат_title.
        Создает тему если нужно.
        """
        if not chat_title:
            chat_title = "chat"
        name = f"{kind} - {chat_title}"
        # trim
        if len(name) > self.MAX_TOPIC_NAME_LEN:
            name = name[:self.MAX_TOPIC_NAME_LEN]
        # check cache
        tid = self.config.get("topics", {}).get(name)
        if tid:
            return tid, name
        # create topic in log_chat
        log_id = self.config.get("log_chat_id")
        if not log_id:
            return None, name
        try:
            # CreateForumTopicRequest для создания темы (новые версии API)
            # title must be str
            resp = await self.client(CreateForumTopicRequest(peer=log_id, topic= name))
            # resp possibly contains 'topic' with 'id'
            # Telethon returns object with topics list; try to read id
            topic_id = None
            if hasattr(resp, "topics") and resp.topics:
                # last created likely at end
                topic_id = resp.topics[-1].id
            elif hasattr(resp, "topic") and hasattr(resp.topic, "id"):
                topic_id = resp.topic.id
            # store
            if topic_id is not None:
                self.config.setdefault("topics", {})[name] = topic_id
                await self._save_config()
                return topic_id, name
        except errors.rpcerrorlist.FloodWaitError as e:
            # если flood — запомним None и пропустим
            return None, name
        except Exception:
            # возможно метод не поддерживается на старой версии Telethon/клиента
            # попытаемся отправлять сообщения в обычную ленту без темы
            return None, name
        return None, name

    async def _log_to_topic(self, topic_id, text, log_id):
        """Отправить сообщение в тему topic_id лог-группы. Если topic_id None — отправить в чат (без темы)."""
        try:
            if topic_id:
                # send_message с указанием topic
                await self.client.send_message(log_id, text, topic=topic_id)
            else:
                await self.client.send_message(log_id, text)
            return True
        except Exception:
            # пробуем без topic
            try:
                await self.client.send_message(log_id, text)
                return True
            except Exception:
                return False

    async def _cache_message(self, event):
        """Сохраняет текст и метаданные новых сообщений в кэше."""
        try:
            chat = await event.get_chat()
            chat_id = getattr(chat, "id", event.chat_id)
            mid = event.message.id
            text = event.message.message or ""
            sender = getattr(event.message.from_id, "user_id", None) or getattr(event.message, "sender_id", None)
            date = getattr(event.message, "date", None)
            key = (chat_id, mid)
            self._cache[key] = {"text": text, "sender": sender, "date": date}
            # trim per chat
            # count keys per chat
            keys = [k for k in self._cache.keys() if k[0] == chat_id]
            if len(keys) > self.MAX_CACHE_PER_CHAT:
                # remove oldest
                sorted_keys = sorted(keys, key=lambda k: self._cache[k].get("date") or 0)
                for k in sorted_keys[: len(keys) - self.MAX_CACHE_PER_CHAT]:
                    self._cache.pop(k, None)
        except Exception:
            pass

    async def _on_new_message(self, event):
        # store new messages so edits/deletes have original
        try:
            await self._cache_message(event)
        except Exception:
            pass

    async def _on_edit(self, event):
        try:
            # event.message is new message
            chat = await event.get_chat()
            chat_id = getattr(chat, "id", event.chat_id)
            chat_title = getattr(chat, "title", str(chat_id))
            mid = event.message.id
            key = (chat_id, mid)
            old = self._cache.get(key, {}).get("text", "<не было в кэше>")
            new = event.message.message or ""
            user = getattr(event.message.from_id, "user_id", None) or getattr(event.message, "sender_id", None)
            user_str = f"user_id={user}"
            when = getattr(event.message, "date", None)
            # build text
            txt = (
                f"Изменение в чате: {chat_title}\n"
                f"Сообщение ID: {mid}\n"
                f"Автор: {user_str}\n"
                f"Время: {when}\n\n"
                f"Старый текст:\n{old}\n\n"
                f"Новый текст:\n{new}"
            )
            # ensure topic
            log_id = await self._ensure_log_chat()
            if not log_id:
                return
            tid, topic_name = await self._ensure_topic(chat_title, "изменения")
            await self._log_to_topic(tid, txt, log_id)
            # update cache with new
            self._cache[key] = {"text": new, "sender": user, "date": when}
        except Exception:
            # swallow but log to self.client if possible
            try:
                await self.client.send_message(await self.client.get_me(), "SpyTopics edit handler error:\n" + traceback.format_exc())
            except:
                pass

    async def _on_delete(self, event):
        """Лог удалённых сообщений. event.deleted_ids содержит id-ы"""
        try:
            # event.chat_id available
            chat_id = event.chat_id
            # chat title best-effort
            try:
                chat = await self.client.get_entity(chat_id)
                chat_title = getattr(chat, "title", str(chat_id))
            except Exception:
                chat_title = str(chat_id)
            log_id = await self._ensure_log_chat()
            if not log_id:
                return
            entries = []
            for mid in event.deleted_ids:
                key = (chat_id, mid)
                cached = self._cache.get(key)
                text = cached.get("text") if cached else "<нет текста в кэше>"
                sender = cached.get("sender") if cached else None
                date = cached.get("date") if cached else None
                # попытка определить кто удалил — через админ лог (только если чат — канал/супергруппа)
                deleter_str = "неизвестно"
                try:
                    # GetAdminLogRequest может вернуть события удаления; попробуем последние 30 записей
                    # Требует права просматривать админ-лог.
                    admin_resp = await self.client(GetAdminLogRequest(channel=chat_id, q=None, limit=50, events_filter=None))
                    # admin_resp.events — проанализировать, найти recent MessageDeletedEvent с msg_id
                    if hasattr(admin_resp, "events") and admin_resp.events:
                        for ev in admin_resp.events:
                            # ev may have action with deleted message ids
                            # тяжело универсализировать — используем str search
                            s = str(ev)
                            if str(mid) in s and "Message" in s:
                                deleter_str = str(ev)
                                break
                except Exception:
                    # игнорируем ошибки (нет прав и т.п.)
                    pass

                entry = {
                    "msg_id": mid,
                    "sender": sender,
                    "date": str(date),
                    "text": text,
                    "deleter": deleter_str
                }
                entries.append(entry)
                # remove from cache
                self._cache.pop(key, None)

            # формируем текст для логов
            txt_lines = [f"Удаление в чате: {chat_title}\nКоличество удалённых: {len(entries)}\n"]
            for e in entries:
                txt_lines.append(
                    f"Сообщение ID: {e['msg_id']}\n"
                    f"Автор: {e['sender']}\n"
                    f"Время: {e['date']}\n"
                    f"Кто удалил: {e['deleter']}\n"
                    f"Текст:\n{e['text']}\n"
                    "-----\n"
                )
            txt = "\n".join(txt_lines)
            tid, topic_name = await self._ensure_topic(chat_title, "удаление")
            await self._log_to_topic(tid, txt, log_id)
        except Exception:
            try:
                await self.client.send_message(await self.client.get_me(), "SpyTopics delete handler error:\n" + traceback.format_exc())
            except:
                pass

    # ------- user commands -------
    async def spysetcmd(self, message):
        """.spyset <id|@username> — вручную задать лог-группу."""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Требуется ID или @username лог-группы.")
            return
        try:
            target = args.strip()
            entity = await self.client.get_entity(target)
            self.config["log_chat_id"] = entity.id
            await self._save_config()
            await utils.answer(message, f"Лог-группа установлена: {getattr(entity, 'title', entity.id)} ({entity.id})")
        except Exception as e:
            await utils.answer(message, "Ошибка при установке: " + str(e))

    async def spyinitcmd(self, message):
        """.spyinit — попытаться создать приватную лог-группу и сохранить её."""
        await utils.answer(message, "Пытаюсь создать лог-группу...")
        cid = await self._ensure_log_chat()
        if cid:
            try:
                ent = await self.client.get_entity(cid)
                await utils.answer(message, self.strings["created_log_chat"].format(title=getattr(ent, "title", cid), id=cid))
            except:
                await utils.answer(message, f"Лог-группа создана: {cid}")
        else:
            await utils.answer(message, self.strings["no_log_chat"])

    async def spystatuscmd(self, message):
        """.spystatus — показать текущую конфигурацию."""
        log_id = self.config.get("log_chat_id")
        topics = self.config.get("topics", {})
        txt = f"Log chat id: {log_id}\nTopics stored: {len(topics)}\n"
        # show few topics
        for k, v in list(topics.items())[:20]:
            txt += f"{k} -> {v}\n"
        await utils.answer(message, txt)

    async def spyclearcmd(self, message):
        """.spyclear — очистить внутренние кэши и topics (в config)."""
        self._cache.clear()
        self.config["topics"] = {}
        await self._save_config()
        await utils.answer(message, "Кэши и topics очищены.")
