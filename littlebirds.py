#!/usr/bin/env python3
import asyncio
import logging
logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

from os import environ

from getpass import getpass
from telethon import TelegramClient, events


class LBTelegramClient(TelegramClient):
    def __init__(self, session_user_id, api_id, api_hash, proxy=None):
        """
        Initializes the LBTelegramClient.
        Args:
            session_user_id::str
                Name of the *.session file.
            api_id::int
                Telegram's api_id acquired through my.telegram.org.
            api_hash::str
                Telegram's api_hash.
            proxy::tuple/dict
                proxy server (PySocks - https://github.com/Anorov/PySocks)
        """
        super().__init__(session_user_id, api_id, api_hash, proxy=proxy)

        logging.info('Connecting to Telegram servers...')
        self._message_queue = None

        try:
            loop.run_until_complete(self.connect())
        except ConnectionError:
            logging.warning('Initial connection failed. Retrying...')
            loop.run_until_complete(self.connect())

        if not loop.run_until_complete(self.is_user_authorized()):
            logging.info('First run. Sending code request...')
            user_phone = environ.get('TG_PHONE')
            if not user_phone:
                user_phone = input('Enter your phone (Format:"+1234567890"): ')
            loop.run_until_complete(self.sign_in(user_phone))

            self_user = None
            while self_user is None:
                code = input('Enter the code you just received: ')
                try:
                    self_user = loop.run_until_complete(self.sign_in(code=code))

                # Two-step verification may be enabled, and .sign_in will
                # raise this error. If that's the case ask for the password.
                except SessionPasswordNeededError:
                    pw = getpass('Two step verification is enabled. '
                                 'Please enter your password: ')

                    self_user =\
                        loop.run_until_complete(self.sign_in(password=pw))
        logging.info('Connected to Telegram servers.')

    async def set_message_queue(self, queue):
        self._message_queue = queue

    async def run(self):
        self.add_event_handler(self.update_handler)
        while True:
            await asyncio.sleep(5)

    async def update_handler(self, update):
        try:
            msg = update.message
        except AttributeError:
            return

        if msg.message is None or len(msg.message) == 0:
            return

        logging.info('enqueued: %s' % msg.message)
        if self._message_queue != None:
            await self._message_queue.put(msg.message)


async def pull_from_queue(queue):
    while True:
        msg = await queue.get()
        logging.info('dequeued: %s' % msg)
        await asyncio.sleep(5)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    queue = asyncio.Queue(loop=loop)

    client = LBTelegramClient(
        environ.get('TG_SESSION', 'session'),
        int(environ['TG_API_ID']),
        environ['TG_API_HASH'],
        proxy=None
    )
    loop.run_until_complete(client.set_message_queue(queue))
    consumer = pull_from_queue(queue)

    loop.run_until_complete(asyncio.gather(client.run(), consumer))
