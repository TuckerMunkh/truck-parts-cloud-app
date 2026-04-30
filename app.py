import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Truck Parts System", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = "part-photos"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def normalize_sku(sku):
    return sku.strip().upper()


def commission_rate(price):
    if price <= 250:
        return 0.30
    if price <= 1500:
        return 0.20
    return 0.12


st.title("Truck Parts Cloud System")

menu = st.sidebar.selectbox(
    "Menu",
    [
        "Add Vehicle",
        "Add Part",
        "Search Inventory",
        "Build Listing",
        "Log Sale",
        "Truck Profit",
    ],
)

if menu == "Add Vehicle":
    st.header("Add Source Truck / Vehicle")

    with st.form("vehicle_form"):
        vehicle_code = st.text_input("Vehicle Code", placeholder="TRUCK-001")
        vin = st.text_input("VIN")
        year = st.number_input("Year", min_value=1900, max_value=2100, step=1)
        make = st.text_input("Make", placeholder="Freightliner")
        model = st.text_input("Model", placeholder="Cascadia")
        engine = st.text_input("Engine", placeholder="Detroit DD15")
        purchase_price = st.number_input("Purchase Price", min_value=0.0)
        auction_source = st.text_input("Auction Source")
        acquired_at = st.date_input("Acquired Date")
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Save Vehicle")

    if submitted:
        vehicle_clean = vehicle_code.strip().upper()

        if not vehicle_clean:
            st.error("Vehicle code is required.")
        else:
            supabase.table("vehicles").upsert({
                "vehicle_code": vehicle_clean,
                "vin": vin,
                "year": year,
                "make": make,
                "model": model,
                "engine": engine,
                "purchase_price": purchase_price,
                "auction_source": auction_source,
                "acquired_at": str(acquired_at),
                "notes": notes,
            }).execute()

            st.success(f"Saved {vehicle_clean}")

if menu == "Add Part":
    st.header("Add Part")

    vehicles = supabase.table("vehicles").select("vehicle_code, year, make, model").execute().data

    vehicle_options = [""] + [
        f"{v['vehicle_code']} — {v.get('year') or ''} {v.get('make') or ''} {v.get('model') or ''}"
        for v in vehicles
    ]

    with st.form("part_form"):
        sku = st.text_input("SKU", placeholder="CTP-001")

        selected_vehicle = st.selectbox("Source Vehicle", vehicle_options)
        vehicle_code = selected_vehicle.split(" — ")[0] if selected_vehicle else None

        part_name = st.text_input("Part Name")
        category = st.text_input("Category")
        oem_number = st.text_input("OEM Number")
        condition = st.selectbox("Condition", ["Used", "New", "Unknown", "Damaged"])
        shelf_location = st.text_input("Shelf Location")
        ask_price = st.number_input("Ask Price", min_value=0.0)
        min_price = st.number_input("Minimum Price", min_value=0.0)
        notes = st.text_area("Notes")
        photos = st.file_uploader(
            "Upload photos",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
        )

        submitted = st.form_submit_button("Save Part")

    if submitted:
        sku_clean = normalize_sku(sku)

        if not sku_clean:
            st.error("SKU is required.")
        elif not part_name:
            st.error("Part name is required.")
        else:
            supabase.table("parts").upsert({
                "sku": sku_clean,
                "vehicle_code": vehicle_code,
                "part_name": part_name,
                "category": category,
                "oem_number": oem_number,
                "condition": condition,
                "shelf_location": shelf_location,
                "ask_price": ask_price,
                "min_price": min_price,
                "notes": notes,
                "status": "New",
            }).execute()

            for photo in photos:
                file_path = f"{sku_clean.lower()}/{photo.name}"
                file_bytes = photo.getvalue()

                supabase.storage.from_(BUCKET).upload(
                    file_path,
                    file_bytes,
                    {
                        "content-type": photo.type,
                        "upsert": "true",
                    },
                )

                public_url = supabase.storage.from_(BUCKET).get_public_url(file_path)

                supabase.table("part_photos").insert({
                    "sku": sku_clean,
                    "file_path": file_path,
                    "public_url": public_url,
                }).execute()

            st.success(f"Saved {sku_clean}")

if menu == "Search Inventory":
    st.header("Search Inventory")

    search = st.text_input("Search SKU or part name")

    if search:
        parts = supabase.table("parts").select("*").or_(
            f"sku.ilike.%{search}%,part_name.ilike.%{search}%"
        ).execute().data

        for part in parts:
            st.subheader(f"{part['sku']} — {part['part_name']}")
            st.write(part)

            photos = supabase.table("part_photos").select("*").eq(
                "sku", part["sku"]
            ).execute().data

            if photos:
                cols = st.columns(4)
                for i, photo in enumerate(photos):
                    cols[i % 4].image(photo["public_url"])

