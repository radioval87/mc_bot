import asyncio
from contextlib import asynccontextmanager


class MessageFormatError(AttributeError):
    pass


@asynccontextmanager
async def manage_socket(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def write_to_socket(writer, messages):
    try:
        for message in messages:
            writer.write(message.encode())
    except AttributeError:
        raise MessageFormatError
    await writer.drain()
