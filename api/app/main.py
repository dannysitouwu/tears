from fastapi import FastAPI, Query, Depends, HTTPException, status, APIRouter, security, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from prometheus_fastapi_instrumentator import Instrumentator
from .metrics import metrics_middleware, get_metrics
from .security import decode_access_token, create_access_token, verify_password
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models, schemas, crud
from typing import Optional
from .websocket import websocket_endpoint, manager
import logging
import json
import time

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
router = APIRouter(prefix="/auth", tags=["auth"])

app = FastAPI(title='tears API')

logging.basicConfig(
	level=logging.INFO,
	format='%(message)s'
)
logger = logging.getLogger("tears-api")

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
	if request.url.path == "/metrics":
		return await call_next(request)
	
	start_time = time.time()
	
	# get user info from token - if available
	user_id = None
	username = None
	auth_header = request.headers.get("authorization", "")
	if auth_header.startswith("Bearer "):
		try:
			token = auth_header.split(" ")[1]
			payload = decode_access_token(token)
			if payload:
				user_id = payload.get("sub")
		except:
			pass
	
	response = await call_next(request)
	
	process_time = time.time() - start_time
	
	# structured log in JSON for Loki
	log_data = {
		"timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
		"method": request.method,
		"path": request.url.path,
		"status_code": response.status_code,
		"duration_ms": round(process_time * 1000, 2),
		"user_id": user_id,
		"query_params": dict(request.query_params) if request.query_params else None,
		"client_host": request.client.host if request.client else None,
	}
	
	logger.info(json.dumps(log_data))
	
	return response

# CORS -- allow frontend to access the API

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

app.middleware("http")(metrics_middleware)

models.Base.metadata.create_all(bind=engine)

app.include_router(router)

def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()
		db.bind.dispose()
# auth
@router.post("/register", response_model=schemas.UserOut)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
	if crud.get_user_by_email(db, payload.email):
		raise HTTPException(status_code=400, detail="Email already registered")
	return crud.create_user(db, payload)

@router.post("/token", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
	# allow login with email or username
	identifier = form_data.username
	user = crud.get_user_by_email(db, identifier) or crud.get_user_by_username(db, identifier)
	if not user or not verify_password(form_data.password, user.password_hash):
		raise HTTPException(status_code=401, detail="Invalid credentials")
	token = create_access_token(subject=user.id)
	return {"access_token": token, "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
	credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
	try:
		payload = decode_access_token(token)
		user_id = int(payload.get("sub"))
	except Exception:
		raise credentials_exception
	user = crud.get_user(db, user_id)
	if user is None:
		raise credentials_exception
	return user


def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme_optional), db: Session = Depends(get_db)):
	if not token:
		return None
	try:
		payload = decode_access_token(token)
		user_id = int(payload.get("sub"))
	except Exception:
		return None
	user = crud.get_user(db, user_id)
	return user

@router.get("/me", response_model=schemas.UserOut)
def get_current_user_info(me = Depends(get_current_user)):
	return me
		
# user 	
	
@app.get('/users', response_model=dict)
def list_users(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=250), db: Session = Depends(get_db)):
	data = crud.list_users(db, page, per_page)
	return {
		'meta': {k: data[k] for k in ('page','per_page','total_items','total_pages')},
		'items': [schemas.UserOut.from_orm(u).dict() for u in data['items']]
	}

# chat
def user_is_participant(db, chat_id, user_id):
    return db.query(models.ChatMember).filter_by(chat_id=chat_id, user_id=user_id).first() is not None

@app.post('/chats', response_model=schemas.ChatOut)
def create_chat(payload: schemas.ChatCreate, db: Session = Depends(get_db), me=Depends(get_current_user_optional)):
	if me is None and payload.is_private:
		raise HTTPException(status_code=403, detail='Authentication required to create private chats')
	chat = crud.create_chat(db, payload, me)
	# return with counts and role
	member_count = db.query(models.ChatMember).filter_by(chat_id=chat.id).count()
	message_count = db.query(models.Message).filter_by(chat_id=chat.id).count()
	role = None
	if me:
		member = db.query(models.ChatMember).filter_by(chat_id=chat.id, user_id=me.id).first()
		role = member.role if member else None
	chat_dict = schemas.ChatOut.from_orm(chat).dict()
	chat_dict.update({
		"member_count": member_count,
		"message_count": message_count,
		"role": role,
	})
	return chat_dict

