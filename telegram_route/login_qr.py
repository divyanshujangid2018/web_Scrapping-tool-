"""Log in to Telegram by scanning a QR code (no login code needs to be typed or shared).

Writes telegram_route/login_qr.png and waits for you to scan it in the Telegram app:
Settings -> Devices -> Link Desktop Device. The QR refreshes every ~30s until scanned (max ~5 min).
If your account has two-step verification, run `python3 telegram_route/discover.py` in your own
terminal once instead (it asks for the password locally).

Usage:  python3 telegram_route/login_qr.py
"""
import asyncio
from pathlib import Path

import qrcode
from tg_client import get_client

PNG = Path(__file__).with_name("login_qr.png")


async def main():
    from telethon.errors import SessionPasswordNeededError
    client = get_client()
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Already logged in as {me.first_name}. Nothing to do.")
        await client.disconnect()
        return
    qr = await client.qr_login()
    for attempt in range(10):
        qrcode.make(qr.url).save(PNG)
        print(f"QR code written to {PNG} - scan it in Telegram: Settings > Devices > Link Desktop Device", flush=True)
        try:
            await qr.wait(timeout=30)
            break
        except asyncio.TimeoutError:
            await qr.recreate()
        except SessionPasswordNeededError:
            print("TWO_STEP_PASSWORD_NEEDED: run `python3 telegram_route/discover.py` in your own terminal once to enter it.")
            await client.disconnect()
            return
    else:
        print("QR not scanned in time - run again.")
        await client.disconnect()
        return
    me = await client.get_me()
    print(f"LOGIN_OK as {me.first_name} - session saved.")
    PNG.unlink(missing_ok=True)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
