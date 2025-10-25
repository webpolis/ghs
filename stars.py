#!/usr/bin/env python3
"""
GitHub Stars Organizer - Unified CLI tool
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from src.github_client import GitHubStarsFetcher
from src.readme_parser import ReadmeFetcher
from src.embeddings import EmbeddingGenerator
from src.database import StarDatabase


def require_github_token():
    load_dotenv()
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN not found in environment variables.")
        print("Please create a .env file with your GitHub token.")
        print("See .env.example for reference.")
        sys.exit(1)
    return github_token


def fetch_readme_for_repo(repo, readme_fetcher):
    """Fetch README for a single repository (I/O bound)"""
    readme_content, readme_type = readme_fetcher.fetch_readme(
        repo["owner"],
        repo["name"]
    )

    if readme_content:
        readme_content = readme_fetcher.parse_content(readme_content, readme_type)

    return {
        "repo": repo,
        "readme_content": readme_content,
        "readme_type": readme_type
    }


def process_repository(repo_data, db, embedding_generator):
    """Process repository with README already fetched"""
    repo = repo_data["repo"]
    readme_content = repo_data["readme_content"]
    readme_type = repo_data["readme_type"]

    embedding = embedding_generator.generate_embedding(
        title=repo["full_name"],
        description=repo["description"],
        readme=readme_content
    )

    db.insert_repository(
        repo_id=repo["id"],
        full_name=repo["full_name"],
        name=repo["name"],
        description=repo["description"],
        url=repo["url"],
        stars=repo["stars"],
        language=repo["language"],
        created_at=repo["created_at"],
        updated_at=repo["updated_at"],
        readme_content=readme_content,
        readme_type=readme_type,
        embedding=embedding
    )


def cmd_fetch(args):
    github_token = require_github_token()

    print("Initializing GitHub Stars Organizer...")
    print("=" * 60)

    db = StarDatabase()
    github_client = GitHubStarsFetcher(github_token)
    readme_fetcher = ReadmeFetcher(github_token)
    embedding_generator = EmbeddingGenerator()

    # Display rate limit status
    rate_limit = github_client.get_rate_limit_status()
    if rate_limit:
        print(f"\nGitHub API Rate Limit:")
        print(f"  Remaining: {rate_limit['remaining']}/{rate_limit['limit']}")
        if rate_limit['reset_in_seconds'] > 0:
            print(f"  Resets in: {rate_limit['reset_in_seconds']}s ({rate_limit['reset_in_seconds']//60}min)")

    print(f"\nFetching starred repositories for user: {github_client.get_username()}")
    starred_repos = github_client.get_starred_repositories()
    print(f"Found {len(starred_repos)} starred repositories")

    stats_before = db.get_statistics()
    print(f"\nDatabase statistics (before):")
    print(f"  Total repositories: {stats_before['total_repositories']}")
    print(f"  Embedded repositories: {stats_before['embedded_repositories']}")
    print(f"  Repositories with README: {stats_before['repositories_with_readme']}")

    # Filter out repos that already exist
    repos_to_process = [repo for repo in starred_repos if not db.repository_exists(repo["id"])]
    skipped_repos = len(starred_repos) - len(repos_to_process)

    print(f"\nRepositories to process: {len(repos_to_process)}")
    print(f"Repositories already stored: {skipped_repos}")

    if not repos_to_process:
        print("\nNo new repositories to process!")
        github_client.close()
        db.close()
        return

    # Use fewer workers to avoid rate limiting (5000 req/hour = ~83 req/min = ~1.4 req/sec)
    max_workers = min(5, len(repos_to_process))
    print(f"\nFetching READMEs in parallel (using {max_workers} workers)...")
    print("-" * 60)

    # Phase 1: Fetch READMEs in parallel (I/O bound)
    repos_with_readmes = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_repo = {
            executor.submit(fetch_readme_for_repo, repo, readme_fetcher): repo
            for repo in repos_to_process
        }

        with tqdm(total=len(repos_to_process), desc="Fetching READMEs", unit="repo",
                  bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:
            for future in as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    repo_data = future.result()
                    repos_with_readmes.append(repo_data)
                    pbar.set_postfix_str(f"✓ {repo['full_name']}", refresh=True)
                except Exception as e:
                    pbar.set_postfix_str(f"✗ {repo['full_name']}", refresh=True)
                    print(f"\n⚠️  Error fetching README for {repo['url']}: {e}")
                finally:
                    pbar.update(1)

    # Phase 2: Generate embeddings and store in database (CPU bound, done sequentially for now)
    print(f"\nGenerating embeddings and storing...")
    print("-" * 60)

    new_repos = 0
    with tqdm(total=len(repos_with_readmes), desc="Processing repos", unit="repo",
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:
        for repo_data in repos_with_readmes:
            repo = repo_data['repo']
            try:
                pbar.set_postfix_str(f"⚙️  {repo['full_name']}", refresh=True)
                process_repository(repo_data, db, embedding_generator)
                new_repos += 1
                pbar.set_postfix_str(f"✓ {repo['full_name']}", refresh=True)
            except Exception as e:
                pbar.set_postfix_str(f"✗ {repo['full_name']}", refresh=True)
                print(f"\n⚠️  Error processing {repo['url']}: {e}")
            finally:
                pbar.update(1)

    print(f"\n{'=' * 60}")
    print(f"Processing complete!")
    print(f"  New repositories added: {new_repos}")
    print(f"  Skipped (already stored): {skipped_repos}")

    stats_after = db.get_statistics()
    print(f"\nDatabase statistics (after):")
    print(f"  Total repositories: {stats_after['total_repositories']}")
    print(f"  Embedded repositories: {stats_after['embedded_repositories']}")
    print(f"  Repositories with README: {stats_after['repositories_with_readme']}")

    github_client.close()
    db.close()

    print(f"\nDatabase saved to: stars.db")


def cmd_search(args):
    if not args.query:
        print("Error: Please provide a search query")
        sys.exit(1)

    query = " ".join(args.query)

    print(f"Searching for: '{query}'")
    print("=" * 60)

    db = StarDatabase()
    embedding_generator = EmbeddingGenerator()

    query_embedding = embedding_generator.generate_query_embedding(query)
    results = db.search_similar(query_embedding, limit=args.limit)

    if not results:
        print("No results found. Run 'stars fetch' first to populate the database.")
    else:
        print(f"\nTop {len(results)} matching repositories:\n")

        for i, (repo_id, full_name, description, url, stars, distance) in enumerate(results, 1):
            print(f"{i}. {full_name}")
            print(f"   ⭐ {stars} stars")
            if description:
                print(f"   📝 {description}")
            print(f"   🔗 {url}")
            print(f"   📊 Distance: {distance:.4f}")
            print()

    db.close()


def cmd_refresh(args):
    github_token = require_github_token()

    print("Refreshing GitHub Stars Database...")
    print("=" * 60)

    db = StarDatabase()
    github_client = GitHubStarsFetcher(github_token)
    readme_fetcher = ReadmeFetcher(github_token)
    embedding_generator = EmbeddingGenerator()

    # Display rate limit status
    rate_limit = github_client.get_rate_limit_status()
    if rate_limit:
        print(f"\nGitHub API Rate Limit:")
        print(f"  Remaining: {rate_limit['remaining']}/{rate_limit['limit']}")
        if rate_limit['reset_in_seconds'] > 0:
            print(f"  Resets in: {rate_limit['reset_in_seconds']}s ({rate_limit['reset_in_seconds']//60}min)")

    print(f"\nFetching current starred repositories for user: {github_client.get_username()}")
    current_starred = github_client.get_starred_repositories()
    current_starred_ids = {repo["id"] for repo in current_starred}
    print(f"Found {len(current_starred)} starred repositories")

    print("\nChecking database for changes...")
    existing_ids = set(db.get_all_repo_ids())

    new_stars = [repo for repo in current_starred if repo["id"] not in existing_ids]
    removed_stars = existing_ids - current_starred_ids

    print(f"\nChanges detected:")
    print(f"  New stars: {len(new_stars)}")
    print(f"  Removed stars: {len(removed_stars)}")

    if not new_stars and not removed_stars:
        print("\nNo changes detected. Database is up to date!")
        github_client.close()
        db.close()
        return

    if removed_stars:
        print(f"\nRemoving {len(removed_stars)} unstarred repositories...")
        for repo_id in tqdm(removed_stars, desc="Removing", unit="repo"):
            db.delete_repository(repo_id)

    if new_stars:
        max_workers = min(5, len(new_stars))
        print(f"\nFetching READMEs for {len(new_stars)} new repositories (using {max_workers} workers)...")

        # Phase 1: Fetch READMEs in parallel
        repos_with_readmes = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_repo = {
                executor.submit(fetch_readme_for_repo, repo, readme_fetcher): repo
                for repo in new_stars
            }

            with tqdm(total=len(new_stars), desc="Fetching READMEs", unit="repo",
                      bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:
                for future in as_completed(future_to_repo):
                    repo = future_to_repo[future]
                    try:
                        repo_data = future.result()
                        repos_with_readmes.append(repo_data)
                        pbar.set_postfix_str(f"✓ {repo['full_name']}", refresh=True)
                    except Exception as e:
                        pbar.set_postfix_str(f"✗ {repo['full_name']}", refresh=True)
                        print(f"\n⚠️  Error fetching README for {repo['url']}: {e}")
                    finally:
                        pbar.update(1)

        # Phase 2: Generate embeddings and store
        print(f"\nGenerating embeddings and storing...")
        with tqdm(total=len(repos_with_readmes), desc="Processing", unit="repo",
                  bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:
            for repo_data in repos_with_readmes:
                repo = repo_data['repo']
                try:
                    pbar.set_postfix_str(f"⚙️  {repo['full_name']}", refresh=True)
                    process_repository(repo_data, db, embedding_generator)
                    pbar.set_postfix_str(f"✓ {repo['full_name']}", refresh=True)
                except Exception as e:
                    pbar.set_postfix_str(f"✗ {repo['full_name']}", refresh=True)
                    print(f"\n⚠️  Error processing {repo['url']}: {e}")
                finally:
                    pbar.update(1)

    stats_after = db.get_statistics()
    print(f"\n{'=' * 60}")
    print(f"Refresh complete!")
    print(f"\nDatabase statistics:")
    print(f"  Total repositories: {stats_after['total_repositories']}")
    print(f"  Embedded repositories: {stats_after['embedded_repositories']}")
    print(f"  Repositories with README: {stats_after['repositories_with_readme']}")

    github_client.close()
    db.close()


def cmd_stats(args):
    if not os.path.exists("stars.db"):
        print("Database not found. Run 'stars fetch' first to create it.")
        sys.exit(1)

    db = StarDatabase()

    stats = db.get_statistics()

    print("GitHub Stars Database Statistics")
    print("=" * 60)
    print(f"Total repositories: {stats['total_repositories']}")
    print(f"Embedded repositories: {stats['embedded_repositories']}")
    print(f"Repositories with README: {stats['repositories_with_readme']}")

    if stats['total_repositories'] > 0:
        readme_percentage = (stats['repositories_with_readme'] / stats['total_repositories']) * 100
        print(f"README coverage: {readme_percentage:.1f}%")

    db.close()


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Stars Organizer - Semantic search for your starred repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  stars fetch                          # Fetch and index all starred repos
  stars search "machine learning"      # Search for repos
  stars refresh                        # Sync added/removed stars
  stars stats                          # Show database statistics
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch and index all starred repositories")

    search_parser = subparsers.add_parser("search", help="Search for repositories by semantic similarity")
    search_parser.add_argument("query", nargs="+", help="Search query")
    search_parser.add_argument("-l", "--limit", type=int, default=10, help="Number of results to return (default: 10)")

    refresh_parser = subparsers.add_parser("refresh", help="Refresh database by syncing added/removed stars")

    stats_parser = subparsers.add_parser("stats", help="Show database statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "fetch": cmd_fetch,
        "search": cmd_search,
        "refresh": cmd_refresh,
        "stats": cmd_stats
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
