import server
import asyncio

asyncio.run(server.main("assets/cert.pem", "assets/key.pem"))