from services.supabase_client import get_supabase
from services.utils import normalize_code

class VehicleService:
    def __init__(self):
        self.supabase = get_supabase()

    def create_or_update(self, data: dict):
        data["vehicle_code"] = normalize_code(data.get("vehicle_code"))
        return self.supabase.table("vehicles").upsert(data).execute()

    def list_all(self):
        return self.supabase.table("vehicles").select("*").order("created_at", desc=True).execute().data

    def get(self, vehicle_code: str):
        data = self.supabase.table("vehicles").select("*").eq(
            "vehicle_code", normalize_code(vehicle_code)
        ).execute().data
        return data[0] if data else None

    def update(self, vehicle_code: str, data: dict):
        return self.supabase.table("vehicles").update(data).eq(
            "vehicle_code", normalize_code(vehicle_code)
        ).execute()
