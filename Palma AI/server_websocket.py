import asyncio
import time
import os
from fastapi import Request
from typing import Literal, Optional, Dict
from uuid import uuid4
from urllib.parse import unquote
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

from injestion import run_pipeline
from query import query_app


load_dotenv()

app = FastAPI(title="Palma Help Agent")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

# --- Order Workflow Endpoints ---
# from order import order_app

# class OrderRequest(BaseModel):
#     item: str
#     quantity: int


# @app.post("/order/start")
# async def start_order(req: OrderRequest):
#     order_id = str(uuid4())

#     # Start workflow asynchronously
#     asyncio.create_task(
#         order_app.ainvoke(
#             {
#                 "item": req.item,
#                 "quantity": req.quantity,
#                 "approved": None,
#                 "status": "started",
#             },
#             config={"configurable": {"thread_id": order_id}},
#         )
#     )

#     return {
#         "order_id": order_id,
#         "status": "started",
#     }


# import json
# import asyncio
# from fastapi.responses import StreamingResponse


# @app.get("/order/events/{order_id}")
# async def order_events(order_id: str):

#     async def event_stream():
#         try:
#             async for event in order_app.astream_events(
#                 None,
#                 config={"configurable": {"thread_id": order_id}},
#             ):
#                 yield f"data: {json.dumps(event)}\n\n"

#         except asyncio.CancelledError:
#             return

#     return StreamingResponse(
#         event_stream(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#         },
#     )


# from typing import Literal


# class DecisionRequest(BaseModel):
#     order_id: str
#     decision: Literal["approve", "reject"]


# @app.post("/order/decision")
# async def order_decision(req: DecisionRequest):
#     await order_app.ainvoke(
#         req.decision,
#         config={"configurable": {"thread_id": req.order_id}},
#     )
#     return {"status": "decision_received"}


# import json
# import asyncio
# from uuid import uuid4
# from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# app = FastAPI()

# @app.websocket("/ws/order")
# async def order_ws(ws: WebSocket):
#     await ws.accept()
#     order_id = str(uuid4())

#     try:
#         # 1. Receive initial order
#         init = await ws.receive_json()

#         asyncio.create_task(
#             order_app.ainvoke(
#                 {
#                     "item": init["item"],
#                     "quantity": init["quantity"],
#                     "approved": None,
#                     "status": "started",
#                 },
#                 config={"configurable": {"thread_id": order_id}},
#             )
#         )

#         # 2. Stream graph events
#         async for event in order_app.astream_events(
#             None,
#             config={"configurable": {"thread_id": order_id}},
#         ):
#             await ws.send_json(event)

#             # 3. Interrupt handling
#             if event["event"] == "on_interrupt":
#                 decision_msg = await ws.receive_json()
#                 await order_app.ainvoke(
#                     decision_msg["decision"],  # approve | reject
#                     config={"configurable": {"thread_id": order_id}},
#                 )

#             if event["event"] == "on_chain_end":
#                 break

#     except WebSocketDisconnect:
#         print("Client disconnected")

# Client-side example (e.g., in a browser console):

# const ws = new WebSocket("ws://localhost:8000/ws/order");

# ws.onopen = () => {
#   ws.send(JSON.stringify({
#     item: "Laptop",
#     quantity: 1
#   }));
# };

# ws.onmessage = (e) => {
#   const event = JSON.parse(e.data);

#   if (event.event === "on_interrupt") {
#     // show approve / reject UI
#     ws.send(JSON.stringify({ decision: "approve" }));
#   }

#   if (event.event === "on_chain_end") {
#     ws.close();
#   }
# };


if __name__ == "__main__":
    # Allow running without uvicorn for quick local checks
    import uvicorn

    host = os.getenv("UVICORN_HOST", "127.0.0.1")
    port = int(os.getenv("UVICORN_PORT", "8000"))
    reload = os.getenv("UVICORN_RELOAD", "0") == "1"
    uvicorn.run("server:app", host=host, port=port, reload=reload)