if menu == "Build Listing":
    st.header("Build Listing Package")

    sku = st.text_input("SKU")

    if st.button("Build"):
        sku_clean = normalize_sku(sku)

        result = supabase.table("parts").select("*").eq("sku", sku_clean).execute().data

        if not result:
            st.error("Part not found.")
        else:
            part = result[0]

            title = f"{part.get('oem_number') or ''} {part['part_name']} {part['condition']} Semi Truck Part".strip()[:80]

            description = f"""
Part: {part['part_name']}
SKU: {part['sku']}
Source Vehicle: {part.get('vehicle_code') or 'Unknown'}
OEM Number: {part.get('oem_number') or 'Unknown'}
Condition: {part.get('condition') or 'Unknown'}
Shelf: {part.get('shelf_location') or 'Unknown'}

Notes:
{part.get('notes') or 'No additional notes.'}

Buyer is responsible for verifying fitment.
Used parts may have normal wear.
Please review photos carefully.
"""

            errors = []

            photos = supabase.table("part_photos").select("*").eq(
                "sku", sku_clean
            ).execute().data

            if not photos or len(photos) < 3:
                errors.append("Need at least 3 photos.")
            if not part.get("ask_price"):
                errors.append("Missing price.")
            if not part.get("shelf_location"):
                errors.append("Missing shelf location.")

            ready = len(errors) == 0

            supabase.table("listing_packages").upsert({
                "sku": sku_clean,
                "title": title,
                "description": description,
                "price": part.get("ask_price"),
                "ready_to_publish": ready,
                "validation_errors": "\n".join(errors),
            }).execute()

            if ready:
                st.success("Ready to publish.")
            else:
                st.warning("Not ready.")
                st.text("\n".join(errors))

            st.text_area("Title", title)
            st.text_area("Description", description, height=300)

if menu == "Log Sale":
    st.header("Log Sale")

    with st.form("sale_form"):
        sku = st.text_input("SKU")
        platform = st.selectbox("Platform", ["eBay", "Facebook Marketplace", "Local", "Other"])
        sold_price = st.number_input("Sold Price", min_value=0.0)
        fees = st.number_input("Fees", min_value=0.0)
        submitted = st.form_submit_button("Save Sale")

    if submitted:
        sku_clean = normalize_sku(sku)
        rate = commission_rate(sold_price)
        commission = sold_price * rate
        payout = sold_price - fees - commission

        supabase.table("sales").insert({
            "sku": sku_clean,
            "platform": platform,
            "sold_price": sold_price,
            "fees": fees,
            "commission_rate": rate,
            "commission_amount": commission,
            "client_payout": payout,
        }).execute()

        supabase.table("parts").update({"status": "Sold"}).eq("sku", sku_clean).execute()

        st.success(f"Commission: ${commission:.2f} | Client payout: ${payout:.2f}")

if menu == "Truck Profit":
    st.header("Truck Part-Out Profit Dashboard")

    vehicles = supabase.table("vehicles").select("*").execute().data

    if not vehicles:
        st.info("No vehicles added yet.")

    for vehicle in vehicles:
        vehicle_code = vehicle["vehicle_code"]

        parts = supabase.table("parts").select("*").eq(
            "vehicle_code", vehicle_code
        ).execute().data

        total_listed_value = sum(float(p.get("ask_price") or 0) for p in parts)

        sold_parts = []
        total_sales = 0
        total_commission = 0
        total_client_payout = 0

        for part in parts:
            sales = supabase.table("sales").select("*").eq(
                "sku", part["sku"]
            ).execute().data

            for sale in sales:
                sold_parts.append({
                    **sale,
                    "part_name": part["part_name"],
                    "sku": part["sku"],
                })
                total_sales += float(sale.get("sold_price") or 0)
                total_commission += float(sale.get("commission_amount") or 0)
                total_client_payout += float(sale.get("client_payout") or 0)

        purchase_price = float(vehicle.get("purchase_price") or 0)
        gross_profit = total_sales - purchase_price

        with st.expander(
            f"{vehicle_code} — {vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')}",
            expanded=False,
        ):
            st.write(vehicle)

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Parts Count", len(parts))
            col2.metric("Listed Value", f"${total_listed_value:,.2f}")
            col3.metric("Total Sold", f"${total_sales:,.2f}")
            col4.metric("Gross Profit", f"${gross_profit:,.2f}")

            st.write(f"Your Commission: ${total_commission:,.2f}")
            st.write(f"Client Payout: ${total_client_payout:,.2f}")

            if sold_parts:
                st.subheader("Sold Parts")
                st.dataframe(sold_parts, use_container_width=True)
            else:
                st.info("No sold parts from this truck yet.")