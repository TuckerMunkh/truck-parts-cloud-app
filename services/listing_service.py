from services.supabase_client import get_supabase
from services.inventory_service import InventoryService
from services.photo_service import PhotoService
from services.utils import normalize_code

class ListingService:
    def __init__(self):
        self.supabase = get_supabase()
        self.inventory = InventoryService()
        self.photos = PhotoService()

    def validate(self, sku: str):
        item = self.inventory.get(sku)
        errors = []
        if not item:
            return ["Item not found."]
        for field in ["sku", "item_name", "condition", "ask_price", "shelf_location"]:
            if not item.get(field):
                errors.append(f"Missing {field}.")
        if len(self.photos.get_item_photos(sku)) < 3:
            errors.append("Need at least 3 item photos.")
        if item.get("source_type") == "Vehicle" and not item.get("vehicle_code"):
            errors.append("Vehicle source selected but vehicle_code is missing.")
        return errors

    def build_title(self, item: dict):
        pieces = [
            item.get("oem_number") or "",
            item.get("item_name") or "",
            item.get("condition") or "",
            item.get("category") or "",
            "Semi Truck Part",
        ]
        return " ".join([p.strip() for p in pieces if p and p.strip()])[:80]

    def build_description(self, item: dict):
        return f"""
Part / Item: {item.get("item_name") or ""}
SKU: {item.get("sku") or ""}
Source Type: {item.get("source_type") or "Unknown"}
Source Vehicle: {item.get("vehicle_code") or "N/A"}
Item Type: {item.get("item_type") or "N/A"}
Category: {item.get("category") or "N/A"}
OEM / Part Number: {item.get("oem_number") or "Unknown"}
Condition: {item.get("condition") or "Unknown"}
Shelf Location: {item.get("shelf_location") or "Unknown"}
Quantity: {item.get("quantity") or 1}

Notes:
{item.get("notes") or "No additional notes."}

Important:
- Buyer is responsible for verifying fitment before purchase.
- Used parts may have normal wear.
- Please review photos carefully.
- Local pickup may be available for heavy items.
""".strip()

    def build_package(self, sku: str):
        sku = normalize_code(sku)
        item = self.inventory.get(sku)
        if not item:
            raise ValueError("Item not found.")
        errors = self.validate(sku)
        package = {
            "sku": sku,
            "title": self.build_title(item),
            "description": self.build_description(item),
            "price": item.get("ask_price"),
            "ready_to_publish": len(errors) == 0,
            "validation_errors": "\n".join(errors),
        }
        self.supabase.table("listing_packages").upsert(package).execute()
        return package

    def facebook_copy(self, sku: str):
        p = self.build_package(sku)
        return f"""
FACEBOOK MARKETPLACE COPY PACKAGE

Title:
{p["title"]}

Price:
${p["price"]}

Description:
{p["description"]}
""".strip()
