import asyncio

from aiohttp import web

routes = web.RouteTableDef()


@routes.get("/echo")
@routes.post("/echo")
async def echo_handler(request):
    data = {}
    if request.can_read_body:
        try:
            data = await request.json()
        except Exception:
            text = await request.text()
            data = {"raw": text}

    return web.json_response({
        "method": request.method,
        "headers": dict(request.headers),
        "url": str(request.url),
        "body": data
    })


@routes.post("/complex")
async def complex_handler(request):
    data = await request.json()
    # Echo back the data but with a tag
    return web.json_response({
        "received": data,
        "status": "processed"
    })


@routes.get("/sleep/{seconds}")
async def sleep_handler(request):
    seconds = float(request.match_info["seconds"])
    await asyncio.sleep(seconds)
    return web.json_response({"slept": seconds})


async def make_app():
    app = web.Application()
    app.add_routes(routes)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), port=8080)
