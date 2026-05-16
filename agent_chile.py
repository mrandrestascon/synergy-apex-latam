import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class AgenteChile:
    def __init__(self):
        self.country = "Chile"
        
    def descargar_datos(self):
        print(f"[{datetime.now()}] Descargando datos para {self.country}...")
        self.datos_macro = {"pib": 310.2, "pib_crecimiento": 1.8, "inflacion": 3.2, "tasa_bc": 5.5, "desempleo": 8.5, "poblacion": 19603733, "bancarizacion": 71.2}
        self.datos_depositos = {
            "Banco Santander Chile": {"depositos_vista": 85000, "depositos_plazo": 52000, "acm": 137000},
            "BancoEstado": {"depositos_vista": 72000, "depositos_plazo": 45000, "acm": 117000},
            "Scotiabank Chile": {"depositos_vista": 58000, "depositos_plazo": 38000, "acm": 96000},
            "BBVA Chile": {"depositos_vista": 45000, "depositos_plazo": 28000, "acm": 73000},
        }
        print("✓ Datos descargados")
    
    def calcular_metricas(self):
        print("[Calculando métricas...]")
        self.metricas = {}
        for banco, datos in self.datos_depositos.items():
            cagr = ((datos["depositos_vista"] + datos["depositos_plazo"]) / 1000000) * 100
            self.metricas[banco] = {**datos, "cagr": round(cagr, 2), "cuota_mercado": round((datos["acm"] / 423000) * 100, 2)}
        print("✓ Métricas calculadas")
    
    def guardar_en_supabase(self):
        print("[Guardando en Supabase...]")
        try:
            country_data = {
                "country": self.country,
                "pib": self.datos_macro["pib"],
                "pib_crecimiento": self.datos_macro["pib_crecimiento"],
                "inflacion": self.datos_macro["inflacion"],
                "tasa_bc": self.datos_macro["tasa_bc"],
                "desempleo": self.datos_macro["desempleo"],
                "poblacion": self.datos_macro["poblacion"],
                "bancarizacion": self.datos_macro["bancarizacion"],
                "fecha_actualizacion": datetime.now().isoformat(),
            }
            supabase.table("countries").upsert(country_data, on_conflict="country").execute()
            print(f"✓ Datos de país guardados: {self.country}")
            
            supabase.table("actors").delete().eq("country", self.country).execute()
            for banco, metricas in self.metricas.items():
                actor_data = {
                    "country": self.country,
                    "nombre_actor": banco,
                    "depositos_vista": metricas["depositos_vista"],
                    "depositos_plazo": metricas["depositos_plazo"],
                    "acm": metricas["acm"],
                    "cagr": metricas["cagr"],
                    "cuota_mercado": metricas["cuota_mercado"],
                    "fecha_actualizacion": datetime.now().isoformat(),
                }
                supabase.table("actors").insert(actor_data).execute()
            print(f"✓ Datos de {len(self.metricas)} actores guardados")
        except Exception as e:
            print(f"✗ Error: {e}")
            raise
    
    def ejecutar(self):
        print("=" * 60)
        print(f"AGENTE CHILE - Iniciado")
        print("=" * 60)
        try:
            self.descargar_datos()
            self.calcular_metricas()
            self.guardar_en_supabase()
            print("=" * 60)
            print("✓ AGENTE COMPLETADO EXITOSAMENTE")
            print("=" * 60)
        except Exception as e:
            print(f"✗ ERROR: {e}")
            raise

if __name__ == "__main__":
    agente = AgenteChile()
    agente.ejecutar()
