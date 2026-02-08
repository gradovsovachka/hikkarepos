# meta developer: @yourname

from .. import loader, utils

@loader.tds
class RestartOkMod(loader.Module):
    """Модуль с фейковым restart"""

    strings = {"name": "RestartOk"}

    async def restartcmd(self, message):
        await utils.answer(message, "ok")
