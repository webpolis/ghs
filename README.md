# GitHub Stars Organizer

A Python CLI tool that organizes your GitHub starred repositories using semantic embeddings and vector search.

**WHY?** If you are like me, who goes **starring** repositories as a way to bookmark them, but you later find it hard to recall a specific tool or library due to the archaic search feature in **GitHub**, which does not do semantic similarity search, then this tool is for you.

## Features

- Unified command-line interface with intuitive subcommands
- Fetches all starred repositories from your GitHub profile
- Extracts and parses README files (supports .md, .txt, and plain README)
- Generates embeddings using a lightweight sentence-transformer model (all-MiniLM-L6-v2)
- Stores data efficiently using sqlite-vec for fast vector similarity search
- Smart refresh command to sync added/removed stars
- Semantic search to find repositories by meaning, not just keywords

## Setup

1. Install dependencies:
```bash
# For CPU-only installation (faster, no CUDA overhead):
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Or for GPU support (if you have CUDA):
pip install -r requirements.txt
```

2. Create a GitHub Personal Access Token:
   - Go to https://github.com/settings/tokens
   - Create a new token with `public_repo` scope
   - Copy the token

3. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your GitHub token
```

## Usage

The tool provides a unified CLI with four main commands:

### Fetch - Initial Indexing

Fetch and index all your starred repositories:

```bash
python stars.py fetch
```

This will:
1. Fetch all your starred repositories from GitHub
2. Download and parse their READMEs (tries .md, .txt, and plain README)
3. Generate embeddings using the all-MiniLM-L6-v2 model (384-dimensional)
4. Store everything in a local SQLite database with vector search capabilities
5. Skip repositories that are already stored

### Search - Semantic Search

Search your stars using natural language queries:

```bash
python stars.py search "your search query"
```

Examples:
```bash
python stars.py search "machine learning frameworks"
python stars.py search "web scraping tools"
python stars.py search "rust web server"
python stars.py search "react component libraries" --limit 5
```

Options:
- `-l, --limit N`: Number of results to return (default: 10)

### Refresh - Sync Changes

Synchronize your database with your current GitHub stars (adds new stars, removes unstarred repositories):

```bash
python stars.py refresh
```

This command:
1. Fetches your current starred repositories
2. Compares with the local database
3. Adds newly starred repositories
4. Removes repositories you've unstarred
5. Shows a summary of changes

### Stats - Database Statistics

Show database statistics:

```bash
python stars.py stats
```

Displays:
- Total repositories indexed
- Number of repositories with embeddings
- Number of repositories with README files
- README coverage percentage

## Command Quick Reference

```bash
python stars.py fetch                   # Initial fetch and index
python stars.py search "query"          # Search repositories
python stars.py search "query" --limit 5  # Limit results
python stars.py refresh                 # Sync added/removed stars
python stars.py stats                   # Show statistics

# Or use the convenience wrapper (no 'python' needed):
./stars fetch
./stars search "machine learning"
```

> **Note**: The old `main.py`, `search.py`, and `stats.py` scripts are still available but deprecated. Use `stars.py` instead for the unified experience.

## How It Works

1. **GitHub API**: Uses PyGithub to fetch your starred repositories
2. **README Extraction**: Tries multiple README file variants and extracts content
3. **Embeddings**: Uses sentence-transformers (all-MiniLM-L6-v2) to generate 384-dim vectors
4. **Vector Search**: Stores embeddings in sqlite-vec for fast similarity search using cosine distance
5. **Smart Sync**: Refresh command intelligently adds/removes repositories based on current stars

## Database Schema

The tool creates a `stars.db` SQLite database with:

**repositories table:**
- Repository metadata (id, name, description, URL, stars, language)
- README content and type
- Timestamps

**vec_repositories table (virtual):**
- Vector embeddings for semantic search
- Linked to repositories via repo_id
