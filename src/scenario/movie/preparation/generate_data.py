"""
Created on Aug 5, 2025

@author: Jiale Lao

Generates Movies_{scale_factor}.csv and Reviews_{scale_factor}.csv files
following these principles:
1. Scale factor controls the number of reviews
2. Sample movies first, then reviews for each sampled movie
3. Filter out reviews with null reviewText
4. Prefer movies with large number of reviews and long reviews
5. Include one movie with largest reviews following same score pattern
6. Include one movie with mostly negative reviews

An example command, providing the folder to the original kaggle dataset, and the scaling factor:
python3 generate_data.py .cache/kagglehub/datasets/andrezaza/clapper-massive-rotten-tomatoes-movies-and-reviews/versions/4 2000

Or to use Google Drive download:
python3 generate_data.py --download-from-drive --scale-factor 2000
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter
import re
import os


def download_from_google_drive():
    """Download movie.zip from Google Drive and extract it."""
    base_dir = Path(__file__).resolve().parents[4]
    source_data_dir = base_dir / "files" / "movie" / "source_data"
    source_data_dir.mkdir(parents=True, exist_ok=True)

    # The CSV files should be directly in source_data after extraction
    data_path = source_data_dir
    reviews_file = data_path / "rotten_tomatoes_movie_reviews.csv"
    movies_file = data_path / "rotten_tomatoes_movies.csv"

    # Check if data is already extracted
    if reviews_file.exists() and movies_file.exists():
        print(f"Data already available at: {data_path}")
        print("Skipping download and extraction.")
        return str(data_path)

    # Download movie.zip directly using file ID
    zip_file = source_data_dir / "movie.zip"

    if not zip_file.exists():
        print("Downloading movie data from Google Drive...")
        print("Downloading movie.zip...")
        # File ID: 1WkeXN3V5A6h-D_oeWvv2G_xs2PgzcQu0
        file_id = "1WkeXN3V5A6h-D_oeWvv2G_xs2PgzcQu0"

        # Try multiple download methods
        success = False

        # Method 1: Try gdown (handles large files better)
        print("Attempting download with gdown (handles large files)...")
        result = os.system(f"gdown 'https://drive.google.com/uc?id={file_id}' -O {zip_file}")
        if result == 0 and zip_file.exists() and zip_file.stat().st_size > 1000000:  # At least 1MB
            success = True
            print(f"Download successful with gdown (size: {zip_file.stat().st_size / 1024 / 1024:.1f}MB)")
        else:
            if zip_file.exists():
                os.remove(zip_file)

        # Method 2: Try wget with cookie handling for large files
        if not success:
            print("Attempting download with wget (handling Google Drive large file)...")
            cookie_file = source_data_dir / "cookie.txt"
            # First get the confirmation token
            os.system(f"wget --save-cookies {cookie_file} --keep-session-cookies --no-check-certificate 'https://drive.google.com/uc?export=download&id={file_id}' -O- 2>&1 | grep -o 'confirm=[^&]*' | sed 's/confirm=//' > {source_data_dir}/confirm.txt")

            # Read confirm token if exists
            confirm_file = source_data_dir / "confirm.txt"
            if confirm_file.exists():
                with open(confirm_file, 'r') as f:
                    confirm = f.read().strip()
                if confirm:
                    result = os.system(f"wget --load-cookies {cookie_file} --no-check-certificate 'https://drive.google.com/uc?export=download&confirm={confirm}&id={file_id}' -O {zip_file}")
                    # Clean up
                    os.remove(cookie_file)
                    os.remove(confirm_file)

                    if result == 0 and zip_file.exists() and zip_file.stat().st_size > 1000000:
                        success = True
                        print(f"Download successful with wget (size: {zip_file.stat().st_size / 1024 / 1024:.1f}MB)")
                    else:
                        if zip_file.exists():
                            os.remove(zip_file)

        # Method 3: Try curl with redirect handling
        if not success:
            print("Attempting download with curl...")
            result = os.system(f"curl -L -o {zip_file} 'https://drive.google.com/uc?export=download&id={file_id}'")
            if result == 0 and zip_file.exists() and zip_file.stat().st_size > 1000000:
                success = True
                print(f"Download successful with curl (size: {zip_file.stat().st_size / 1024 / 1024:.1f}MB)")
            else:
                if zip_file.exists():
                    os.remove(zip_file)

        if not success:
            raise RuntimeError(
                f"Failed to download movie.zip from Google Drive using all methods.\n"
                f"The file might be too large for automated download.\n"
                f"Please manually download from: https://drive.google.com/file/d/{file_id}/view\n"
                f"And save it to: {zip_file}"
            )
    else:
        print(f"Archive file already exists at: {zip_file}")
        print("Skipping download.")

    print(f"Unzipping {zip_file}...")
    os.system(f"unzip -o {zip_file} -d {source_data_dir}")

    # Clean up zip file after extraction
    os.system(f"rm {zip_file}")

    # Verify files exist
    if not reviews_file.exists() or not movies_file.exists():
        raise RuntimeError(
            f"CSV files not found after extraction.\n"
            f"Expected files:\n"
            f"  - {reviews_file}\n"
            f"  - {movies_file}\n"
            f"Please check the zip file contents."
        )

    print(f"Download and extraction completed. Data available at: {data_path}")
    return str(data_path)


def load_data(data_path):
    """Load and clean the raw data."""
    print("Loading data...")
    movies_df = pd.read_csv(f"{data_path}/rotten_tomatoes_movies.csv")
    reviews_df = pd.read_csv(f"{data_path}/rotten_tomatoes_movie_reviews.csv")
    
    print(f"Loaded {len(movies_df)} movies and {len(reviews_df)} reviews")
    
    # Filter out reviews with null reviewText
    reviews_df = reviews_df.dropna(subset=['reviewText'])
    print(f"After filtering null reviewText: {len(reviews_df)} reviews")
    
    return movies_df, reviews_df


def find_pattern_movie(reviews_df):
    """Find the movie with largest number of reviews following same score pattern."""
    print("Finding movie with consistent score pattern...")
    
    # Pre-filter for /5 and /10 patterns only
    pattern_5_reviews = reviews_df[reviews_df['originalScore'].str.contains('/5', na=False)]
    pattern_10_reviews = reviews_df[reviews_df['originalScore'].str.contains('/10', na=False)]
    
    best_movie = None
    best_pattern = None
    best_score = 0
    
    # Check /5 pattern
    if len(pattern_5_reviews) > 0:
        movie_counts = pattern_5_reviews.groupby('id').size()
        for movie_id, count in movie_counts.items():
            if count >= 50:  # Need at least 50 reviews
                unique_scores = pattern_5_reviews[pattern_5_reviews['id'] == movie_id]['originalScore'].nunique()
                score = count * unique_scores  # Prefer more reviews with more diversity
                if score > best_score:
                    best_movie = movie_id
                    best_pattern = '/5'
                    best_score = score
    
    # Check /10 pattern
    if len(pattern_10_reviews) > 0:
        movie_counts = pattern_10_reviews.groupby('id').size()
        for movie_id, count in movie_counts.items():
            if count >= 50:  # Need at least 50 reviews
                unique_scores = pattern_10_reviews[pattern_10_reviews['id'] == movie_id]['originalScore'].nunique()
                score = count * unique_scores
                if score > best_score:
                    best_movie = movie_id
                    best_pattern = '/10'
                    best_score = score
    
    print(f"Selected pattern movie: {best_movie} with {best_pattern} pattern")
    return best_movie, best_pattern


def get_negative_movie():
    """Use hardcoded negative movie."""
    print("Using hardcoded negative movie: taken_3")
    return 'taken_3'


def get_top_movies_fast(reviews_df, top_n=200):
    """Get top movies by review count quickly."""
    print(f"Getting top {top_n} movies by review count...")
    movie_counts = reviews_df.groupby('id').size().sort_values(ascending=False)
    return movie_counts.head(top_n).index.tolist()


def sample_reviews(reviews_df, pattern_movie, pattern_pattern, negative_movie, top_movies, scale_factor):
    """Sample reviews using movie-first strategy."""
    print(f"Sampling {scale_factor} reviews using movie-first strategy...")
    
    selected_reviews = []
    used_movies = set()
    
    # Step 1: Add pattern movie reviews (ONLY those matching the pattern)
    print(f"Step 1: Adding pattern movie {pattern_movie} (only {pattern_pattern} reviews)")
    pattern_movie_reviews = reviews_df[
        (reviews_df['id'] == pattern_movie) & 
        (reviews_df['originalScore'].str.contains(pattern_pattern, na=False))
    ]
    selected_reviews.append(pattern_movie_reviews)
    used_movies.add(pattern_movie)
    remaining = scale_factor - len(pattern_movie_reviews)
    print(f"Added {len(pattern_movie_reviews)} pattern reviews, remaining: {remaining}")
    
    # Step 2: Add negative movie reviews (ALL reviews, no pattern filtering)
    if negative_movie != pattern_movie and remaining > 0:
        print(f"Step 2: Adding negative movie {negative_movie} (all reviews)")
        negative_movie_reviews = reviews_df[reviews_df['id'] == negative_movie]
        if len(negative_movie_reviews) > 0:
            sample_size = min(len(negative_movie_reviews), remaining // 3)  # Use up to 1/3 of remaining
            sampled = negative_movie_reviews.sample(n=sample_size, random_state=42)
            selected_reviews.append(sampled)
            used_movies.add(negative_movie)
            remaining -= sample_size
            print(f"Added {sample_size} negative reviews, remaining: {remaining}")
    
    # Step 3: Add reviews from top movies (ALL reviews, no pattern filtering)
    print("Step 3: Adding reviews from top movies (all reviews)")
    for movie_id in top_movies:
        if remaining <= 0:
            break
        if movie_id in used_movies:
            continue
            
        movie_reviews = reviews_df[reviews_df['id'] == movie_id]
        if len(movie_reviews) == 0:
            continue
            
        # Sample 5-15 reviews per movie for diversity
        sample_size = min(len(movie_reviews), max(5, remaining // 30), remaining)
        sampled = movie_reviews.sample(n=sample_size, random_state=42)
        selected_reviews.append(sampled)
        used_movies.add(movie_id)
        remaining -= sample_size
    
    print(f"Final step: added reviews from {len(used_movies)} total movies")
    
    # Combine and shuffle
    final_reviews = pd.concat(selected_reviews, ignore_index=True)
    final_reviews = final_reviews.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Trim to exact scale factor
    final_reviews = final_reviews.head(scale_factor)
    
    return final_reviews


def generate_movies_table(movies_df, reviews_df):
    """Generate movies table for movies that have reviews."""
    movie_ids_with_reviews = reviews_df['id'].unique()
    selected_movies = movies_df[movies_df['id'].isin(movie_ids_with_reviews)].copy()
    return selected_movies


def print_statistics(movies_df, reviews_df, pattern_movie, pattern_pattern, negative_movie):
    """Print comprehensive statistics to verify requirements."""
    print("\n" + "="*50)
    print("DATASET STATISTICS")
    print("="*50)
    
    print(f"Total movies: {len(movies_df)}")
    print(f"Total reviews: {len(reviews_df)}")
    
    # Top-5 movies with most reviews in dataset
    movie_review_counts = reviews_df.groupby('id').size().sort_values(ascending=False)
    print(f"\nTop-5 movies with most reviews in dataset:")
    for i, (movie_id, count) in enumerate(movie_review_counts.head(5).items()):
        print(f"  {i+1}. {movie_id}: {count} reviews")
    
    # Pattern movie statistics
    pattern_movie_reviews = reviews_df[reviews_df['id'] == pattern_movie]
    pattern_movie_pattern_reviews = pattern_movie_reviews[
        pattern_movie_reviews['originalScore'].str.contains(pattern_pattern, na=False)
    ]
    pattern_scores = pattern_movie_pattern_reviews['originalScore'].value_counts()
    
    print(f"\nPattern movie ({pattern_movie}):")
    print(f"  Total reviews in dataset: {len(pattern_movie_reviews)}")
    print(f"  Reviews with {pattern_pattern} pattern: {len(pattern_movie_pattern_reviews)}")
    if len(pattern_movie_pattern_reviews) > 0:
        print(f"  Unique {pattern_pattern} scores: {pattern_movie_pattern_reviews['originalScore'].nunique()}")
        print(f"  Score distribution: {dict(pattern_scores.head())}")
    
    # Negative movie statistics
    negative_movie_reviews = reviews_df[reviews_df['id'] == negative_movie]
    if len(negative_movie_reviews) > 0:
        negative_ratio = (negative_movie_reviews['scoreSentiment'] == 'NEGATIVE').mean()
        
        print(f"\nNegative movie ({negative_movie}):")
        print(f"  Total reviews in dataset: {len(negative_movie_reviews)}")
        print(f"  Negative reviews: {(negative_movie_reviews['scoreSentiment'] == 'NEGATIVE').sum()}")
        print(f"  Negative ratio: {negative_ratio:.1%}")
    
    # Overall dataset statistics
    print(f"\nOverall dataset:")
    print(f"  Null reviewText: {reviews_df['reviewText'].isnull().sum()} (should be 0)")
    print(f"  Average review length: {reviews_df['reviewText'].str.len().mean():.1f} characters")
    
    # Score pattern distribution
    for pattern in ['/5', '/10', '/4']:
        count = reviews_df['originalScore'].str.contains(pattern, na=False).sum()
        pct = count / len(reviews_df) * 100
        print(f"  Reviews with {pattern} pattern: {count} ({pct:.1f}%)")
    
    # Sentiment distribution
    sentiment_counts = reviews_df['scoreSentiment'].value_counts()
    print(f"  Sentiment distribution: {dict(sentiment_counts)}")


def main():
    parser = argparse.ArgumentParser(description="Generate movie dataset")
    parser.add_argument('data_path', nargs='?', help='Path to the Kaggle dataset directory (optional if --download-from-drive is used)')
    parser.add_argument('scale_factor', nargs='?', type=int, help='Number of reviews to generate (up to 1375738 after filtering nulls)')
    parser.add_argument('--download-from-drive', action='store_true', help='Download data from Google Drive')
    parser.add_argument('--scale-factor', type=int, dest='scale_factor_flag', help='Scale factor (alternative to positional argument)')
    args = parser.parse_args()

    # Determine data path
    if args.download_from_drive:
        data_path = download_from_google_drive()
    elif args.data_path:
        data_path = args.data_path
    else:
        parser.error("Either provide data_path or use --download-from-drive")

    # Determine scale factor
    scale_factor = args.scale_factor_flag if args.scale_factor_flag is not None else args.scale_factor
    if scale_factor is None:
        parser.error("scale_factor is required (either positional or --scale-factor)")

    # Load data
    movies_df, reviews_df = load_data(data_path)
    
    # Validate scale_factor bounds
    max_reviews = len(reviews_df)  # Already filtered for nulls in load_data
    if scale_factor > max_reviews:
        print(f"Warning: scale_factor ({scale_factor}) exceeds available reviews ({max_reviews})")
        print(f"Using maximum available reviews: {max_reviews}")
        scale_factor = max_reviews
    
    # Find special movies
    pattern_movie, pattern_pattern = find_pattern_movie(reviews_df)
    negative_movie = get_negative_movie()
    
    # Get top movies by review count (much faster than ranking all movies)
    top_movies = get_top_movies_fast(reviews_df)
    
    # Sample reviews
    selected_reviews = sample_reviews(
        reviews_df, pattern_movie, pattern_pattern, negative_movie,
        top_movies, scale_factor
    )
    
    # Generate movies table
    selected_movies = generate_movies_table(movies_df, selected_reviews)
    
    # Print statistics
    print_statistics(selected_movies, selected_reviews, pattern_movie, pattern_pattern, negative_movie)
    
    # Save files to data/sf_{scale_factor}/ directory
    base_output_dir = Path(__file__).resolve().parents[4] / "files" / "movie" / "data"
    output_dir = base_output_dir / f"sf_{scale_factor}"
    output_dir.mkdir(parents=True, exist_ok=True)

    movies_file = output_dir / "Movies.csv"
    reviews_file = output_dir / "Reviews.csv"

    # Clean reviewText to prevent CSV formatting issues
    selected_reviews = selected_reviews.copy()
    selected_reviews['reviewText'] = selected_reviews['reviewText'].str.replace('\n', ' ', regex=False).str.replace('\r', ' ', regex=False)

    selected_movies.to_csv(movies_file, index=False)
    selected_reviews.to_csv(reviews_file, index=False)

    print(f"\nFiles saved:")
    print(f"  {movies_file}")
    print(f"  {reviews_file}")

    print(f"\n=== Generated Tables Summary ===")
    print(f"Movies.csv: {len(selected_movies)} rows")
    print(f"Reviews.csv: {len(selected_reviews)} rows")
    print(f"Maximum table size: {max(len(selected_movies), len(selected_reviews))} rows")


if __name__ == "__main__":
    main()