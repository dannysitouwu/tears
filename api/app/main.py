from fastapi import FastAPI, Query, Depends, HTTPException, status, APIRouter, security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from .security import decode_access_token, create_access_token, verify_password
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models, schemas, crud
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
router = APIRouter(prefix="/auth", tags=["auth"])

app = FastAPI(title='tears API')

models.Base.metadata.create_all(bind=engine)

def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()
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
	return crud.create_chat(db, payload, me)

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
	return msg
	
@app.post('/chats/{chat_id}/members', response_model=dict)
def add_member(chat_id: int, payload: schemas.MemberCreate, db: Session = Depends(get_db), me = Depends(get_current_user)):
    # only owner can add members
    owner = db.query(models.ChatMember).filter_by(chat_id=chat_id, user_id=me.id, role="owner").first()
    if not owner:
        raise HTTPException(status_code=403, detail="Only owner can add members")
    member = crud.add_chat_member(db, chat_id, payload.user_id)
    return {"id": member.id, "chat_id": member.chat_id, "user_id": member.user_id}


@app.get('/chats', response_model=dict)
def list_chats(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=250), db: Session = Depends(get_db)):
	data = crud.list_chats(db, page, per_page)
	return {
		'meta': {k: data[k] for k in ('page','per_page','total_items','total_pages')},
		'items': [schemas.ChatOut.from_orm(c).dict() for c in data['items']]
	}

@app.get('/chats/{chat_id}/messages', response_model=dict)
def chat_messages(chat_id: int, page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=250), db: Session = Depends(get_db)):
	data = crud.list_messages(db, page, per_page, chat_id=chat_id)
	return {
		'meta': {k: data[k] for k in ('page','per_page','total_items','total_pages')},
		'items': [schemas.MessageOut.from_orm(m).dict() for m in data['items']]
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

app.include_router(router)