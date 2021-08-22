import aiofiles
import asyncio
import os

from aiohttp import web


async def archivate(request):
    archive_hash = request.match_info.get('archive_hash')
    photos_path = f'./test_photos/{archive_hash}'
    if not os.path.exists(photos_path):
        raise web.HTTPBadRequest(text='Archive does not exist of was removed')
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
        chunk = await proc.stdout.read(1024 * 1024)
        if proc.stdout.at_eof():
            break
        await response.write(chunk)
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
