import aiofiles
import argparse
import asyncio
import logging
import os
import pathlib

from aiohttp import web
from functools import partial


def create_parser():
    parser = argparse.ArgumentParser(
        description='Скрипт, позволяющий заархивировать и скачать данные',
    )
    parser.add_argument(
        '-l',
        '--logging',
        help='Включение/выключение логирования',
        default=False,
        action='store_true',
    )
    parser.add_argument(
        '-d',
        '--delay',
        help='Задержка ответа',
        type=float,
        default=0,
    )
    parser.add_argument(
        '--dir',
        help='Выбор пути к каталогу с фотографиями',
        type=pathlib.Path,
    )
    return parser


async def archivate(request, delay, folder):
    logging.debug('Handling archive downloading request')

    archive_hash = request.match_info.get('archive_hash', folder)
    photos_path = os.path.join('./test_photos', archive_hash)
    if not os.path.exists(photos_path):
        message = f'Archive {archive_hash} does not exist of was removed'
        logging.exception(message)
        raise web.HTTPBadRequest(text=message)

    command = 'zip', '-r', '-', photos_path
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
    )

    headers = {
        'Content-Type': 'application/zip',
        'Trasfer-Encoding': 'chunked',
        'Content-Disposition': 'attachment; filename="archive.zip"',
    }
    response = web.StreamResponse(headers=headers)
    response.enable_chunked_encoding()
    await response.prepare(request)

    try:
        while True:
            await asyncio.sleep(delay)
            logging.debug('Sending archive chunk')
            chunk = await proc.stdout.read(1024 * 1024)
            if proc.stdout.at_eof():
                logging.debug('End of the archive')
                break
            await response.write(chunk)
    except asyncio.CancelledError:
        logging.debug('Download was interrupted')
        await proc.communicate()
        raise
    finally:
        proc.kill()
        logging.debug('Process killed')
    logging.debug('Returning a full response')
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    parser = create_parser()
    arguments = parser.parse_args()

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
        filename='server.log',
    )
    if not arguments.logging:
        logging.disable(logging.CRITICAL + 1)

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get(
            '/archive/{archive_hash}',
            partial(
                archivate,
                folder=arguments.dir,
                delay=arguments.delay,
            )),
    ])
    web.run_app(app)
