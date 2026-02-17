import argparse
import asyncio
import os

from dotenv import load_dotenv

from injestion import run_pipeline


def require_env(keys):
	missing = [k for k in keys if not os.getenv(k)]
	if missing:
		raise SystemExit(
			"Missing required environment variables: " + ", ".join(missing)
		)


def parse_args():
	parser = argparse.ArgumentParser(
		description="Run the ingestion pipeline for a given URL",
	)
	parser.add_argument(
		"url",
		nargs="?",
		default="https://demo.bookstackapp.com/",
		help="Seed URL to crawl (default: https://demo.bookstackapp.com/)"
	)
	parser.add_argument(
		"--max-depth",
		type=int,
		default=5,
		help="Crawler max depth (default: 5)",
	)
	parser.add_argument(
		"--extract-depth",
		type=str,
		default="advanced",
		choices=["basic", "advanced"],
		help="Extraction depth (default: advanced)",
	)
	return parser.parse_args()


async def main():
	# Load env from .env if present
	load_dotenv()

	# Validate required env vars
	require_env(["OPENAI_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX", "TAVILY_API_KEY"])

	args = parse_args()
	await run_pipeline(
		args.url,
		max_depth=args.max_depth,
		extract_depth=args.extract_depth,
	)


if __name__ == "__main__":
	asyncio.run(main())
