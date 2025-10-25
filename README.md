# StarSearch: Semantic Search for GitHub Stars

A command-line tool to semantically search your starred GitHub repositories.

**¿WHY?** If you are like me, who goes **starring** repositories as a way to bookmark them, but you later find it hard to recall a specific tool or library due to the archaic search feature in **GitHub**, which does not do semantic similarity search, then this tool is for you.

## Features

- Unified command-line interface with intuitive subcommands
- Fetches all starred repositories from your GitHub profile
- **Parallel processing** with 5 concurrent workers for fast README fetching
- **Intelligent rate limit handling** - automatically detects and waits for GitHub API limits to reset
- Extracts and parses README files (supports .md, .txt, and plain README)
- Generates embeddings using a lightweight sentence-transformer model (all-MiniLM-L6-v2)
- Stores data efficiently using sqlite-vec for fast vector similarity search
- Smart refresh command to sync added/removed stars
- Semantic search to find repositories by meaning, not just keywords
- Real-time progress feedback showing currently processing repositories

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
1. Check your GitHub API rate limit status
2. Fetch all your starred repositories from GitHub
3. Download and parse their READMEs in parallel (5 concurrent workers)
4. Generate embeddings using the all-MiniLM-L6-v2 model (384-dimensional)
5. Store everything in a local SQLite database with vector search capabilities
6. Skip repositories that are already stored

**Rate Limiting:** The tool automatically monitors GitHub API rate limits and will pause with a clear message if limits are reached, then resume when they reset.

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

1. **GitHub API**: Uses PyGithub to fetch your starred repositories with intelligent rate limit handling
2. **Parallel README Fetching**: Downloads READMEs using 5 concurrent workers with shared rate limit detection
3. **README Extraction**: Uses GitHub's dedicated README API endpoint for efficient fetching
4. **Embeddings**: Uses sentence-transformers (all-MiniLM-L6-v2) to generate 384-dim vectors
5. **Vector Search**: Stores embeddings in sqlite-vec for fast similarity search using cosine distance
6. **Smart Sync**: Refresh command intelligently adds/removes repositories based on current stars
7. **Rate Limit Protection**: Automatically detects rate limits, displays clear wait times, and resumes when ready

## Database Schema

The tool creates a `stars.db` SQLite database with:

**repositories table:**
- Repository metadata (id, name, description, URL, stars, language)
- README content and type
- Timestamps

**vec_repositories table (virtual):**
- Vector embeddings for semantic search
- Linked to repositories via repo_id
