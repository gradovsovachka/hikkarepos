# -*- coding: utf-8 -*-
# femboi_aura_ultra_mega.py
# Автор: femboy://kiwser
# Полный фембой-модуль: уровни, ауры, магазин, предметы, питомцы, подарки
# Все команды начинаются с "-"

from .. import loader, utils
import json, os, time, random


@loader.tds
class FemboiAuraUltraMegaMod(loader.Module):
    strings = {"name": "femboi_aura_ultra_mega"}

    # ---------------- DB ----------------

    def __init__(self):
        self.file = "femboy_mega.json"
        self.db = self.load_db()

        # aura эффекты
        self.effects = {
            "blossom": "🌸",
            "star": "✧",
            "love": "💗",
            "pastel": "🩵",
            "sparkle": "✨",
            "butterfly": "🦋",
            "pinkburst": "💞",
        }

        # питомцы + множители exp
        self.pets = {
            "catboy": {"emoji": "🐾", "x": 1.2},
            "fairyboy": {"emoji": "🦋", "x": 1.4},
            "foxboy": {"emoji": "🦊", "x": 1.6},
            "angel": {"emoji": "✨", "x": 2.0},
        }

        # предметы магазина
        self.items = {
            "candy": {"price": 150, "exp": 200, "emoji": "🍬"},
            "perfume": {"price": 500, "exp": 700, "emoji": "🌸"},
            "love": {"price": 1200, "exp": 2000, "emoji": "💗"},
            "elixir": {"price": 5000, "exp": 7000, "emoji": "✨"},
        }

    def load_db(self):
        if not os.path.exists(self.file):
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            return {}
        try:
            with open(self.file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def save_db(self):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.db, f, ensure_ascii=False, indent=4)

    # ---------------- CORE ----------------

    def user(self, uid):
        uid = str(uid)
        if uid not in self.db:
            self.db[uid] = {
                "exp": 0,
                "sc": 0,
                "effect": None,
                "pet": None,
                "items": {},
                "last_daily": 0,
            }
            self.save_db()
        return uid

    def lvl_from_exp(self, exp):
        lvl = int(exp ** 0.45)
        return min(lvl, 5_000_000)

    def exp_gain(self, uid, base):
        uid = self.user(uid)
        mlt = 1.0
        pet = self.db[uid]["pet"]
        if pet and pet in self.pets:
            mlt = self.pets[pet]["x"]
        gain = int(base * mlt)
        self.db[uid]["exp"] += gain
        self.save_db()
        return gain

    def rank(self, lvl):
        if lvl < 100:
            return "soft kitten"
        if lvl < 1000:
            return "sweet femboy"
        if lvl < 10000:
            return "pink pride"
        if lvl < 100000:
            return "ultra cute"
        if lvl < 1000000:
            return "angelic femboy"
        return "divine femboy deity ✧"

    # ---------------- COMMANDS ----------------

    async def kawaiicmd(self, m):
        """-kawaii — получить exp"""
        uid = self.user(m.from_id)
        gained = self.exp_gain(uid, 20)

        msg = random.choice([
            "૮₍｡´• ˕ •`｡₎ა *скромно улыбается*",
            "(*≧▽≦) хочу быть милее…",
            "🩷 сияю для тебя, нyaa",
            "(˶ᵔ ᵕ ᵔ˶) обними меня…",
            "🌸 твой фембой становится сильнее…"
        ])

        await utils.answer(m, f"{msg}\n\n+<b>{gained}</b> exp")

    async def profilecmd(self, m):
        """-profile — профиль"""
        uid = self.user(m.from_id)
        u = self.db[uid]

        lvl = self.lvl_from_exp(u["exp"])
        rank = self.rank(lvl)
        effect = self.effects.get(u["effect"], "нет")
        pet = u["pet"]
        pet_emoji = self.pets[pet]["emoji"] if pet else "нет"

        await utils.answer(
            m,
            f"<b>Femboy Profile</b>\n"
            f"Уровень: <b>{lvl:,}</b>\n"
            f"Опыт: <b>{u['exp']:,}</b>\n"
            f"Ранг: <i>{rank}</i>\n"
            f"Аура: {effect}\n"
            f"Питомец: {pet_emoji}\n"
            f"SoftCoins: <b>{u['sc']}</b>"
        )

    async def auracmd(self, m):
        """-aura — список эффектов"""
        txt = "Доступные эффекты:\n"
        for k, v in self.effects.items():
            txt += f"{k} — {v}\n"
        await utils.answer(m, txt)

    async def setaura_cmd(self, m):
        """-setaura <название>"""
        arg = utils.get_args_raw(m).lower()
        if not arg:
            return await utils.answer(m, "Укажи эффект.")

        if arg not in self.effects:
            return await utils.answer(m, "Нет такого эффекта.")

        uid = self.user(m.from_id)
        self.db[uid]["effect"] = arg
        self.save_db()

        await utils.answer(m, f"Аура установлена: {self.effects[arg]}")

    setaura = setaura_cmd

    # ---------------- DAILY ----------------

    async def dailycmd(self, m):
        """-daily — ежедневный бонус"""
        uid = self.user(m.from_id)
        now = int(time.time())
        last = self.db[uid]["last_daily"]

        if now - last < 86400:
            left = int((86400 - (now - last)) / 3600)
            return await utils.answer(m, f"Уже получал! Осталось: <b>{left} ч</b>")

        self.db[uid]["last_daily"] = now
        self.db[uid]["sc"] += 300
        exp = self.exp_gain(uid, 250)
        self.save_db()

        await utils.answer(m, f"🌸 Ежедневка!\n+300 SC\n+{exp} exp")

    # ---------------- SHOP ----------------

    async def shopcmd(self, m):
        """-shop — магазин"""
        txt = "<b>Магазин</b>\n"
        for k, v in self.items.items():
            txt += f"{v['emoji']} <b>{k}</b>: {v['price']} SC → +{v['exp']} exp\n"
        await utils.answer(m, txt)

    async def buycmd(self, m):
        """-buy <item>"""
        arg = utils.get_args_raw(m).lower()
        if arg not in self.items:
            return await utils.answer(m, "Такого предмета нет.")

        uid = self.user(m.from_id)
        it = self.items[arg]

        if self.db[uid]["sc"] < it["price"]:
            return await utils.answer(m, "Не хватает SC!")

        self.db[uid]["sc"] -= it["price"]
        self.db[uid]["items"].setdefault(arg, 0)
        self.db[uid]["items"][arg] += 1
        self.save_db()

        await utils.answer(m, f"Куплено: {it['emoji']} <b>{arg}</b>")

    async def usecmd(self, m):
        """-use <item>"""
        arg = utils.get_args_raw(m).lower()
        uid = self.user(m.from_id)

        if arg not in self.db[uid]["items"]:
            return await utils.answer(m, "У тебя нет этого предмета.")

        if self.db[uid]["items"][arg] <= 0:
            return await utils.answer(m, "Предметов нет.")

        it = self.items[arg]
        self.db[uid]["items"][arg] -= 1
        gained = self.exp_gain(uid, it["exp"])
        self.save_db()

        await utils.answer(m, f"Использовано {it['emoji']} +{gained} exp")

    # ---------------- PETS ----------------

    async def petcmd(self, m):
        """-pet <имя> — выбрать питомца"""
        arg = utils.get_args_raw(m).lower()
        if not arg:
            txt = "Питомцы:\n"
            for k, v in self.pets.items():
                txt += f"{v['emoji']} {k} — x{v['x']} exp\n"
            return await utils.answer(m, txt)

        if arg not in self.pets:
            return await utils.answer(m, "Нет такого питомца.")

        uid = self.user(m.from_id)
        self.db[uid]["pet"] = arg
        self.save_db()

        await utils.answer(m, f"Теперь твой питомец: {self.pets[arg]['emoji']} {arg}")

    # ---------------- GIFTS ----------------

    async def giftcmd(self, m):
        """-gift <reply> <SC> — отправить монеты"""
        if not m.is_reply:
            return await utils.answer(m, "Ответь на сообщение пользователя.")

        args = utils.get_args_raw(m).split()
        if not args or not args[0].isdigit():
            return await utils.answer(m, "Укажи число SC.")

        amount = int(args[0])
        from_uid = self.user(m.from_id)
        to_uid = self.user(m.reply_to_msg_id or m.reply_message.from_id)

        if amount <= 0:
            return await utils.answer(m, "Нельзя отправлять 0 или меньше.")

        if self.db[from_uid]["sc"] < amount:
            return await utils.answer(m, "Недостаточно SC!")

        self.db[from_uid]["sc"] -= amount
        self.db[to_uid]["sc"] += amount
        self.save_db()

        await utils.answer(m, f"🎁 Подарено {amount} SC!")
