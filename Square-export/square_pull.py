"""
Texas Ranchers — Square Orders Pull
Pulls completed orders + line items from both Square locations (Main, Ranchers
Academy), tags each row with its location, and appends new rows to a Google
Sheet. Dedupes against an existing "Order ID + Line UID" combo so re-runs
don't double-count.

Run manually, same pattern as the Stripe pull script.
"""

import os
import uuid
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from square import Square

load_dotenv()

# ---------------------------------------------------------------------------
# CONFIG — fill in via .env, never hardcode tokens here
# ---------------------------------------------------------------------------
SQUARE_ACCESS_TOKEN = os.environ["SQUARE_ACCESS_TOKEN"]  # set in .env
GOOGLE_SHEET_ID = os.environ.get("SQUARE_SHEET_ID", "PASTE_SHEET_ID_HERE")
GOOGLE_CREDS_PATH = os.environ.get("GOOGLE_CREDS_PATH", "service_account.json")

# Both locations confirmed from Square dashboard
LOCATIONS = {
    "LWR7YY2PKWKQY": "Main",
    "LTWTYAMJDX909": "Ranchers Academy",
}

# Pull window — adjust as needed. Start with a wide backfill window once,
# then narrow to "since last run" for ongoing pulls.
START_AT = "2025-01-01T00:00:00Z"
END_AT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

SHEET_TAB_NAME = "Square Orders"

# Column order written to the sheet — mirrors the Shopify Orders tab shape
# where it makes sense, so downstream ETL can treat them consistently.
COLUMNS = [
    "Order ID",          # Square order id
    "Line UID",           # line item uid within the order — dedup key part 2
    "Location",           # "Main" or "Ranchers Academy"
    "Created At",          # order created_at, ISO
    "Closed At",           # order closed_at, ISO
    "Line Item Title",      # line item name
    "Quantity",
    "Gross Sales",          # line item gross_sales_money, dollars
    "Discounts",            # line item total_discount_money, dollars
    "Net Revenue",          # line item total_money minus any return, dollars
    "Catalog Object ID",    # for later category mapping once buckets are decided
    "Customer ID",          # often blank for in-person POS
    "Source",                # state/order source if useful later
]


def money_to_dollars(money_obj):
    """Square amounts are integer cents. Returns None-safe dollar float."""
    if not money_obj:
        return 0.0
    return money_obj.get("amount", 0) / 100.0


def fetch_all_orders(client, location_ids, start_at, end_at):
    """Pages through SearchOrders for the given locations and date window."""
    orders = []
    cursor = None

    while True:
        body = {
            "location_ids": location_ids,
            "query": {
                "filter": {
                    "state_filter": {"states": ["COMPLETED"]},
                    "date_time_filter": {
                        "closed_at": {"start_at": start_at, "end_at": end_at}
                    },
                },
                "sort": {"sort_field": "CLOSED_AT", "sort_order": "ASC"},
            },
            "limit": 100,
        }
        if cursor:
            body["cursor"] = cursor

        response = client.orders.search(**body)

        page_orders = response.orders if hasattr(response, "orders") else []
        orders.extend(page_orders)

        cursor = getattr(response, "cursor", None)
        if not cursor:
            break

    return orders


def flatten_order_to_rows(order, location_lookup):
    """One Square order -> one row per line item."""
    rows = []
    order_id = order.id
    location_id = order.location_id
    location_name = location_lookup.get(location_id, location_id)
    created_at = order.created_at
    closed_at = getattr(order, "closed_at", None)
    customer_id = getattr(order, "customer_id", None) or ""
    source = getattr(getattr(order, "source", None), "name", "") or ""

    line_items = getattr(order, "line_items", None) or []

    for li in line_items:
        rows.append({
            "Order ID": order_id,
            "Line UID": getattr(li, "uid", str(uuid.uuid4())),
            "Location": location_name,
            "Created At": created_at,
            "Closed At": closed_at,
            "Line Item Title": getattr(li, "name", ""),
            "Quantity": getattr(li, "quantity", ""),
            "Gross Sales": money_to_dollars(getattr(li, "gross_sales_money", None)),
            "Discounts": money_to_dollars(getattr(li, "total_discount_money", None)),
            "Net Revenue": money_to_dollars(getattr(li, "total_money", None)),
            "Catalog Object ID": getattr(li, "catalog_object_id", "") or "",
            "Customer ID": customer_id,
            "Source": source,
        })

    return rows


def get_existing_keys(worksheet):
    """Builds a set of 'Order ID|Line UID' strings already in the sheet."""
    records = worksheet.get_all_records()
    return {f"{r.get('Order ID')}|{r.get('Line UID')}" for r in records}


def main():
    client = Square(token=SQUARE_ACCESS_TOKEN)

    # Sanity check: confirm location IDs match what's expected before pulling
    loc_response = client.locations.list()
    found_ids = {loc.id for loc in loc_response.locations}
    expected_ids = set(LOCATIONS.keys())
    if not expected_ids.issubset(found_ids):
        missing = expected_ids - found_ids
        raise SystemExit(
            f"Expected location IDs not found on this account: {missing}. "
            f"Found: {found_ids}"
        )
    print(f"Confirmed locations: {LOCATIONS}")

    print(f"Pulling orders from {START_AT} to {END_AT}...")
    orders = fetch_all_orders(client, list(LOCATIONS.keys()), START_AT, END_AT)
    print(f"Fetched {len(orders)} orders.")

    all_rows = []
    for order in orders:
        all_rows.extend(flatten_order_to_rows(order, LOCATIONS))
    print(f"Flattened to {len(all_rows)} line-item rows.")

    # --- Google Sheets connection ---
    creds = Credentials.from_service_account_file(
        GOOGLE_CREDS_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(GOOGLE_SHEET_ID)

    try:
        ws = sh.worksheet(SHEET_TAB_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_TAB_NAME, rows=1000, cols=len(COLUMNS))
        ws.append_row(COLUMNS)
        print(f"Created new tab: {SHEET_TAB_NAME}")

    existing_keys = get_existing_keys(ws)
    print(f"{len(existing_keys)} rows already in sheet, deduping against those.")

    new_rows = [
        row for row in all_rows
        if f"{row['Order ID']}|{row['Line UID']}" not in existing_keys
    ]
    print(f"{len(new_rows)} new rows to write.")

    if new_rows:
        values = [[row.get(col, "") for col in COLUMNS] for row in new_rows]
        ws.append_rows(values, value_input_option="USER_ENTERED")
        print(f"Wrote {len(new_rows)} rows to '{SHEET_TAB_NAME}'.")
    else:
        print("Nothing new to write.")


if __name__ == "__main__":
    main()
