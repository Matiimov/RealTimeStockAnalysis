import argparse, datetime as dt, sys
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

def load_holidays(path="data/us_market_holidays_2025.txt"):
    dates = set()
    try:
        with open(path) as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if not line: continue
                dates.add(dt.date.fromisoformat(line))
    except FileNotFoundError:
        pass
    return dates

def is_open_at(et_dt: dt.datetime, holidays: set[dt.date]) -> tuple[bool,str]:
    d = et_dt.date()
    wd = et_dt.weekday()  # 0=Mon
    if wd > 4:
        return False, "Weekend"
    if d in holidays:
        return False, "US holiday"
    # Regular session 09:31–16:00 ET
    start = et_dt.replace(hour=9, minute=31, second=0, microsecond=0)
    end   = et_dt.replace(hour=16, minute=0, second=0, microsecond=0)
    if not (start <= et_dt < end):
        return False, "Outside regular hours"
    return True, "Open"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--at", help="Time in ET, format: YYYY-MM-DD HH:MM (assumed ET)")
    p.add_argument("--now", action="store_true", help="Check current time (ET)")
    args = p.parse_args()

    holidays = load_holidays()
    if args.now:
        et_dt = dt.datetime.now(ET)
    elif args.at:
        et_dt = dt.datetime.strptime(args.at, "%Y-%m-%d %H:%M").replace(tzinfo=ET)
    else:
        print("usage: --now OR --at 'YYYY-MM-DD HH:MM'", file=sys.stderr)
        sys.exit(2)

    ok, why = is_open_at(et_dt, holidays)
    print("OPEN" if ok else "CLOSED", "-", why, "|", et_dt.isoformat())
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
