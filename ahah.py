# meta developer: @your_username
# meta name: LapokuCuteInfo

from .. import loader, utils
import time

__version__ = (1, 0, 0, 5)

start_time = time.time()


@loader.tds
class LapokuCuteInfo(loader.Module):
    """Super cute femboy info"""

    strings = {
        "name": "LapokuCuteInfo",
    }

    def get_uptime(self):
        uptime = int(time.time() - start_time)
        h = uptime // 3600
        m = (uptime % 3600) // 60
        s = uptime % 60
        return f"{h:02}:{m:02}:{s:02}"

    async def watcher(self, message):
        if not message.out:
            return

        if message.raw_text.strip() == ".info":
            await message.delete()

            start = time.perf_counter()
            me = await self._client.get_me()
            ping = round((time.perf_counter() - start) * 1000, 2)

            text = (
                "<b>୨୧ ⋆｡˚ 💖 𝓛𝓪𝓹𝓸𝓴𝓾 💖 ˚｡⋆ ୨୧</b>\n"
                "♡ <b>owner</b>: <code>{owner}</code> 🧸\n"
                "♡ <b>ping</b>: <code>{ping} ms</code> ⚡\n"
                "♡ <b>status</b>: online & super cute ✨\n"
                "♡ <b>core</b>: Lapoku 🎀\n"
                "♡ <b>vibe</b>: soft pink energy 💞\n"
                "♡ <b>mood</b>: (≧◡≦) ♡\n"
                "♡ <b>hug level</b>: 100% 🫂💗\n"
                "<b>୨୧ ⋆｡˚ 🍼 stay adorable 🍼 ˚｡⋆ ୨୧</b>"
            ).format(
                owner=me.first_name,
                ping=ping,
                uptime=self.get_uptime()
            )

            await message.respond(
                message=text
            )
