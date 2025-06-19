from bson import ObjectId
from fastapi import HTTPException, status
from src.database.database import user_table
from typing import Dict, Any, Optional
import datetime


def format_time_for_frontend(seconds: int) -> str:
    """Convert seconds to a formatted string like '10m 30s'"""
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes}m {remaining_seconds}s"


def get_user_statistics(user_id: str) -> Dict[str, Any]:
    """Get statistics for a specific user"""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz kullanıcı ID",
        )

    user_data = user_table.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı",
        )

    # Format time for frontend display
    pyramid_time = user_data.get("pyramid_stats", {}).get("time", 0)
    vocabulary_time = user_data.get("vocabulary_stats", {}).get("time", 0)
    
    # Format success rate as percentage string
    pyramid_success = user_data.get("pyramid_stats", {}).get("success_rate", 0.0)
    vocabulary_success = user_data.get("vocabulary_stats", {}).get("success_rate", 0.0)
    
    # Get statistics from user document
    stats = {
        "pyramid": {
            "time": format_time_for_frontend(pyramid_time),
            "sentences": str(user_data.get("pyramid_stats", {}).get("sentences", 0)),
            "successRate": f"{pyramid_success:.1f}%",
        },
        "vocabulary": {
            "time": format_time_for_frontend(vocabulary_time),
            "vocabularies": str(user_data.get("vocabulary_stats", {}).get("vocabularies", 0)),
            "successRate": f"{vocabulary_success:.1f}%",
        }
    }

    return stats


def parse_time_to_seconds(time_str: str) -> int:
    """Parse time string like '10m 30s' to seconds"""
    total_seconds = 0
    if "m" in time_str:
        parts = time_str.split("m")
        if parts[0].strip():
            total_seconds += int(parts[0].strip()) * 60
        time_str = parts[1].strip()
    
    if "s" in time_str:
        time_str = time_str.replace("s", "").strip()
        if time_str:
            total_seconds += int(time_str)
    
    return total_seconds


def parse_percentage(percentage_str: str) -> float:
    """Parse percentage string like '95.5%' to float 95.5"""
    return float(percentage_str.replace("%", "").strip())


def update_user_statistics(user_id: str, stats_type: str, stats_data: Dict[str, Any]) -> bool:
    """Update statistics for a specific user"""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz kullanıcı ID",
        )

    if stats_type not in ["pyramid", "vocabulary"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz istatistik tipi. Kabul edilen değerler: 'pyramid', 'vocabulary'",
        )

    # Convert frontend values to database types
    db_data = {}
    if stats_type == "pyramid":
        if "time" in stats_data:
            # Convert time string to seconds
            db_data["time"] = parse_time_to_seconds(stats_data["time"])
        if "sentences" in stats_data:
            # Convert sentences to integer
            db_data["sentences"] = int(stats_data["sentences"])
        if "successRate" in stats_data:
            # Convert success rate to float
            db_data["success_rate"] = parse_percentage(stats_data["successRate"])
    else:  # vocabulary
        if "time" in stats_data:
            # Convert time string to seconds
            db_data["time"] = parse_time_to_seconds(stats_data["time"])
        if "vocabularies" in stats_data:
            # Convert total vocabularies to integer
            db_data["vocabularies"] = int(stats_data["vocabularies"])
        if "successRate" in stats_data:
            # Convert success rate to float
            db_data["success_rate"] = parse_percentage(stats_data["successRate"])

    update_field = f"{stats_type}_stats"
    
    # Use $set with dot notation to update specific fields
    update_data = {}
    for key, value in db_data.items():
        update_data[f"{update_field}.{key}"] = value

    result = user_table.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )

    return result.modified_count > 0
