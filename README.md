# Spotify Listening History EDA

Exploratory data analysis, statistical inference, and skip-prediction modeling on my personal Spotify streaming history (2017–2025), covering 226,000+ streams.

## Project Structure

```
spotify-listening-history-eda/
├── notebooks/
│   └── spotify-listening-history-eda.ipynb   # main notebook
├── scripts/
│   ├── combine_spotifiles.py                  # merges raw Spotify JSON exports
│   ├── add_genres.py                          # fetches genre tags via Spotify API
│   ├── add_genres_methods.py                  # genre enrichment helpers
│   ├── hybrid_genre_method.py                 # hybrid genre tagging logic
│   └── musicbrainz_genre_method.py            # MusicBrainz fallback genre method
├── plots/                                     # exported visualizations
├── data/
│   ├── raw/                                   # place Spotify JSON exports here
│   └── processed/                             # genre-enriched CSV (not committed)
├── .env                                       # API credentials (not committed)
├── .gitignore
├── requirements.txt
└── README.md
```

## What's in this project

- **EDA & Visualization** — temporal listening patterns, genre analysis, year-over-year comparisons
- **Inference** — two-proportion z-tests comparing genre preferences on weekdays vs. weekends
- **Prediction** — binary skip classification using Logistic Regression and Random Forest

## Getting your data

This repo does not include personal listening data. To run the notebook with your own Spotify history:

1. Log in to [Spotify](https://www.spotify.com) and go to **Account → Privacy Settings**
2. Scroll to **Download your data** and request your **Extended streaming history** (not the basic version — you need the full history going back more than one year)
3. Spotify will email you a download link within 30 days
4. Unzip the download and locate the files named `Streaming_History_Audio_*.json`
5. Place them in `data/raw/`
6. Run `scripts/combine_spotifiles.py` to merge them into a single file

> **Note:** The extended history includes a `skipped` field and milliseconds played per stream, which are required for the Prediction section.

## Genre enrichment

The notebook reads from `data/processed/spotify_data_with_hybrid_genres.csv`, which adds genre tags not present in the raw Spotify export. These were fetched using the [Spotify Web API](https://developer.spotify.com/documentation/web-api) and [MusicBrainz](https://musicbrainz.org/) as a fallback.

To reproduce this step:

1. Create a [Spotify Developer](https://developer.spotify.com/) account and register an app to get a client ID and secret
2. Add your credentials to a `.env` file in the project root:
   ```
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   ```
3. Run `scripts/add_genres.py`

## Setup

```bash
git clone https://github.com/jurneebrinson/spotify-listening-history-eda.git
cd spotify-listening-history-eda
pip install -r requirements.txt
jupyter notebook notebooks/spotify-listening-history-eda.ipynb
```

## Visualizations

![Temporal Analysis](plots/Temporal%20Analysis.png)
![Top 10 Genres](plots/Top%2010%20Genres.png)
![Prediction ROC Curve](plots/Prediction%20ROC%20Curve.png)

## Key findings

- Listening activity dropped to near zero from 2020–mid 2021 during a switch to Apple Music, then resumed when the account moved to Spotify Premium
- Genre preferences are statistically consistent across weekdays and weekends — statistically significant differences exist for 14 of 20 genres, but all effect sizes are negligible (Cohen's h < 0.05)
- A Random Forest classifier predicts skip behavior with AUC 0.83 and recall 0.92 after removing data leakage from play-duration and stream-end metadata features
