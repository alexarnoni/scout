from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download SofaScore rounds JSON.")
    parser.add_argument("--unique-tournament-id", type=int, default=372)
    parser.add_argument("--season-id", type=int, default=86993)
    parser.add_argument("--round", type=int)
    parser.add_argument("--round-from", type=int)
    parser.add_argument("--round-to", type=int)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
    )
    parser.add_argument("--cookies-file", type=Path)
    parser.add_argument("--user-agent", type=str)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def round_url(unique_tournament_id: int, season_id: int, round_number: int) -> str:
    return (
        "https://www.sofascore.com/api/v1/unique-tournament/"
        f"{unique_tournament_id}/season/{season_id}/events/round/{round_number}"
    )


def output_path(output_dir: Path, round_number: int) -> Path:
    return output_dir / f"sofascore_round_{round_number:03d}.json"


def load_cookie_header(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("cookies file is empty")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict) and "Cookie" in payload:
        return str(payload["Cookie"]).strip()
    for line in text.splitlines():
        if "Cookie:" in line:
            return line.split("Cookie:", 1)[1].strip()
    raise ValueError("cookies file missing Cookie header")


def fetch_round(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
) -> dict:
    response = client.get(url, headers=headers)
    if response.status_code == 403:
        raise PermissionError(
            "403: SofaScore blocked this request. Export Cookie from browser DevTools "
            "and pass --cookies-file ..."
        )
    response.raise_for_status()
    return response.json()


def iter_rounds(args: argparse.Namespace) -> list[int] | None:
    if args.round is not None:
        return [args.round]
    if args.round_from is not None or args.round_to is not None:
        if args.round_from is None or args.round_to is None:
            raise ValueError("--round-from and --round-to must be used together")
        if args.round_to < args.round_from:
            raise ValueError("--round-to must be >= --round-from")
        return list(range(args.round_from, args.round_to + 1))
    return None


def main() -> int:
    args = parse_args()

    headers = {
        "Accept": "*/*",
        "Referer": (
            "https://www.sofascore.com/pt/torneio/futebol/brazil/"
            f"paulista-serie-a1/{args.unique_tournament_id}"
        ),
        "User-Agent": args.user_agent or DEFAULT_USER_AGENT,
    }

    if args.cookies_file:
        try:
            headers["Cookie"] = load_cookie_header(args.cookies_file)
        except Exception as exc:
            print(f"Invalid cookies file: {exc}", file=sys.stderr)
            return 1

    rounds = iter_rounds(args)
    if not args.dry_run:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with httpx.Client(timeout=20) as client:
            if rounds is None:
                round_number = 1
                while True:
                    url = round_url(args.unique_tournament_id, args.season_id, round_number)
                    if args.verbose:
                        print(f"GET {url}")
                    try:
                        payload = fetch_round(client, url, headers)
                    except PermissionError as exc:
                        print(str(exc), file=sys.stderr)
                        return 1
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code == 404:
                            break
                        print(
                            f"HTTP error {exc.response.status_code} for URL: {url}",
                            file=sys.stderr,
                        )
                        return 1
                    except httpx.RequestError as exc:
                        print(f"Connection error for URL: {url}: {exc}", file=sys.stderr)
                        return 1
                    except ValueError as exc:
                        print(f"Invalid JSON for URL: {url}: {exc}", file=sys.stderr)
                        return 1

                    out_path = output_path(args.output_dir, round_number)
                    if args.dry_run:
                        print(f"DRY-RUN would write: {out_path}")
                    else:
                        out_path.write_text(
                            json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
                        if args.verbose:
                            print(f"Wrote {out_path}")
                    round_number += 1
            else:
                for round_number in rounds:
                    url = round_url(args.unique_tournament_id, args.season_id, round_number)
                    if args.verbose:
                        print(f"GET {url}")
                    try:
                        payload = fetch_round(client, url, headers)
                    except PermissionError as exc:
                        print(str(exc), file=sys.stderr)
                        return 1
                    except httpx.HTTPStatusError as exc:
                        print(
                            f"HTTP error {exc.response.status_code} for URL: {url}",
                            file=sys.stderr,
                        )
                        return 1
                    except httpx.RequestError as exc:
                        print(f"Connection error for URL: {url}: {exc}", file=sys.stderr)
                        return 1
                    except ValueError as exc:
                        print(f"Invalid JSON for URL: {url}: {exc}", file=sys.stderr)
                        return 1

                    out_path = output_path(args.output_dir, round_number)
                    if args.dry_run:
                        print(f"DRY-RUN would write: {out_path}")
                    else:
                        out_path.write_text(
                            json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
                        if args.verbose:
                            print(f"Wrote {out_path}")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
