from services.supabase_client import get_supabase
from services.utils import normalize_code

class InventoryService:
    def __init__(self):
        self.supabase = get_supabase()

    def create_or_update(self, data: dict):
        data["sku"] = normalize_code(data.get("sku"))
        data["vehicle_code"] = normalize_code(data.get("vehicle_code")) if data.get("vehicle_code") else None
        return self.supabase.table("inventory_items").upsert(data).execute()

    def update(self, sku: str, data: dict):
        if "vehicle_code" in data:
            data["vehicle_code"] = normalize_code(data["vehicle_code"]) if data["vehicle_code"] else None
        return self.supabase.table("inventory_items").update(data).eq("sku", normalize_code(sku)).execute()

    def get(self, sku: str):
        data = self.supabase.table("inventory_items").select("*").eq("sku", normalize_code(sku)).execute().data
        return data[0] if data else None

    def search(self, search: str):
        return self.supabase.table("inventory_items").select("*").or_(
            f"sku.ilike.%{search}%,item_name.ilike.%{search}%,category.ilike.%{search}%,oem_number.ilike.%{search}%"
        ).order("created_at", desc=True).execute().data

    def list_by_vehicle(self, vehicle_code: str):
        return self.supabase.table("inventory_items").select("*").eq("vehicle_code", normalize_code(vehicle_code)).execute().data

    def list_misc(self):
        return self.supabase.table("inventory_items").select("*").neq("source_type", "Vehicle").execute().data
