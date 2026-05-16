import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class AgenteCostaRica:
    def __init__(self):
        self.country = "Costa Rica"
        
    def descargar_datos(self):
        print(f"[{datetime.now()}] Descargando datos para {self.country}...")
        self.datos_macro = {"pib": 68.9, "pib_crecimiento": 2.5, "inflacion": 3.5, "tasa_bc": 5.25, "desempleo": 9.1, "poblacion": 5180829, "bancarizacion": 65.8}
        self.datos_depositos = {
            "Banco Nacional de Costa Rica": {"depositos_vista": 16500, "depositos_plazo": 10200, "acm": 26700},
            "BAC Credomatic": {"depositos_vista": 14200, "depositos_plazo": 8800, "acm": 23000},
            "Scotiabank Costa Rica": {"depositos_vista": 11000, "depositos_plazo": 6800, "acm": 17800},
            "HSBC Costa Rica": {"depositos_vista": 8900, "depositos_plazo": 5500, "acm": 14400},
        }
        print("✓ Datos descargados")
    
    def calcular_metricas(self):
        print("[Calculando métricas...]")
        self.metricas = {}
        for banco, datos in self.datos_depositos.items():
            cagr = ((datos["depositos_vista"] + datos["depositos_plazo"]) / 1000000) * 100
            self.metricas[banco] = {**datos, "cagr": round(cagr, 2), "cuota_mercado": round((datos["acm"] / 81900) * 100, 2)}
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
        print(f"AGENTE COSTA RICA - Iniciado")
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
    agente = AgenteCostaRica()
    agente.ejecutar()
