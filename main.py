"""
Main FastAPI Application
Entry point for the API Requirements Management System
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from swagger_import_controller import router as swagger_import_router

# Create FastAPI app
app = FastAPI(
    title="API Requirements Management System",
    description="System for managing API requirements with Swagger/OpenAPI import",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(swagger_import_router)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on application startup"""
    init_db()
    print("Database initialized successfully")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "API Requirements Management System",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

