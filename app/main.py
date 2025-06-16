from fastapi import FastAPI
from .routes import location, weather, chat
from fastapi_mcp import FastApiMCP
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",  # just in case
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use ["*"] to allow all, not recommended in prod
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, etc.
    allow_headers=["*"],
)


# Include route modules
app.include_router(location.router)
app.include_router(weather.router)
app.include_router(chat.router)



mcp = FastApiMCP(
    app,
    name="Weather MCP",
    description="Simple API exposing weather data (Temperature and Precipitation)",
)

mcp.mount()