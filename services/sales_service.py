from services.supabase_client import get_supabase
from services.utils import normalize_code, commission_rate, money

class SalesService:
    def __init__(self):
        self.supabase = get_supabase()

    def log_sale(self, sku: str, platform: str, sold_price: float, fees: float, notes: str = ""):
        sku = normalize_code(sku)
        rate = commission_rate(sold_price)
        commission = money(sold_price) * rate
        client_payout = money(sold_price) - money(fees) - commission
        row = {
            "sku": sku,
            "platform": platform,
            "sold_price": sold_price,
            "fees": fees,
            "commission_rate": rate,
            "commission_amount": commission,
            "client_payout": client_payout,
            "notes": notes,
        }
        self.supabase.table("sales").insert(row).execute()
        self.supabase.table("inventory_items").update({"status": "Sold"}).eq("sku", sku).execute()
        return row

    def get_sales_by_sku(self, sku: str):
        return self.supabase.table("sales").select("*").eq("sku", normalize_code(sku)).execute().data

    def list_recent(self):
        return self.supabase.table("sales").select("*").order("sold_at", desc=True).limit(100).execute().data
