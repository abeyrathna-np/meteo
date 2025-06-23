import json
import os
from typing import Any, Dict, List
from fastmcp import FastMCP
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv
from requests import Session
import logging

from app import db_utils
from app.models import Weather

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Fast API server
app = FastAPI(title="Weather API with GROQ...")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",  # just in case
    "https://meteo-chat.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use ["*"] to allow all, not recommended in prod
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, etc.
    allow_headers=["*"],
)

# Initialize MCP server
mcp = FastMCP("weather-server")

# Initialize Groq client
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    logger.error("Missing Groq API key")
    raise ValueError("GROQ_API_KEY must be set")

groq_client = Groq(api_key=groq_api_key)

# Database helper functions - Fixed the Depends issue
class WeatherService:
    @staticmethod
    def get_weather_data(skip: int = 0, limit: int = 100) -> List[Weather]:
        """Get weather data from database"""
        try:
            db = db_utils.get_db().__next__()  # Get database session
            return db_utils.get_all_weather(db, skip, limit)
        except Exception as e:
            logger.error(f"Database error in get_weather_data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    @staticmethod
    def get_weather_data_by_date(date: str) -> Weather:
        """Get weather data by date"""
        try:
            db = db_utils.get_db().__next__()  # Get database session
            weather = db_utils.get_weather_by_date(db, date)
            if not weather:
                raise HTTPException(status_code=404, detail="Date not found")
            return weather
        except Exception as e:
            logger.error(f"Database error in get_weather_data_by_date: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Define the actual functions without MCP decoration for direct calling
def _get_weather_data(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get all available weather data from the database.
    
    Args:
        limit: Maximum number of weather data to return (default: 100)
        offset: Number of weather data to skip (default: 0)
    
    Returns:
        List of Weather objects with id, date, temp_max, temp_min, precipitation, location_id, location information
    """
    logger.info(f"Getting weather data with limit={limit}, offset={offset}")
    weather_data = WeatherService.get_weather_data(offset, limit)
    
    # Convert to dict format for JSON serialization
    result = []
    for weather in weather_data:
        weather_dict = {
            "id": weather.id,
            "date": str(weather.date),
            "temp_max": weather.temp_max,
            "temp_min": weather.temp_min,
            "precipitation": weather.precipitation,
            "location_id": weather.location_id,
            "location": {
                "id": weather.location.id,
                "name": weather.location.name,
                "geom_wkt": weather.location.geom_wkt
            } if weather.location else None
        }
        result.append(weather_dict)
    
    return result

def _get_weather_data_by_date(date: str) -> Dict[str, Any]:
    """
    Get weather data for a specific date from the database.
    
    Args:
        date: Date for which the weather data is requested (format: YYYY-MM-DD)
    
    Returns:
        Weather data object for a specific date with id, date, temp_max, temp_min, precipitation, location_id, location information
    """
    logger.info(f"Getting weather data for date: {date}")
    weather = WeatherService.get_weather_data_by_date(date)
    
    # Convert to dict format for JSON serialization
    result = {
        "id": weather.id,
        "date": str(weather.date),
        "temp_max": weather.temp_max,
        "temp_min": weather.temp_min,
        "precipitation": weather.precipitation,
        "location_id": weather.location_id,
        "location": {
            "id": weather.location.id,
            "name": weather.location.name,
            "geom_wkt": weather.location.geom_wkt
        } if weather.location else None
    }
    
    return result

# MCP Tools - These are for MCP server functionality
@mcp.tool()
def get_weather_data(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """MCP tool wrapper for getting weather data"""
    return _get_weather_data(limit, offset)

@mcp.tool()
def get_weather_data_by_date(date: str) -> Dict[str, Any]:
    """MCP tool wrapper for getting weather data by date"""
    return _get_weather_data_by_date(date)

# Convert MCP tools to OpenAI function format for Groq
def get_tool_schemas():
    """Convert MCP tools to OpenAI function calling format"""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_weather_data",
                "description": "Get all available weather data from the database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of weather data to return",
                            "default": 100
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Number of weather data to skip",
                            "default": 0
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_weather_data_by_date",
                "description": "Get weather data for a specific date from the database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "The date for which weather data is required (format: YYYY-MM-DD)"
                        }
                    },
                    "required": ["date"]
                }
            }
        }
    ]

# Tool execution mapping - Use the internal functions without MCP decoration
TOOL_FUNCTIONS = {
    "get_weather_data": _get_weather_data,
    "get_weather_data_by_date": _get_weather_data_by_date
}

# Main chat handler with Groq integration
async def handle_chat_with_tools(user_message: str) -> str:
    """
    Handle user message with automatic tool selection and execution
    """
    try:
        logger.info(f"Processing user message: {user_message}")
        
        # Initial Groq call with tool availability
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful weather assistant. You can help users find weather information. When users ask about weather data, use the available tools to get the information. Always provide helpful and informative responses."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            model="llama3-70b-8192",
            tools=get_tool_schemas(),
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1000
        )
        
        message = response.choices[0].message
        logger.info(f"Groq response: tool_calls={bool(message.tool_calls)}, content={message.content}")
        
        # Check if Groq wants to call any tools
        if message.tool_calls:
            logger.info(f"Executing {len(message.tool_calls)} tool calls")
            
            # Execute tool calls
            tool_results = []
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"Calling function: {function_name} with args: {function_args}")
                
                # Execute the tool
                if function_name in TOOL_FUNCTIONS:
                    try:
                        result = TOOL_FUNCTIONS[function_name](**function_args)
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "result": result
                        })
                        logger.info(f"Tool {function_name} executed successfully")
                    except Exception as e:
                        logger.error(f"Error executing tool {function_name}: {str(e)}")
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "error": str(e)
                        })
                else:
                    logger.error(f"Unknown function: {function_name}")
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "error": f"Unknown function: {function_name}"
                    })
            
            # Generate final response with tool results
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful weather assistant. Provide clear, natural responses based on the tool results. Format the weather information in a user-friendly way."
                },
                {
                    "role": "user",
                    "content": user_message
                },
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in message.tool_calls
                    ]
                }
            ]
            
            # Add tool results to conversation
            for tool_result in tool_results:
                content = tool_result.get("result", tool_result.get("error"))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_result["tool_call_id"],
                    "content": json.dumps(content, default=str)  # Handle non-serializable objects
                })
            
            logger.info("Generating final response with tool results")
            
            # Final response generation
            final_response = groq_client.chat.completions.create(
                messages=messages,
                model="llama3-70b-8192",
                temperature=0.7,
                max_tokens=1000
            )
            
            result = final_response.choices[0].message.content
            logger.info(f"Final response generated: {result[:100]}...")
            return result
            
        else:
            # No tools needed, return direct response
            logger.info("No tools needed, returning direct response")
            return message.content
            
    except Exception as e:
        logger.error(f"Error in handle_chat_with_tools: {str(e)}")
        return f"I encountered an error while processing your request: {str(e)}. Please try again or contact support if this continues."

# FastAPI endpoints
@app.get("/")
async def root():
    return {"message": "Weather MCP Server with Groq Integration"}

@app.post("/chat")
async def chat(message: dict):
    """
    Chat endpoint for testing the Groq integration
    """
    user_message = message.get("message", "")
    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    logger.info(f"Received chat request: {user_message}")
    response = await handle_chat_with_tools(user_message)
    return {"response": response}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "mcp_tools": len(TOOL_FUNCTIONS)}

# Debug endpoint to test database connection
@app.get("/debug/weather")
async def debug_weather():
    """Debug endpoint to test weather data retrieval"""
    try:
        weather_data = _get_weather_data(limit=5)  # Use the internal function
        return {"status": "success", "weather_data": weather_data}
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}")
        return {"status": "error", "error": str(e)}

# Debug endpoint to test Groq connection
@app.get("/debug/groq")
async def debug_groq():
    """Debug endpoint to test Groq connection"""
    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello, this is a test."}],
            model="llama3-70b-8192",
            max_tokens=50
        )
        return {"status": "success", "response": response.choices[0].message.content}
    except Exception as e:
        logger.error(f"Groq debug error: {str(e)}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)