import argparse


def parse_arguments():
    """Parses command-line arguments for pipeline control."""
    parser = argparse.ArgumentParser(description="Portfolio Analyzer & EOD Pipeline Engine")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["debug", "full"],
        default="debug",
        help="Execution mode: 'debug' uses a minimal 10-stock list, 'full' runs the Nifty 750 universe."
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all intermediate cache files in data/cache/ before starting."
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip syncing computed dataframes to Supabase PostgreSQL."
    )
    parser.add_argument(
        "--skip-notifications",
        action="store_true",
        help="Skip sending Discord webhooks and email alerts."
    )
    return parser.parse_args()