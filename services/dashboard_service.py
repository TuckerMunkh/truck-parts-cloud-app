from services.inventory_service import InventoryService
from services.sales_service import SalesService
from services.utils import money

class DashboardService:
    def __init__(self):
        self.inventory = InventoryService()
        self.sales = SalesService()

    def vehicle_summary(self, vehicle: dict):
        parts = self.inventory.list_by_vehicle(vehicle["vehicle_code"])
        total_listed_value = sum(money(p.get("ask_price")) for p in parts)
        total_sales = total_commission = total_client_payout = 0
        sold_rows = []
        for item in parts:
            for sale in self.sales.get_sales_by_sku(item["sku"]):
                total_sales += money(sale.get("sold_price"))
                total_commission += money(sale.get("commission_amount"))
                total_client_payout += money(sale.get("client_payout"))
                sold_rows.append({**sale, "item_name": item.get("item_name"), "sku": item.get("sku")})
        purchase_price = money(vehicle.get("purchase_price"))
        return {
            "parts": parts,
            "sold_rows": sold_rows,
            "total_listed_value": total_listed_value,
            "total_sales": total_sales,
            "total_commission": total_commission,
            "total_client_payout": total_client_payout,
            "purchase_price": purchase_price,
            "gross_profit": total_sales - purchase_price,
        }

    def misc_summary(self):
        items = self.inventory.list_misc()
        total_listed_value = sum(money(i.get("ask_price")) for i in items)
        total_sales = total_commission = total_client_payout = 0
        sold_rows = []
        for item in items:
            for sale in self.sales.get_sales_by_sku(item["sku"]):
                total_sales += money(sale.get("sold_price"))
                total_commission += money(sale.get("commission_amount"))
                total_client_payout += money(sale.get("client_payout"))
                sold_rows.append({**sale, "item_name": item.get("item_name"), "sku": item.get("sku")})
        return {
            "items": items,
            "sold_rows": sold_rows,
            "total_listed_value": total_listed_value,
            "total_sales": total_sales,
            "total_commission": total_commission,
            "total_client_payout": total_client_payout,
        }
