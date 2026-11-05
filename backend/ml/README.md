# xG training pipeline

`train_xg.py` downloads **StatsBomb Open Data**, extracts shot events, computes shot distance/angle plus contextual features, trains a scikit-learn logistic-regression pipeline, evaluates it, and writes:

- `models/xg_model.joblib`
- `models/xg_model_card.json`

The runtime API automatically uses the trained artifact when present and otherwise labels its transparent geometric fallback as a baseline.

Run from `backend/`:

```bash
python -m ml.train_xg --competition-id 43 --season-id 106 --max-matches 50
```

If you publish analysis derived from StatsBomb Open Data, follow StatsBomb's attribution terms.
