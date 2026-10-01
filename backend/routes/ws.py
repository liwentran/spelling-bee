from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ws_manager import manager
import json

router = APIRouter()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                command = json.loads(data)
                await manager.handle_command(session_id, command)
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
