import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializar cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Crear app FastAPI
app = FastAPI(
    title="SynergY Apex LATAM API",
    description="API para datos de expansión bancaria LATAM",
    version="1.0.0"
)

# Agregar CORS para que el dashboard pueda consumir la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RUTAS DE LA API

@app.get("/")
def root():
    """Health check"""
    return {
        "status": "ok",
        "message": "API SynergY Apex LATAM",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
def health():
    """Verifica que la API y Supabase están conectadas"""
    try:
        # Intenta conectar a Supabase
        response = supabase.table("countries").select("*").limit(1).execute()
        return {
            "status": "healthy",
            "supabase": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/countries")
def get_countries():
    """Obtiene lista de países con sus datos macroeconómicos"""
    try:
        response = supabase.table("countries").select("*").execute()
        return {
            "data": response.data,
            "count": len(response.data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mexico")
def get_mexico():
    """Obtiene datos completos de México"""
    try:
        # Obtener datos del país
        country_response = supabase.table("countries").select("*").eq("country", "México").execute()
        
        # Obtener datos de actores (bancos)
        actors_response = supabase.table("actors").select("*").eq("country", "México").execute()
        
        return {
            "country_data": country_response.data[0] if country_response.data else None,
            "actors": actors_response.data,
            "actors_count": len(actors_response.data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/{country_name}")
def get_country(country_name: str):
    """Obtiene datos de un país específico"""
    try:
        # Obtener datos del país
        country_response = supabase.table("countries").select("*").eq("country", country_name).execute()
        
        # Obtener datos de actores
        actors_response = supabase.table("actors").select("*").eq("country", country_name).execute()
        
        if not country_response.data:
            raise HTTPException(status_code=404, detail=f"País '{country_name}' no encontrado")
        
        return {
            "country": country_name,
            "country_data": country_response.data[0],
            "actors": actors_response.data,
            "actors_count": len(actors_response.data),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/{country_name}/actors")
def get_country_actors(country_name: str):
    """Obtiene solo los actores (bancos) de un país"""
    try:
        response = supabase.table("actors").select("*").eq("country", country_name).order("cuota_mercado", desc=True).execute()
        
        return {
            "country": country_name,
            "actors": response.data,
            "count": len(response.data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/{country_name}/macro")
def get_country_macro(country_name: str):
    """Obtiene solo datos macroeconómicos de un país"""
    try:
        response = supabase.table("countries").select("*").eq("country", country_name).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"País '{country_name}' no encontrado")
        
        return {
            "country": country_name,
            "data": response.data[0],
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/actors/top/{limit}")
def get_top_actors(limit: int = 10):
    """Obtiene los actores más grandes por cuota de mercado"""
    try:
        response = supabase.table("actors").select("*").order("cuota_mercado", desc=True).limit(limit).execute()
        
        return {
            "limit": limit,
            "actors": response.data,
            "count": len(response.data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Para desarrollo local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)