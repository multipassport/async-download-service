import aiofiles
import asyncio
import logging
import os

from aiohttp import web


async def archivate(request):
    logging.debug('Handling archive downloading request')
    archive_hash = request.match_info.get('archive_hash')
    photos_path = f'./test_photos/{archive_hash}'
    if not os.path.exists(photos_path):
        message = f'Archive {archive_hash} does not exist of was removed'
        logging.exception(message)
        raise web.HTTPBadRequest(text=message)
    command = f'zip -jr - {photos_path}'

    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    headers = {
        'Content-Type': 'application/zip',
        'Content-Disposition': 'attachment; filename="archive.zip"',
    }
    response = web.StreamResponse(headers=headers)
    await response.prepare(request)

    while True:
        logging.debug('Sending archive chunk')
        chunk = await proc.stdout.read(1024 * 1024)
        if proc.stdout.at_eof():
            logging.debug('End of the archive')
            break
        await response.write(chunk)
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
        filename='server.log',
    )

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
