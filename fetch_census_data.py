#!/usr/bin/env python3
"""
Fetch Census B18105 (Ambulatory Difficulty) data and annotate tracts_within_1mile.csv

For each tract, fetches:
1. Total population (5+ years): count, with ambulatory difficulty, percentage
2. Population 65+: count, with ambulatory difficulty, percentage
"""

import pandas as pd
import requests
import sys
from pathlib import Path

# Census API endpoint
CENSUS_API_BASE = "https://api.census.gov/data/2023/acs/acs5"

# Ensure generated directory exists
GENERATED_DIR = Path('generated')
GENERATED_DIR.mkdir(exist_ok=True)

def fetch_b18105_data(tract_geoids):
    """
    Fetch B18105 data for given tract GEOIDs.

    Variables needed:
    - B18105_001E: Total population 5+ years
    - B18105_004E: Male 5-17 with ambulatory difficulty
    - B18105_007E: Male 18-34 with ambulatory difficulty
    - B18105_010E: Male 35-64 with ambulatory difficulty
    - B18105_013E: Male 65-74 with ambulatory difficulty
    - B18105_016E: Male 75+ with ambulatory difficulty
    - B18105_020E: Female 5-17 with ambulatory difficulty
    - B18105_023E: Female 18-34 with ambulatory difficulty
    - B18105_026E: Female 35-64 with ambulatory difficulty
    - B18105_029E: Female 65-74 with ambulatory difficulty
    - B18105_032E: Female 75+ with ambulatory difficulty
    - B18105_012E: Male 65-74 total
    - B18105_015E: Male 75+ total
    - B18105_028E: Female 65-74 total
    - B18105_031E: Female 75+ total
    """

    # Variables to fetch
    variables = [
        'B18105_001E',  # Total pop 5+
        'B18105_004E', 'B18105_007E', 'B18105_010E', 'B18105_013E', 'B18105_016E',  # Male with difficulty
        'B18105_020E', 'B18105_023E', 'B18105_026E', 'B18105_029E', 'B18105_032E',  # Female with difficulty
        'B18105_012E', 'B18105_015E',  # Male 65+ totals
        'B18105_028E', 'B18105_031E',  # Female 65+ totals
    ]

    # Extract state and county from first GEOID (all should be same state/county)
    # Format: SSCCCTTTTTT (State, County, Tract)
    first_geoid = tract_geoids[0]
    state_fips = first_geoid[:2]
    county_fips = first_geoid[2:5]

    print(f"Fetching data for State {state_fips}, County {county_fips}")

    # Build API request
    var_string = ','.join(variables)
    url = f"{CENSUS_API_BASE}?get=NAME,{var_string}&for=tract:*&in=state:{state_fips}&in=county:{county_fips}"

    print(f"API URL: {url}")

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Convert to DataFrame
        # First row is headers
        headers = data[0]
        rows = data[1:]

        df = pd.DataFrame(rows, columns=headers)

        # Create GEOID from state, county, tract
        df['GEOID'] = df['state'] + df['county'] + df['tract']

        # Filter to only our tracts
        df = df[df['GEOID'].isin(tract_geoids)]

        # Convert numeric columns to integers
        for col in variables:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        print(f"Fetched data for {len(df)} tracts")

        return df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Census data: {e}", file=sys.stderr)
        sys.exit(1)

def calculate_metrics(df):
    """
    Calculate the required metrics from raw B18105 data.

    Returns DataFrame with columns:
    - GEOID
    - total_pop_5plus: Total population 5+ years
    - total_amb_diff: Total with ambulatory difficulty (all ages)
    - total_amb_diff_pct: Percentage with ambulatory difficulty
    - pop_65plus: Population 65+ years
    - pop_65plus_amb_diff: Population 65+ with ambulatory difficulty
    - pop_65plus_amb_diff_pct: Percentage of 65+ with ambulatory difficulty
    """

    result = pd.DataFrame()
    result['GEOID'] = df['GEOID']

    # Total population 5+ years
    result['total_pop_5plus'] = df['B18105_001E']

    # Total with ambulatory difficulty (sum all age groups for both sexes)
    result['total_amb_diff'] = (
        df['B18105_004E'] + df['B18105_007E'] + df['B18105_010E'] +
        df['B18105_013E'] + df['B18105_016E'] +  # Males
        df['B18105_020E'] + df['B18105_023E'] + df['B18105_026E'] +
        df['B18105_029E'] + df['B18105_032E']    # Females
    )

    # Percentage with ambulatory difficulty
    result['total_amb_diff_pct'] = (
        (result['total_amb_diff'] / result['total_pop_5plus'] * 100)
        .round(2)
    )

    # Population 65+ (sum of 65-74 and 75+ for both sexes)
    result['pop_65plus'] = (
        df['B18105_012E'] + df['B18105_015E'] +  # Male
        df['B18105_028E'] + df['B18105_031E']    # Female
    )

    # Population 65+ with ambulatory difficulty
    result['pop_65plus_amb_diff'] = (
        df['B18105_013E'] + df['B18105_016E'] +  # Male
        df['B18105_029E'] + df['B18105_032E']    # Female
    )

    # Percentage of 65+ with ambulatory difficulty
    result['pop_65plus_amb_diff_pct'] = (
        (result['pop_65plus_amb_diff'] / result['pop_65plus'] * 100)
        .round(2)
    )

    # Handle division by zero (set to 0 or NaN)
    result['total_amb_diff_pct'] = result['total_amb_diff_pct'].fillna(0)
    result['pop_65plus_amb_diff_pct'] = result['pop_65plus_amb_diff_pct'].fillna(0)

    return result

