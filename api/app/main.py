from fastapi import FastAPI, Query, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models, schemas, crud

app = FastAPI(title='tears API')

models.Base.metadata.create_all(bind=engine)

def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()
		
@app.get('/users', response_model=dict)
def api_list_users(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=250), db: Session = Depends(get_db)):
	data = crud.list_users(db, page, per_page)
	return {
		'meta': {k: data[k] for k in ('page','per_page','total_items','total_pages')},
		'items': [schemas.UserOut.from_orm(u).dict() for u in data['items']]
	}


@app.get('/chats', response_model=dict)
def api_list_chats(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=250), db: Session = Depends(get_db)):
	data = crud.list_chats(db, page, per_page)
	return {
		'meta': {k: data[k] for k in ('page','per_page','total_items','total_pages')},
		'items': [schemas.ChatOut.from_orm(c).dict() for c in data['items']]
	}


@app.get('/chats/{chat_id}/messages', response_model=dict)
def api_chat_messages(chat_id: int, page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=250), db: Session = Depends(get_db)):
	data = crud.list_messages(db, page, per_page, channel_id=chat_id)
	return {
		'meta': {k: data[k] for k in ('page','per_page','total_items','total_pages')},
		'items': [schemas.MessageOut.from_orm(m).dict() for m in data['items']]
	}


@app.get('/messages', response_model=dict)
def api_messages(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=250), user_id: int = None, channel_id: int = None, q: str = None, start_date: str = None, end_date: str = None, db: Session = Depends(get_db)):
	data = crud.list_messages(db, page, per_page, user_id=user_id, channel_id=channel_id, q_text=q, start_date=start_date, end_date=end_date)
	return {
		'meta': {k: data[k] for k in ('page','per_page','total_items','total_pages')},
		'items': [schemas.MessageOut.from_orm(m).dict() for m in data['items']]
	}


@app.get('/messages/{message_id}', response_model=schemas.MessageOut)
def api_get_message(message_id: int, db: Session = Depends(get_db)):
	msg = crud.get_message(db, message_id)
	if not msg:
		raise HTTPException(status_code=404, detail='Message not found')
	return msg


@app.post('/messages', response_model=schemas.MessageOut)
def api_create_message(payload: schemas.MessageCreate, db: Session = Depends(get_db)):
	if (not payload.content and not payload.sticker_id) or (payload.content and payload.sticker_id):
		raise HTTPException(status_code=400, detail='Debes enviar solo texto o solo sticker, no ambos ni ninguno')
	msg = models.message(
		user_id=payload.user_id,
		channel_id=payload.channel_id,
		content=payload.content,
		sticker_id=payload.sticker_id,
	)
	db.add(msg)
	db.commit()
	db.refresh(msg)
	return msg