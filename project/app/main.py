from sklearn.preprocessing import MultiLabelBinarizer
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api import predict, viz
from sqlalchemy.orm import Session
from .database import SessionLocal, engine

from . import crud, models, schemas

from typing import List

import pickle
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
tfidf_vectorizer = TfidfVectorizer(max_df=0.8, max_features=10000)

multilabel_binarizer = MultiLabelBinarizer()

models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(
    title='Human-Rights-first-Police-Tracker DS API',
    description='Search locations where use of police force is reported on social media',
    version='0.1',
    docs_url='/',
)


@app.get("/incidents/", response_model=List[schemas.Incidents])
def read_incidents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    incidents = crud.get_incidents(db, skip=skip, limit=limit)
    return incidents


@app.post('/cron_update/', response_model=List[schemas.PBIncidents])
def read_pbincidents(pbincidents: list):
    df = pd.DataFrame(pbincidents)
    # pickle dump from notebook category_tags.py
    tags_model = open('tags_name.pkl', 'rb')
    clf2 = pickle.loads(tags_model)
# take the new data and vectorize it for the model
# run vectorized data through model
    df_tfidf = tfidf_vectorizer.transform(df['name'])
    y_pred = clf2.predict(df_tfidf)
# get predictions and inverse transform the results so we can read the results
    df['tag_predicted'] = multilabel_binarizer.inverse_transform(y_pred)
# clean the results by eliminating commas and parenthesis, append to df
    df['tag_predicted'] = df['tag_predicted'].apply(lambda x: ', '.join(x))
    tags_model.close()


app.include_router(predict.router)
app.include_router(viz.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

if __name__ == '__main__':
    uvicorn.run(app)
