from bson import ObjectId
from src.database.database import user_table


async def get_xp(user_id: str):
    """
    Get user data including XP
    """
    if not ObjectId.is_valid(user_id):
        return None

    user_data = user_table.find_one({"_id": ObjectId(user_id)})
    if user_data:
        # Include xp in the response, default to 0 if not present
        return {
            "id": str(user_data["_id"]),
            "username": user_data.get("username", ""),
            "email": user_data.get("email", ""),
            "xp": user_data.get("xp", 0),
            "learning_language": user_data.get("learning_language", ""),
            "purpose": user_data.get("purpose", ""),
            "level": user_data.get("level", ""),
        }
    return None


async def update_xp(user_id: str, amount: int):
    """
    Update user XP
    """
    if not ObjectId.is_valid(user_id):
        return None

    # Set the new XP value, ensuring it's an integer
    if not isinstance(amount, int):
        return None

    user_table.update_one({"_id": ObjectId(user_id)}, {"$set": {"xp": amount}})
    return True
