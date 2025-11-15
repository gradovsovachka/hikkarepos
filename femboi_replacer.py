# -*- coding: utf-8 -*-
# femboi_soft_protect.py
# Автор: femboy://kiwser

from .. import loader, utils
import os
import re

@loader.tds
class FemboiSoftProtectMod(loader.Module):
    """Мягкие замены с защитой: нельзя менять системные файлы."""
    strings = {"name": "femboi_soft_protect"}

    def __init__(self):
        # что заменяем
        self.patterns = [
            (r"hikka", "femboi"),
            (r"Hikka", "Femboi"),
            (r"HIKKA", "FEMBOI"),
        ]

        # расширения для работы
        self.exts = (".py", ".txt", ".md", ".json")

        # ЗАПРЕЩЁННЫЕ директории (их никогда нельзя трогать)
        self.forbidden = [
            "hikka",      # корень Хикки
            "core",
            "loader",
            "web",
            "modules",    # системные, НЕ userbot/modules
            "utils",
            "api",
        ]

    def _is_forbidden(self, path: str):
        p = path.lower().replace("\\", "/")
        for f in self.forbidden:
            if f"/{f.lower()}" in p or p.endswith(f"/{f.lower()}"):
                return True
        return False

    def _scan_files(self, root):
        for dp, _, files in os.walk(root):
            if self._is_forbidden(dp):
                continue
            for f in files:
                if f.lower().endswith(self.exts):
                    yield os.path.join(dp, f)

    async def softpreviewcmd(self, m):
        """-softpreview <путь> — показать заменяемые файлы (с защитой)"""
        args = utils.get_args_raw(m).strip()
        if not args:
            return await utils.answer(m, "укажи путь, солнышко 💗")

        root = os.path.abspath(args)
        if not os.path.isdir(root):
            return await utils.answer(m, "это не папочка, мой хороший…")

        if self._is_forbidden(root):
            return await utils.answer(m, "нельзя трогать системные файлы… я не дам тебе сломать бота 🩵")

        out = "🔍 Предпросмотр безопасных замен:\n\n"
        count = 0

        for file in self._scan_files(root):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    txt = f.read()
            except:
                continue

            changes = 0
            for patt, _ in self.patterns:
                changes += len(re.findall(patt, txt, flags=re.IGNORECASE))

            if changes > 0:
                count += 1
                out += f"• {file} — {changes} возможных замен\n"

        if count == 0:
            out += "ничего не найдено 🌸"
        await utils.answer(m, out)

    async def softapplycmd(self, m):
        """-softapply <путь> — безопасное применение замен"""
        args = utils.get_args_raw(m).strip()
        if not args:
            return await utils.answer(m, "скажи мне путь, милый 💗")

        root = os.path.abspath(args)
        if not os.path.isdir(root):
            return await utils.answer(m, "это не папка, солнышко…")

        if self._is_forbidden(root):
            return await utils.answer(m, "мур… туда нельзя… ты можешь сломать бота, а я тебя берегу 🩵")

        changed = 0

        for file in self._scan_files(root):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    txt = f.read()
            except:
                continue

            new = txt
            for patt, repl in self.patterns:
                new = re.sub(patt, repl, new, flags=re.IGNORECASE)

            if new != txt:
                changed += 1
                try:
                    with open(file, "w", encoding="utf-8") as f:
                        f.write(new)
                except:
                    continue

        await utils.answer(m, f"✨ мягко и безопасно заменено в {changed} файлах ✨")
