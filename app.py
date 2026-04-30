import streamlit as st
import pandas as pd
from services.vehicle_service import VehicleService
from services.inventory_service import InventoryService
from services.photo_service import PhotoService
from services.listing_service import ListingService
from services.sales_service import SalesService
from services.dashboard_service import DashboardService
from services.utils import normalize_code

st.set_page_config(page_title="Truck Parts Cloud System V2", layout="wide")

vehicles = VehicleService()
inventory = InventoryService()
photos = PhotoService()
listings = ListingService()
sales = SalesService()
dashboard = DashboardService()

st.title("Truck Parts Cloud System V2")

menu = st.sidebar.selectbox("Menu", ["Dashboard", "Vehicles", "Inventory", "Photos", "Listings", "Sales", "Reports"])

if menu == "Dashboard":
    st.header("Dashboard")
    all_vehicles = vehicles.list_all()
    misc = dashboard.misc_summary()
    c1, c2, c3 = st.columns(3)
    c1.metric("Vehicles", len(all_vehicles))
    c2.metric("Misc Items", len(misc["items"]))
    c3.metric("Misc Sales", f'${misc["total_sales"]:,.2f}')
    st.info("Vehicle = disassembly/part-out. Misc/Vendor/Overstock = general inventory.")

if menu == "Vehicles":
    action = st.radio("Vehicle Action", ["Add Vehicle", "Edit Vehicle", "View Vehicles"], horizontal=True)

    if action == "Add Vehicle":
        st.header("Add Source Truck / Vehicle")
        with st.form("add_vehicle_form"):
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
            uploaded = st.file_uploader("Upload vehicle photos now or later", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
            submitted = st.form_submit_button("Save Vehicle")
        if submitted:
            vehicle_clean = normalize_code(vehicle_code)
            if not vehicle_clean:
                st.error("Vehicle code is required.")
            else:
                vehicles.create_or_update({
                    "vehicle_code": vehicle_clean, "vin": vin, "year": year, "make": make,
                    "model": model, "engine": engine, "purchase_price": purchase_price,
                    "auction_source": auction_source, "acquired_at": str(acquired_at), "notes": notes
                })
                count = len(photos.upload_vehicle_photos(vehicle_clean, uploaded))
                st.success(f"Saved {vehicle_clean}. Uploaded {count} photos.")

    if action == "Edit Vehicle":
        st.header("Edit Vehicle")
        all_vehicles = vehicles.list_all()
        opts = [v["vehicle_code"] for v in all_vehicles]
        if not opts:
            st.info("No vehicles found.")
        else:
            selected = st.selectbox("Select Vehicle", opts)
            vehicle = vehicles.get(selected)
            with st.form("edit_vehicle_form"):
                vin = st.text_input("VIN", value=vehicle.get("vin") or "")
                year = st.number_input("Year", min_value=1900, max_value=2100, step=1, value=int(vehicle.get("year") or 2000))
                make = st.text_input("Make", value=vehicle.get("make") or "")
                model = st.text_input("Model", value=vehicle.get("model") or "")
                engine = st.text_input("Engine", value=vehicle.get("engine") or "")
                purchase_price = st.number_input("Purchase Price", min_value=0.0, value=float(vehicle.get("purchase_price") or 0))
                auction_source = st.text_input("Auction Source", value=vehicle.get("auction_source") or "")
                notes = st.text_area("Notes", value=vehicle.get("notes") or "")
                submitted = st.form_submit_button("Update Vehicle")
            if submitted:
                vehicles.update(selected, {"vin": vin, "year": year, "make": make, "model": model, "engine": engine, "purchase_price": purchase_price, "auction_source": auction_source, "notes": notes})
                st.success(f"Updated {selected}")
            st.subheader("Current Photos")
            vphotos = photos.get_vehicle_photos(selected)
            if vphotos:
                cols = st.columns(4)
                for i, p in enumerate(vphotos):
                    cols[i % 4].image(p["public_url"])
            else:
                st.info("No vehicle photos yet.")

    if action == "View Vehicles":
        rows = vehicles.list_all()
        st.dataframe(pd.DataFrame(rows), use_container_width=True) if rows else st.info("No vehicles added yet.")

if menu == "Inventory":
    action = st.radio("Inventory Action", ["Add Item", "Edit Item", "Search Inventory"], horizontal=True)
    all_vehicles = vehicles.list_all()
    vehicle_options = [""] + [f'{v["vehicle_code"]} — {v.get("year") or ""} {v.get("make") or ""} {v.get("model") or ""}' for v in all_vehicles]

    if action == "Add Item":
        st.header("Add Inventory Item")
        with st.form("add_item_form"):
            sku = st.text_input("SKU", placeholder="CTP-001")
            source_type = st.selectbox("Source Type", ["Vehicle", "Misc", "Vendor", "Overstock"])
            selected_vehicle = st.selectbox("Source Vehicle", vehicle_options, disabled=(source_type != "Vehicle"))
            vehicle_code = selected_vehicle.split(" — ")[0] if selected_vehicle else None
            item_type = st.selectbox("Item Type", ["Part", "Tire", "Rim", "Oil", "AC Unit", "Tool", "Misc"])
            item_name = st.text_input("Item Name")
            category = st.text_input("Category")
            oem_number = st.text_input("OEM Number")
            condition = st.selectbox("Condition", ["Used", "New", "Unknown", "Damaged"])
            shelf_location = st.text_input("Shelf Location")
            ask_price = st.number_input("Ask Price", min_value=0.0)
            min_price = st.number_input("Minimum Price", min_value=0.0)
            quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
            vendor_name = st.text_input("Vendor Name / Source")
            notes = st.text_area("Notes")
            uploaded = st.file_uploader("Upload item photos now or later", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
            submitted = st.form_submit_button("Save Item")
        if submitted:
            sku_clean = normalize_code(sku)
            if not sku_clean:
                st.error("SKU is required.")
            elif not item_name:
                st.error("Item name is required.")
            elif source_type == "Vehicle" and not vehicle_code:
                st.error("Vehicle source requires a vehicle code.")
            else:
                inventory.create_or_update({
                    "sku": sku_clean, "item_type": item_type, "source_type": source_type,
                    "vehicle_code": vehicle_code if source_type == "Vehicle" else None,
                    "item_name": item_name, "category": category, "oem_number": oem_number,
                    "condition": condition, "shelf_location": shelf_location,
                    "ask_price": ask_price, "min_price": min_price, "quantity": int(quantity),
                    "vendor_name": vendor_name, "notes": notes, "status": "New",
                })
                count = len(photos.upload_item_photos(sku_clean, uploaded))
                st.success(f"Saved {sku_clean}. Uploaded {count} photos.")

    if action == "Edit Item":
        st.header("Edit Inventory Item")
        search_sku = st.text_input("Enter SKU to edit", placeholder="CTP-001")
        if search_sku:
            item = inventory.get(search_sku)
            if not item:
                st.error("Item not found.")
            else:
                source_types = ["Vehicle", "Misc", "Vendor", "Overstock"]
                item_types = ["Part", "Tire", "Rim", "Oil", "AC Unit", "Tool", "Misc"]
                conditions = ["Used", "New", "Unknown", "Damaged"]
                statuses = ["New", "Photographed", "Listed", "Pending", "Sold", "Removed"]
                with st.form("edit_item_form"):
                    source_type = st.selectbox("Source Type", source_types, index=source_types.index(item.get("source_type") or "Misc"))
                    selected_vehicle = next((x for x in vehicle_options if item.get("vehicle_code") and x.startswith(item["vehicle_code"])), "")
                    selected_vehicle = st.selectbox("Source Vehicle", vehicle_options, index=vehicle_options.index(selected_vehicle) if selected_vehicle in vehicle_options else 0, disabled=(source_type != "Vehicle"))
                    vehicle_code = selected_vehicle.split(" — ")[0] if selected_vehicle else None
                    item_type = st.selectbox("Item Type", item_types, index=item_types.index(item.get("item_type") or "Part"))
                    item_name = st.text_input("Item Name", value=item.get("item_name") or "")
                    category = st.text_input("Category", value=item.get("category") or "")
                    oem_number = st.text_input("OEM Number", value=item.get("oem_number") or "")
                    condition = st.selectbox("Condition", conditions, index=conditions.index(item.get("condition") or "Used"))
                    shelf_location = st.text_input("Shelf Location", value=item.get("shelf_location") or "")
                    ask_price = st.number_input("Ask Price", min_value=0.0, value=float(item.get("ask_price") or 0))
                    min_price = st.number_input("Minimum Price", min_value=0.0, value=float(item.get("min_price") or 0))
                    quantity = st.number_input("Quantity", min_value=1, step=1, value=int(item.get("quantity") or 1))
                    status = st.selectbox("Status", statuses, index=statuses.index(item.get("status") or "New"))
                    vendor_name = st.text_input("Vendor Name / Source", value=item.get("vendor_name") or "")
                    notes = st.text_area("Notes", value=item.get("notes") or "")
                    submitted = st.form_submit_button("Update Item")
                if submitted:
                    inventory.update(search_sku, {
                        "source_type": source_type, "vehicle_code": vehicle_code if source_type == "Vehicle" else None,
                        "item_type": item_type, "item_name": item_name, "category": category,
                        "oem_number": oem_number, "condition": condition, "shelf_location": shelf_location,
                        "ask_price": ask_price, "min_price": min_price, "quantity": int(quantity),
                        "status": status, "vendor_name": vendor_name, "notes": notes,
                    })
                    st.success(f"Updated {normalize_code(search_sku)}")
                st.subheader("Current Photos")
                iphotos = photos.get_item_photos(search_sku)
                if iphotos:
                    cols = st.columns(4)
                    for i, p in enumerate(iphotos):
                        cols[i % 4].image(p["public_url"])
                else:
                    st.info("No item photos yet.")

    if action == "Search Inventory":
        st.header("Search Inventory")
        search = st.text_input("Search by SKU, item name, OEM, or category")
        if search:
            rows = inventory.search(search)
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
                for item in rows:
                    with st.expander(f'{item["sku"]} — {item["item_name"]}'):
                        st.write(item)
                        iphotos = photos.get_item_photos(item["sku"])
                        if iphotos:
                            cols = st.columns(4)
                            for i, p in enumerate(iphotos):
                                cols[i % 4].image(p["public_url"])
            else:
                st.info("No items found.")

if menu == "Photos":
    st.header("Upload Photos After Initial Entry")
    target = st.radio("Photo Target", ["Vehicle", "Inventory Item"], horizontal=True)
    if target == "Vehicle":
        code = st.text_input("Vehicle Code", placeholder="TRUCK-001")
        uploaded = st.file_uploader("Upload vehicle photos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
        if st.button("Upload Vehicle Photos"):
            st.success(f"Uploaded {len(photos.upload_vehicle_photos(code, uploaded))} vehicle photos.") if code else st.error("Vehicle code is required.")
    else:
        sku = st.text_input("SKU", placeholder="CTP-001")
        uploaded = st.file_uploader("Upload item photos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
        if st.button("Upload Item Photos"):
            st.success(f"Uploaded {len(photos.upload_item_photos(sku, uploaded))} item photos.") if sku else st.error("SKU is required.")

if menu == "Listings":
    st.header("Listing Tools")
    sku = st.text_input("SKU", placeholder="CTP-001")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Build Listing Package"):
            try:
                p = listings.build_package(sku)
                st.success("Ready to publish.") if p["ready_to_publish"] else st.warning("Not ready yet.")
                if p["validation_errors"]:
                    st.text(p["validation_errors"])
                st.text_area("Title", p["title"], height=80)
                st.text_area("Description", p["description"], height=350)
                st.write(f'Price: ${p["price"]}')
            except Exception as e:
                st.error(str(e))
    with c2:
        if st.button("Generate Facebook Copy"):
            try:
                st.text_area("Facebook Copy Package", listings.facebook_copy(sku), height=500)
            except Exception as e:
                st.error(str(e))

if menu == "Sales":
    action = st.radio("Sales Action", ["Log Sale", "Recent Sales"], horizontal=True)
    if action == "Log Sale":
        with st.form("sale_form"):
            sku = st.text_input("SKU", placeholder="CTP-001")
            platform = st.selectbox("Platform", ["eBay", "Facebook Marketplace", "Local", "Other"])
            sold_price = st.number_input("Sold Price", min_value=0.0)
            fees = st.number_input("Fees", min_value=0.0)
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save Sale")
        if submitted:
            if not sku:
                st.error("SKU is required.")
            else:
                row = sales.log_sale(sku, platform, sold_price, fees, notes)
                st.success(f'Commission: ${row["commission_amount"]:,.2f} | Client payout: ${row["client_payout"]:,.2f}')
    else:
        rows = sales.list_recent()
        st.dataframe(pd.DataFrame(rows), use_container_width=True) if rows else st.info("No sales logged yet.")

if menu == "Reports":
    report = st.radio("Report", ["Truck Part-Out Profit", "Misc Inventory Profit"], horizontal=True)
    if report == "Truck Part-Out Profit":
        for vehicle in vehicles.list_all():
            s = dashboard.vehicle_summary(vehicle)
            with st.expander(f'{vehicle["vehicle_code"]} — {vehicle.get("year")} {vehicle.get("make")} {vehicle.get("model")}'):
                vphotos = photos.get_vehicle_photos(vehicle["vehicle_code"])
                if vphotos:
                    cols = st.columns(4)
                    for i, p in enumerate(vphotos):
                        cols[i % 4].image(p["public_url"])
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Items Count", len(s["parts"]))
                c2.metric("Listed Value", f'${s["total_listed_value"]:,.2f}')
                c3.metric("Total Sold", f'${s["total_sales"]:,.2f}')
                c4.metric("Gross Profit", f'${s["gross_profit"]:,.2f}')
                st.write(f'Your Commission: ${s["total_commission"]:,.2f}')
                st.write(f'Client Payout: ${s["total_client_payout"]:,.2f}')
                st.subheader("Items from Vehicle")
                st.dataframe(pd.DataFrame(s["parts"]), use_container_width=True) if s["parts"] else st.info("No items tied to this vehicle.")
                st.subheader("Sold Items")
                st.dataframe(pd.DataFrame(s["sold_rows"]), use_container_width=True) if s["sold_rows"] else st.info("No sales from this vehicle yet.")
    else:
        s = dashboard.misc_summary()
        c1, c2, c3 = st.columns(3)
        c1.metric("Misc Items", len(s["items"]))
        c2.metric("Listed Value", f'${s["total_listed_value"]:,.2f}')
        c3.metric("Total Sold", f'${s["total_sales"]:,.2f}')
        st.write(f'Your Commission: ${s["total_commission"]:,.2f}')
        st.write(f'Client Payout: ${s["total_client_payout"]:,.2f}')
        st.subheader("Misc Inventory")
        st.dataframe(pd.DataFrame(s["items"]), use_container_width=True) if s["items"] else st.info("No misc inventory yet.")
        st.subheader("Misc Sales")
        st.dataframe(pd.DataFrame(s["sold_rows"]), use_container_width=True) if s["sold_rows"] else st.info("No misc sales yet.")
