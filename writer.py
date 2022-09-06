import asyncio
import json
import logging

import configargparse


async def read_and_save_to_log(reader):
    msg = await reader.read(1000)
    logging.debug(msg.decode())
    return msg


async def tcp_writer(host, port, token):
    reader, writer = await asyncio.open_connection(host, port)

    await read_and_save_to_log(reader)

    message = f'{token}\n'
    writer.write(message.encode())

    answer = await read_and_save_to_log(reader)
    
    if json.loads(answer) is None:
        logging.warning('Неизвестный токен. ' 
                        'Проверьте его или зарегистрируйте заново.')
        raise SystemExit
    
    while True:
        message = input()
        writer.write(message.encode())
        writer.write('\n'.encode())

        logging.debug(f'Sent message: {message}')

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

    logging.basicConfig(
        format=(
            '%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s] '
            '%(message)s'
        ),
        level=logging.DEBUG
    )

    asyncio.run(tcp_writer(args.host, args.port, args.token))
