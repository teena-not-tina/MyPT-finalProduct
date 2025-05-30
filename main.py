from fastapi import FastAPI
from models import MsgPayload
from fastapi.middleware.cors import CORSMiddleware
from stable_diffusion import contact_comfyui, character_update
from stable_diffusion.img_output import get_current_img, login_find_img


app = FastAPI()
messages_list: dict[int, MsgPayload] = {}

# CORS 설정 (React 앱에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contact_comfyui.router, prefix="")
app.include_router(character_update.router, prefix="")
app.include_router(get_current_img.router, prefix="")
app.include_router(login_find_img.router, prefix="")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello"}


# About page route
@app.get("/about")
def about() -> dict[str, str]:
    return {"message": "This is the about page."}


# Route to add a message
@app.post("/messages/{msg_name}/")
def add_msg(msg_name: str) -> dict[str, MsgPayload]:
    # Generate an ID for the item based on the highest ID in the messages_list
    msg_id = max(messages_list.keys()) + 1 if messages_list else 0
    messages_list[msg_id] = MsgPayload(msg_id=msg_id, msg_name=msg_name)

    return {"message": messages_list[msg_id]}


# Route to list all messages
@app.get("/messages")
def message_items() -> dict[str, dict[int, MsgPayload]]:
    return {"messages:": messages_list}
