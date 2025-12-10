from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import Word

router = APIRouter(prefix="/words", tags=["words"])


# ---------- Schemas ----------

class WordBase(BaseModel):
    word: str
    definition: str
    extra_json: Optional[str] = None
    active: bool = True


class WordCreate(WordBase):
    pass


class WordUpdate(BaseModel):
    word: Optional[str] = None
    definition: Optional[str] = None
    extra_json: Optional[str] = None
    active: Optional[bool] = None


class WordOut(WordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Endpoints ----------

@router.get("", response_model=List[WordOut])
def list_words(db: Session = Depends(get_db)):
    return db.query(Word).order_by(Word.id).all()


@router.get("/{word_id}", response_model=WordOut)
def get_word(word_id: int, db: Session = Depends(get_db)):
    w = db.query(Word).filter(Word.id == word_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Word not found")
    return w


@router.post("", response_model=WordOut, status_code=status.HTTP_201_CREATED)
def create_word(payload: WordCreate, db: Session = Depends(get_db)):
    # Enforce unique word text
    existing = db.query(Word).filter(Word.word == payload.word).first()
    if existing:
        raise HTTPException(status_code=400, detail="Word already exists")

    w = Word(
        word=payload.word,
        definition=payload.definition,
        extra_json=payload.extra_json,
        active=payload.active,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


@router.patch("/{word_id}", response_model=WordOut)
def update_word(word_id: int, payload: WordUpdate, db: Session = Depends(get_db)):
    w = db.query(Word).filter(Word.id == word_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Word not found")

    data = payload.dict(exclude_unset=True)

    if "word" in data:
        # enforce uniqueness
        existing = db.query(Word).filter(Word.word == data["word"]).first()
        if existing and existing.id != word_id:
            raise HTTPException(status_code=400, detail="Word already exists")
        w.word = data["word"]

    if "definition" in data:
        w.definition = data["definition"]

    if "extra_json" in data:
        w.extra_json = data["extra_json"]

    if "active" in data:
        w.active = data["active"]

    w.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(w)
    return w


@router.delete("/{word_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_word(word_id: int, db: Session = Depends(get_db)):
    w = db.query(Word).filter(Word.id == word_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Word not found")

    db.delete(w)
    db.commit()
    return
