"""Run one or more Resolver element-usage searches with resolver_sdk."""

import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd
from resolver_sdk import ResolverClient

import logging
logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s %(levelname)s %(name)s : %(message)s"
)

logger = logging.getLogger(__name__)

from elementSearches import (
    dataDefinitionSearch, fieldSearch, formSearch, formulaSearch,
    lifecycleElementSearch, objectTypeGroupSearch, objectTypeSearch,
    reportSearch, roleSearch
)

SEARCHES = {
    "object-types": objectTypeSearch, "object-type-groups": objectTypeGroupSearch,
    "data-definitions": dataDefinitionSearch, "fields": fieldSearch,
    "formula": formulaSearch,  "forms": formSearch,"reports": reportSearch, 
    "lifecycle-elements": lifecycleElementSearch, "roles": roleSearch,
}
from dotenv import load_dotenv

load_dotenv()
AVAILABLE_ENVS = {
    "Deploy 2": os.getenv("DEPLOY_2"),
}



def upload_results(results, tag):
    """Write every selected search's used and unused rows to one timestamped workbook."""
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    filename = output_dir / f"{tag}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        for name, (used, unused) in results.items():
            if isinstance(used, dict):
                for part, rows in used.items():
                    if part.startswith("_"):
                        continue
                    if part == "orchestration_events":
                        pd.DataFrame(rows).to_excel(writer, sheet_name="Orchestration Events", index=False)
                        continue
                    if part == "consume_orchestration_events":
                        pd.DataFrame(rows).to_excel(writer, sheet_name="Consume Orchestration Events", index=False)
                        continue
                    pd.DataFrame(rows).to_excel(writer, sheet_name=f"Used{part.title()}"[:31], index=False)
                    pd.DataFrame(unused[part]).to_excel(writer, sheet_name=f"Unused{part.title()}"[:31], index=False)
            else:
                pd.DataFrame(used).to_excel(writer, sheet_name=f"Used{name}"[:31], index=False)
                pd.DataFrame(unused).to_excel(writer, sheet_name=f"Unused{name}"[:31], index=False)
    print(f"Results saved to {filename}")
    return filename


def build_client(base_url, api_key):
    return ResolverClient(base_url=base_url, api_key=api_key)


def run_search(module, base_url, api_key, include_orchestration_events=False):
    client = build_client(base_url, api_key)
    if module is lifecycleElementSearch:
        result = module.search(client, include_orchestration_events=include_orchestration_events)
    else:
        result = module.search(client)
    return result, client.get_api_calls()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", help="Label printed for this Resolver environment.")
    parser.add_argument("--base-url", default=os.getenv("RESOLVER_BASE_URL"))
    parser.add_argument("--api-key", default=os.getenv("RESOLVER_API_KEY"))
    parser.add_argument("--search", nargs="+", choices=SEARCHES, help="One or more searches to run.")
    parser.add_argument("--upload", action="store_true", help="Write all result rows to an Excel workbook.")
    parser.add_argument(
        "--orchestration-events",
        action="store_true",
        help="Add orchestration event and consuming orchestration event tracing results to lifecycle output.",
    )
    parser.add_argument("--tag", default="element_search", help="Prefix for the Excel workbook.")
    return parser.parse_args()


def main():
    args = parse_args()
    environment = args.environment or input("Environment label: ").strip()
    base_url = args.base_url or os.getenv("PRODUCTION_BASE_URL" if input("Sandbox or Production environment? (S/P): ").strip().lower() in ("p", "production") else "SANDBOX_BASE_URL")
    api_key = args.api_key or AVAILABLE_ENVS.get(input(f"Select Resolver Environment ({', '.join(AVAILABLE_ENVS)}): ").strip())
    selected = args.search or input(f"Searches ({', '.join(SEARCHES)}), comma-separated: ").replace(" ", "").split(",")
    if "lifecycle-elements" in selected and not args.orchestration_events:
        include_orchestration_events = input("Include orchestration event tracing? [y/N]: ").strip().lower() in {"y", "yes"}
        args.orchestration_events = include_orchestration_events
    invalid = set(selected) - SEARCHES.keys()
    if invalid:
        raise SystemExit(f"Unknown search name(s): {', '.join(sorted(invalid))}")
    upload = args.upload or input("Upload results to Excel? [y/N]: ").strip().lower() in {"y", "yes"}
    print(f"Running {', '.join(selected)} against {environment}.")
    results, calls = {}, 0
    with ThreadPoolExecutor(max_workers=len(selected)) as executor:
        futures = {
            executor.submit(
                run_search,
                module=SEARCHES[name],
                base_url=base_url,
                api_key=api_key,
                include_orchestration_events=args.orchestration_events,
            ): name
            for name in selected
        }
        for future in as_completed(futures):
            name = futures[future]
            results[name], count = future.result()
            calls += count
            print(f"Completed {name}.")
    if upload:
        upload_results(results, args.tag)
    print(f"Total API calls: {calls}")


if __name__ == "__main__":
    main()
