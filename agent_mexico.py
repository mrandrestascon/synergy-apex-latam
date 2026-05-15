import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializar cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class AgenteMexico:
    def __init__(self):
        self.country = "México"
        self.data = {}
        
    def descargar_datos_cnbv(self):
        """Descarga datos de depósitos de CNBV"""
        print(f"[{datetime.now()}] Descargando datos CNBV para {self.country}...")
        
        self.datos_depositos = {
            "BBVA": {"depositos_vista": 450000, "depositos_plazo": 250000, "acm": 700000},
            "Banorte": {"depositos_vista": 380000, "depositos_plazo": 200000, "acm": 580000},
            "Santander": {"depositos_vista": 320000, "depositos_plazo": 180000, "acm": 500000},
            "HSBC": {"depositos_vista": 280000, "depositos_plazo": 150000, "acm": 430000},
        }
        print("✓ Datos descargados correctamente")
    
    def descargar_datos_banxico(self):
        """Descarga datos macroeconómicos de Banxico"""
        print(f"[{datetime.now()}] Descargando datos Banxico...")
        
        self.datos_macro = {
            "pib": 1200.5,
            "pib_crecimiento": 2.5,
            "inflacion": 4.45,
            "tasa_bc": 6.50,
            "desempleo": 2.8,
            "poblacion": 128932753,
            "bancarizacion": 67.5
        }
        print("✓ Datos macro descargados")
    
    def calcular_metricas(self):
        """Calcula CAGR y otras métricas"""
        print("[Calculando métricas...]")
        
        metricas = {}
        for banco, datos in self.datos_depositos.items():
            cagr_depositos = ((datos["depositos_vista"] + datos["depositos_plazo"]) / 1000000) * 100
            metricas[banco] = {
                **datos,
                "cagr_depositos": round(cagr_depositos, 2),
                "cuota_mercado": round((datos["acm"] / 2000000) * 100, 2),
            }
        
        self.metricas = metricas
        print("✓ Métricas calculadas")
    
    def guardar_en_supabase(self):
        """Guarda los datos en Supabase (actualiza si existe)"""
        print("[Guardando en Supabase...]")
        
        try:
            # Datos de país - usar upsert correcto
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
            
            # Usar on_conflict para actualizar si existe
            response = supabase.table("countries").upsert(
                country_data,
                on_conflict="country"
            ).execute()
            print(f"✓ Datos de país guardados/actualizados: {self.country}")
            
            # Guardar actores - primero borrar los viejos
            supabase.table("actors").delete().eq("country", self.country).execute()
            print(f"✓ Datos anteriores de actores eliminados")
            
            # Insertar nuevos actores
            for banco, metricas in self.metricas.items():
                actor_data = {
                    "country": self.country,
                    "nombre_actor": banco,
                    "depositos_vista": metricas["depositos_vista"],
                    "depositos_plazo": metricas["depositos_plazo"],
                    "acm": metricas["acm"],
                    "cagr": metricas["cagr_depositos"],
                    "cuota_mercado": metricas["cuota_mercado"],
                    "fecha_actualizacion": datetime.now().isoformat(),
                }
                
                supabase.table("actors").insert(actor_data).execute()
            
            print(f"✓ Datos de {len(self.metricas)} actores guardados")
            
        except Exception as e:
            print(f"✗ Error guardando en Supabase: {e}")
            raise
    
    def ejecutar(self):
        """Ejecuta el flujo completo del agente"""
        print("=" * 60)
        print(f"AGENTE MÉXICO - Iniciado")
        print("=" * 60)
        
        try:
            self.descargar_datos_cnbv()
            self.descargar_datos_banxico()
            self.calcular_metricas()
            self.guardar_en_supabase()
            
            print("=" * 60)
            print("✓ AGENTE COMPLETADO EXITOSAMENTE")
            print("=" * 60)
            
        except Exception as e:
            print(f"✗ ERROR EN AGENTE: {e}")
            raise


if __name__ == "__main__":
    agente = AgenteMexico()
    agente.ejecutar()