def main():
    # Read the tract CSV
    print("Reading generated/tracts_within_1mile.csv...")
    tracts_df = pd.read_csv('generated/tracts_within_1mile.csv', dtype={'GEOID': str})

    print(f"Found {len(tracts_df)} tracts")
    print(f"Tracts: {tracts_df['GEOID'].tolist()}")

    # Fetch Census data
    print("\nFetching Census B18105 data...")
    census_df = fetch_b18105_data(tracts_df['GEOID'].tolist())

    # Calculate metrics
    print("\nCalculating metrics...")
    metrics_df = calculate_metrics(census_df)

    # Merge with original tract data
    print("\nMerging data...")
    annotated_df = tracts_df.merge(metrics_df, on='GEOID', how='left')

    # Check for any missing data
    missing = annotated_df[annotated_df['total_pop_5plus'].isna()]
    if len(missing) > 0:
        print(f"\nWARNING: {len(missing)} tracts missing Census data:")
        print(missing[['GEOID', 'NAMELSAD']])

    # Display summary statistics
    print("\n=== Summary Statistics ===")
    print(f"\nTotal Population 5+:")
    print(f"  Min: {annotated_df['total_pop_5plus'].min()}")
    print(f"  Max: {annotated_df['total_pop_5plus'].max()}")
    print(f"  Mean: {annotated_df['total_pop_5plus'].mean():.1f}")

    print(f"\nTotal with Ambulatory Difficulty:")
    print(f"  Min: {annotated_df['total_amb_diff'].min()}")
    print(f"  Max: {annotated_df['total_amb_diff'].max()}")
    print(f"  Mean: {annotated_df['total_amb_diff'].mean():.1f}")

    print(f"\nPercentage with Ambulatory Difficulty:")
    print(f"  Min: {annotated_df['total_amb_diff_pct'].min():.2f}%")
    print(f"  Max: {annotated_df['total_amb_diff_pct'].max():.2f}%")
    print(f"  Mean: {annotated_df['total_amb_diff_pct'].mean():.2f}%")

    print(f"\nPopulation 65+:")
    print(f"  Min: {annotated_df['pop_65plus'].min()}")
    print(f"  Max: {annotated_df['pop_65plus'].max()}")
    print(f"  Mean: {annotated_df['pop_65plus'].mean():.1f}")

    print(f"\nPopulation 65+ with Ambulatory Difficulty:")
    print(f"  Min: {annotated_df['pop_65plus_amb_diff'].min()}")
    print(f"  Max: {annotated_df['pop_65plus_amb_diff'].max()}")
    print(f"  Mean: {annotated_df['pop_65plus_amb_diff'].mean():.1f}")

    print(f"\nPercentage 65+ with Ambulatory Difficulty:")
    print(f"  Min: {annotated_df['pop_65plus_amb_diff_pct'].min():.2f}%")
    print(f"  Max: {annotated_df['pop_65plus_amb_diff_pct'].max():.2f}%")
    print(f"  Mean: {annotated_df['pop_65plus_amb_diff_pct'].mean():.2f}%")

    # Display first few rows
    print("\n=== First 3 rows of annotated data ===")
    print(annotated_df.head(3).to_string())

    # Save to new CSV
    output_file = GENERATED_DIR / 'tracts_within_1mile_annotated.csv'
    annotated_df.to_csv(output_file, index=False)
    print(f"\n✓ Saved annotated data to {output_file}")

    # Data quality checks
    print("\n=== Data Quality Checks ===")
    errors = []

    # Check for negative values
    numeric_cols = ['total_pop_5plus', 'total_amb_diff', 'pop_65plus', 'pop_65plus_amb_diff']
    for col in numeric_cols:
        if (annotated_df[col] < 0).any():
            errors.append(f"ERROR: Negative values found in {col}")

    # Check for ambulatory difficulty > total population
    if (annotated_df['total_amb_diff'] > annotated_df['total_pop_5plus']).any():
        errors.append("ERROR: Total ambulatory difficulty exceeds total population")

    if (annotated_df['pop_65plus_amb_diff'] > annotated_df['pop_65plus']).any():
        errors.append("ERROR: 65+ ambulatory difficulty exceeds 65+ population")

    # Check for 65+ pop > total pop
    if (annotated_df['pop_65plus'] > annotated_df['total_pop_5plus']).any():
        errors.append("ERROR: 65+ population exceeds total population")

    # Check for percentages > 100
    if (annotated_df['total_amb_diff_pct'] > 100).any():
        errors.append("ERROR: Total ambulatory difficulty percentage exceeds 100%")

    if (annotated_df['pop_65plus_amb_diff_pct'] > 100).any():
        errors.append("ERROR: 65+ ambulatory difficulty percentage exceeds 100%")

    if errors:
        print("\n".join(errors))
        sys.exit(1)
    else:
        print("✓ All data quality checks passed!")
        print("✓ No errors found in the data")

if __name__ == '__main__':
    main()
