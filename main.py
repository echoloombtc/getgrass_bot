# -*- coding: utf-8 -*-
# @Time     :2023/12/26 17:00
# @Author   :ym
# @File     :main.py
# @Software :PyCharm
import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
import aiohttp
import aiohttp_socks


async def check_proxy(proxy_url):
    try:
        connector = aiohttp_socks.ProxyConnector.from_url(proxy_url)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get('http://httpbin.org/ip', timeout=10) as response:
                if response.status == 200:
                    logger.info(f"Proxy {proxy_url} is valid.")
                    return True
                else:
                    logger.error(f"Proxy {proxy_url} responded with status code {response.status}. Invalid proxy.")
                    return False
    except aiohttp.ClientProxyConnectionError as e:
        logger.error(f"Failed to connect to proxy {proxy_url}. Invalid proxy or connection issue.")
        logger.exception(e)
        return False


async def connect_to_wss(socks5_proxy, user_id):
    logger.info(f"Connecting to WebSocket server via proxy {socks5_proxy}")
    if not await check_proxy(socks5_proxy):
        logger.error(f"Proxy {socks5_proxy} is invalid. Stopping execution.")
        return

    while True:
        try:
            device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
            logger.info(f"Device ID: {device_id}")

            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = "wss://proxy.wynd.network:4650/"
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(20)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "2.5.0"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            logger.error(f"An error occurred: {e}. Reconnecting...")
            await asyncio.sleep(5)  # Wait for a while before attempting to reconnect


async def main():
    # TODO Modify user_id
    _user_id = 'enter your grass user id here'
    # TODO Specify the SOCKS5 proxy
    socks5_proxy = 'socks5://username:password@host:port'
    await connect_to_wss(socks5_proxy, _user_id)


if __name__ == '__main__':
    # Run the main function
    asyncio.run(main())
