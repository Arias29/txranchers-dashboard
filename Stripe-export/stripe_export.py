import os
import time
import stripe
import gspread
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_API_KEY")
stripe.max_network_retries = 5


def main():
    print("Authenticating with Google Sheets...")
    gc = gspread.service_account(filename=os.getenv("GOOGLE_CREDENTIALS_PATH"))
    worksheet = gc.open(os.getenv("GOOGLE_SHEET_NAME")).worksheet("Sheet1")

    existing_ids = set(worksheet.col_values(1))
    print(f"Loaded {len(existing_ids)} existing charge IDs from sheet.\n")

    for charge in stripe.Charge.list(
        expand=["data.customer", "data.payment_intent"]
    ).auto_paging_iter():
        print(f"Processing charge {charge.id}")
        try:
            if charge.id in existing_ids:
                print("  Skipping — already exists")
                continue

            if not charge.payment_intent:
                print("  No payment intent — skipping")
                continue

            pi_id = (
                charge.payment_intent.id
                if hasattr(charge.payment_intent, "id")
                else charge.payment_intent
            )

            sessions = stripe.checkout.Session.list(payment_intent=pi_id, limit=1)
            if not sessions.data:
                print("  No session found — skipping")
                continue
            session = sessions.data[0]

            line_items = stripe.checkout.Session.list_line_items(
                session.id, expand=["data.price.product"]
            )

            customer = charge.customer
            customer_name = ""
            customer_email = ""
            customer_city = ""
            customer_state = ""
            if customer and hasattr(customer, "name"):
                customer_name = customer.name or ""
                customer_email = customer.email or ""
                if customer.address:
                    customer_city = customer.address.city or ""
                    customer_state = customer.address.state or ""

            created_str = datetime.fromtimestamp(charge.created, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            amount = charge.amount / 100
            amount_refunded = charge.amount_refunded / 100

            rows = []
            for item in line_items.data:
                event_date = ""
                if item.price and item.price.product and hasattr(item.price.product, "description"):
                    event_date = item.price.product.description or ""

                unit_price = item.price.unit_amount / 100 if item.price and item.price.unit_amount else 0
                discount = item.amount_discount / 100 if item.amount_discount else 0

                rows.append([
                    charge.id,
                    customer_name,
                    customer_email,
                    customer_city,
                    customer_state,
                    created_str,
                    amount,
                    amount_refunded,
                    item.description or "",
                    event_date,
                    item.quantity,
                    unit_price,
                    discount,
                ])

            if rows:
                worksheet.append_rows(rows, value_input_option="RAW")
                print(f"  Writing {len(rows)} row(s)")
            else:
                print("  No line items — skipping")

        except Exception as e:
            print(f"  Error on {charge.id}: {e}")
            continue

        time.sleep(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