@app.post('/chats/{id}/messages', response_model=schemas.MessageOut)
def send_message(id: int, payload: schemas.ChatMessageCreate, db: Session = Depends(get_db), me=Depends(get_current_user)):
	# use the path id as the chat identifier
	chat = crud.get_chat(db, id)
	if not chat:
		raise HTTPException(status_code=404, detail="Chat not found")
	# if private, only participants can send
	if chat.is_private and not crud.user_is_participant(db, id, me.id):
		raise HTTPException(status_code=403, detail="Not a participant")
	# create message with authenticated user
	msg = models.Message(user_id=me.id, chat_id=id, content=payload.content)
	db.add(msg)
	db.commit()
	db.refresh(msg)
	# return with username and display_name
	msg_dict = schemas.MessageOut.from_orm(msg).dict()
	msg_dict["username"] = me.username
	msg_dict["display_name"] = me.display_name
	return msg_dict
	
@app.post('/chats/{chat_id}/join', response_model=dict)
def join_chat(chat_id: int, db: Session = Depends(get_db), me = Depends(get_current_user)):
	chat = crud.get_chat(db, chat_id)
	if not chat:
		raise HTTPException(status_code=404, detail="Chat not found")
	if chat.is_private:
		raise HTTPException(status_code=403, detail="Cannot join private chat")
	
	# check if already member
	existing = db.query(models.ChatMember).filter_by(chat_id=chat_id, user_id=me.id).first()
	if existing:
		return {"message": "Already a member", "role": existing.role}
	
	# add as member (not owner)
	member = crud.add_chat_member(db, chat_id, me.id, role="member")
	return {"message": "Joined successfully", "role": member.role}

@app.post('/chats/{chat_id}/members', response_model=dict)
def add_member(chat_id: int, payload: schemas.MemberCreate, db: Session = Depends(get_db), me = Depends(get_current_user)):
	# only owner can add members
	owner = db.query(models.ChatMember).filter_by(chat_id=chat_id, user_id=me.id, role="owner").first()
	if not owner:
		raise HTTPException(status_code=403, detail="Only owner can add members")

	user_id = payload.user_id
	if not user_id and payload.username:
		user = crud.find_user_by_username(db, payload.username)
		if not user:
			raise HTTPException(status_code=404, detail="User not found")
		user_id = user.id
	if not user_id:
		raise HTTPException(status_code=400, detail="user_id or username is required")

	member = crud.add_chat_member(db, chat_id, user_id)
	return {"id": member.id, "chat_id": member.chat_id, "user_id": member.user_id}


@app.get('/chats', response_model=dict)
def list_chats(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=250), search: Optional[str] = Query(None), db: Session = Depends(get_db), me=Depends(get_current_user_optional)):
	data = crud.list_chats(db, page, per_page, search=search)
	items = []
	for entry in data['items']:
		chat = entry['chat']
		role = None
		if me:
			member = db.query(models.ChatMember).filter_by(chat_id=chat.id, user_id=me.id).first()
			role = member.role if member else None
		chat_dict = schemas.ChatOut.from_orm(chat).dict()
		chat_dict.update({
			"member_count": entry["member_count"],
			"message_count": entry["message_count"],
			"role": role,
		})
		items.append(chat_dict)
	return {
		'meta': {k: data[k] for k in ('page','per_page','total_items','total_pages')},
		'items': items
	}

