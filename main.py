import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FoodItem(BaseModel):
    name: str = Field(..., description="Food name")
    amount_g: float = Field(..., ge=0, description="Amount eaten in grams")
    calories_per_100g: Optional[float] = Field(None, ge=0, description="Calories per 100g")
    calories_per_serving: Optional[float] = Field(
        None, ge=0, description="Calories per serving (if using serving size)"
    )
    serving_size_g: Optional[float] = Field(
        None, ge=0, description="Serving size in grams corresponding to calories_per_serving"
    )


class CalculationRequest(BaseModel):
    items: List[FoodItem]


class ItemResult(BaseModel):
    name: str
    amount_g: float
    calories: float
    method: str
    note: Optional[str] = None


class CalculationResponse(BaseModel):
    total_calories: float
    items: List[ItemResult]


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.post("/api/calculate", response_model=CalculationResponse)
def calculate_calories(payload: CalculationRequest):
    results: List[ItemResult] = []
    total = 0.0

    for item in payload.items:
        calories = 0.0
        method = "unknown"
        note: Optional[str] = None

        if item.calories_per_100g is not None:
            calories = (item.amount_g * item.calories_per_100g) / 100.0
            method = "per_100g"
        elif (
            item.calories_per_serving is not None
            and item.serving_size_g is not None
            and item.serving_size_g > 0
        ):
            servings = item.amount_g / item.serving_size_g
            calories = servings * item.calories_per_serving
            method = "per_serving"
        else:
            note = "Missing calorie data; counted as 0"
            method = "insufficient_data"

        calories = float(round(calories, 2))
        total += calories

        results.append(
            ItemResult(
                name=item.name,
                amount_g=float(item.amount_g),
                calories=calories,
                method=method,
                note=note,
            )
        )

    return CalculationResponse(total_calories=float(round(total, 2)), items=results)


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
