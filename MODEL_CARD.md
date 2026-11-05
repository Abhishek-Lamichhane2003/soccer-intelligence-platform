# Analytics model card

## Win probability

The live win/draw/loss service is an **explainable baseline**, not a trained betting model. It uses score difference, match minute, and a small home-field prior. The API and UI label it as such.

## xG

The repository contains a reproducible StatsBomb Open Data training pipeline at `backend/ml/train_xg.py`.

When `backend/models/xg_model.joblib` exists, runtime xG predictions use that trained scikit-learn artifact and expose its JSON model card. If the artifact is absent, `/api/v1/ml/xg/predict` uses a clearly labeled geometric baseline.

The training pipeline reports ROC-AUC, log loss, Brier score, sample count, features, split method, limitations, and data attribution. Do not put a metric on a resume until you personally run the training script and preserve the generated model card.

## Optional LLM analyst

The LLM analyst is disabled by default. When explicitly enabled with an API key, it receives only normalized match facts and is instructed not to invent missing events or players. On any LLM/provider failure, the API returns the deterministic local analyst instead.