@app.get('/chats/{chat_id}', response_model=schemas.ChatOut)
def get_chat(chat_id: int, db: Session = Depends(get_db), me=Depends(get_current_user_optional)):
	chat = crud.get_chat(db, chat_id)
	if not chat:
		raise HTTPException(status_code=404, detail="Chat not found")
	member_count = db.query(models.ChatMember).filter_by(chat_id=chat.id).count()
	message_count = db.query(models.Message).filter_by(chat_id=chat.id).count()
	role = None
	if me:
		member = db.query(models.ChatMember).filter_by(chat_id=chat.id, user_id=me.id).first()
		role = member.role if member else None
	chat_dict = schemas.ChatOut.from_orm(chat).dict()
	chat_dict.update({
		"member_count": member_count,
		"message_count": message_count,
		"role": role,
	})
	return chat_dict

@app.get('/chats/{chat_id}/messages', response_model=dict)
def chat_messages(chat_id: int, page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=250), db: Session = Depends(get_db), me=Depends(get_current_user_optional)):
	# Check if chat exists
	chat = crud.get_chat(db, chat_id)
	if not chat:
		raise HTTPException(status_code=404, detail="Chat not found")
	
	# If chat is private, only members can view messages
	if chat.is_private and me:
		if not crud.user_is_participant(db, chat_id, me.id):
			raise HTTPException(status_code=403, detail="Not a participant")
	elif chat.is_private and not me:
		raise HTTPException(status_code=401, detail="Authentication required")
	
	data = crud.list_messages(db, page, per_page, chat_id=chat_id)
	items = []
	for m in data['items']:
		user = db.query(models.User).filter_by(id=m.user_id).first()
		# build dict manually to include username and display_name
		payload = {
			"id": m.id,
			"chat_id": m.chat_id,
			"user_id": m.user_id,
			"username": user.username if user else None,
			"display_name": user.display_name if user else None,
			"content": m.content,
			"created_at": m.created_at,
		}
		items.append(payload)
	return {
		'meta': {k: data[k] for k in ('page','per_page','total_items','total_pages')},
		'items': items
	}

# messages

@app.get('/messages', response_model=dict)
def messages(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=250), user_id: int = None, chat_id: int = None, q: str = None, start_date: str = None, end_date: str = None, db: Session = Depends(get_db)):
	data = crud.list_messages(db, page, per_page, user_id=user_id, chat_id=chat_id, q_text=q, start_date=start_date, end_date=end_date)
	return {
		'meta': {k: data[k] for k in ('page','per_page','total_items','total_pages')},
		'items': [schemas.MessageOut.from_orm(m).dict() for m in data['items']]
	}


@app.get('/messages/{message_id}', response_model=schemas.MessageOut)
def get_message(message_id: int, db: Session = Depends(get_db)):
	msg = crud.get_message(db, message_id)
	if not msg:
		raise HTTPException(status_code=404, detail='Message not found')
	return msg


@app.post('/messages', response_model=schemas.MessageOut)
def create_message(payload: schemas.MessageCreate, db: Session = Depends(get_db), me=Depends(get_current_user)):
	# using authenticated user
	if not payload.content or not payload.content.strip():
		raise HTTPException(status_code=400, detail='send only text messages')
	chat = crud.get_chat(db, payload.chat_id)
	if not chat:
		raise HTTPException(status_code=404, detail='Chat not found')
	if chat.is_private and not crud.user_is_participant(db, payload.chat_id, me.id):
		raise HTTPException(status_code=403, detail='You are not a member of this chat')
	msg = crud.create_message(db, me.id, payload.chat_id, payload.content)
	return msg

# websocket

@app.websocket("/ws/chats/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: int, token: str = Query(...)):
	db = SessionLocal()
	try:
		await websocket_endpoint(websocket, chat_id, token, db)
	finally:
		db.close()

@app.get("/ws/status")
async def websocket_status():
	return {
		"total_connections": manager.get_total_connections(),
		"active_chats": len(manager.active_connections),
		"chats": {
			chat_id: len(users)
			for chat_id, users in manager.active_connections.items()
		}
	}
# metrics 

@app.get("/metrics")
async def metrics():
	return get_metrics()

# health 

@app.get("/health")
async def health():
	return {"status": "ok"}

app.include_router(router)