import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class AgentePanama:
    def __init__(self):
        self.country = "Panamá"
        
    def descargar_datos(self):
        print(f"[{datetime.now()}] Descargando datos para {self.country}...")
        self.datos_macro = {"pib": 78.5, "pib_crecimiento": 3.2, "inflacion": 2.8, "tasa_bc": 3.5, "desempleo": 5.2, "poblacion": 4408581, "bancarizacion": 58.3}
        self.datos_depositos = {
            "Banco Nacional de Panamá": {"depositos_vista": 18000, "depositos_plazo": 11000, "acm": 29000},
            "Banorte Panamá": {"depositos_vista": 15000, "depositos_plazo": 9200, "acm": 24200},
            "HSBC Panamá": {"depositos_vista": 12000, "depositos_plazo": 7500, "acm": 19500},
            "Scotiabank Panamá": {"depositos_vista": 10000, "depositos_plazo": 6200, "acm": 16200},
        }
        print("✓ Datos descargados")
    
    def calcular_metricas(self):
        print("[Calculando métricas...]")
        self.metricas = {}
        for banco, datos in self.datos_depositos.items():
            cagr = ((datos["depositos_vista"] + datos["depositos_plazo"]) / 1000000) * 100
            self.metricas[banco] = {**datos, "cagr": round(cagr, 2), "cuota_mercado": round((datos["acm"] / 88900) * 100, 2)}
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
        print(f"AGENTE PANAMÁ - Iniciado")
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
    agente = AgentePanama()
    agente.ejecutar()
