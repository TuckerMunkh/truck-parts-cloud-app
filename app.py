import streamlit as st
from supabase import create_client
from datetime import datetime

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
    ["Add Part", "Search Inventory", "Build Listing", "Log Sale"]
)

if menu == "Add Part":
    st.header("Add Part")

    with st.form("part_form"):
        sku = st.text_input("SKU", placeholder="CTP-001")
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
            accept_multiple_files=True
        )

        submitted = st.form_submit_button("Save Part")

    if submitted:
        sku_clean = normalize_sku(sku)

        supabase.table("parts").upsert({
            "sku": sku_clean,
            "part_name": part_name,
            "category": category,
            "oem_number": oem_number,
            "condition": condition,
            "shelf_location": shelf_location,
            "ask_price": ask_price,
            "min_price": min_price,
            "notes": notes,
            "status": "New"
        }).execute()

        for photo in photos:
            file_path = f"{sku_clean.lower()}/{photo.name}"
            file_bytes = photo.getvalue()

            supabase.storage.from_(BUCKET).upload(
                file_path,
                file_bytes,
                {"content-type": photo.type, "upsert": "true"}
            )

            public_url = supabase.storage.from_(BUCKET).get_public_url(file_path)

            supabase.table("part_photos").insert({
                "sku": sku_clean,
                "file_path": file_path,
                "public_url": public_url
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
            photos = supabase.table("part_photos").select("*").eq("sku", sku_clean).execute().data

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
                "validation_errors": "\\n".join(errors)
            }).execute()

            if ready:
                st.success("Ready to publish.")
            else:
                st.warning("Not ready.")
                st.text("\\n".join(errors))

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
            "client_payout": payout
        }).execute()

        supabase.table("parts").update({"status": "Sold"}).eq("sku", sku_clean).execute()

        st.success(f"Commission: ${commission:.2f} | Client payout: ${payout:.2f}")