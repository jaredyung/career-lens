# CareerLens

CareerLens is a labor-market intelligence dashboard for data careers.

It collects real job postings from the Adzuna API, classifies them into common data career paths, stores the results in DuckDB, and presents interactive analytics through a Streamlit dashboard.

The goal is to help users explore how different data roles compare across salary, hiring companies, locations, and available job postings.

## Features

### Market Overview

CareerLens provides summary metrics for the current dataset, including:

- number of job postings analyzed
- number of hiring companies
- estimated average salary
- estimated median salary

Users can filter the market by:

- job title
- company
- location
- role category
- minimum salary

### Role Intelligence

Job postings are classified into five primary career paths:

- Data Analyst
- Data Scientist
- Data Engineer
- Analytics Engineer
- Machine Learning Engineer

CareerLens allows users to compare roles based on:

- number of sampled job postings
- number of hiring companies
- estimated average salary
- estimated median salary

### Company Intelligence

Users can select an employer and analyze:

- available data job postings
- role categories being hired
- hiring locations
- estimated compensation
- role mix
- individual job postings

### Job Explorer

CareerLens includes a searchable table of job postings with:

- title
- company
- location
- role classification
- posting date
- estimated salary range
- link to the original posting

## Architecture

```text
Adzuna API
    |
    v
Python Ingestion Pipeline
    |
    v
Data Cleaning and Normalization
    |
    v
Role Classification
    |
    v
DuckDB
    |
    v
Analytics
    |
    v
Streamlit Dashboard