import uvicorn

from app.utils.event_loop import run

server = uvicorn.Server(uvicorn.Config("app.main:app", host="0.0.0.0", port=8080))
run(server.serve())
