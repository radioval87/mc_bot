import asyncio

import configargparse


async def tcp_writer(host, port, token):
    _, writer = await asyncio.open_connection(host, port)

    message = f'{token}\n'
    writer.write(message.encode())

    while True:
        message = input()
        writer.write(message.encode())
        writer.write('\n'.encode())

if __name__ == '__main__':
    parser = configargparse.ArgParser()
    parser.add_argument(
        '--host', required=True, type=str, help='Host address',
        env_var='HOST'
    )
    parser.add_argument(
        '--port', required=True, type=str, help=('Host port'), env_var='PORT'
    )
    parser.add_argument(
        '--token', type=str,
        help='Personal hash to connect as an existing user', env_var='TOKEN'
    )
    args = parser.parse_args()

    asyncio.run(tcp_writer(args.host, args.port, args.token))
