from typing import List, Dict, Any
from src.database.database import user_table
from bson import ObjectId


def get_leaderboard() -> Dict[str, Any]:
    """
    Liderlik tablosu verilerini getiren fonksiyon.
    """
    leaderboard_data = []

    # XP sıralamasına göre azalan şekilde kullanıcıları çek
    cursor = (
        user_table.find({"xp": {"$exists": True}}, {"_id": 1, "username": 1, "xp": 1})
        .sort("xp", -1)
        .limit(100)
    )  # En iyi 100 kullanıcı

    rank = 1
    for user_data in cursor:
        leaderboard_data.append(
            {"rank": rank, "username": user_data["username"], "xp": user_data.get("xp", 0)}
        )
        rank += 1

    return {"leaderboard": leaderboard_data}


def get_leaderboard_for_user(user_id: str) -> Dict[str, Any]:
    """
    Kullanıcının da bulunduğu 4 kişilik liderlik tablosunu getiren fonksiyon.
    """
    leaderboard_data = []
    # Kullanıcı ilk 4 içindeyse ilk 4'ü, değilse kullanıcının sıralamasını ve çevresindekileri al
    # Kullanıcının ismini "You" olarak gösteriyoruz
    user_rank = get_user_rank(user_id)
    if user_rank["rank"] <= 4:
        cursor = (
            user_table.find({"xp": {"$exists": True}}, {"_id": 1, "username": 1, "xp": 1})
            .sort("xp", -1)
            .limit(4)
        )
        rank = 1
        for user_data in cursor:
            if user_data["_id"] == ObjectId(user_id):
                leaderboard_data.append(
                    {"rank": rank, "username": "You", "xp": user_data.get("xp", 0)}
                )
            else:
                leaderboard_data.append(
                    {"rank": rank, "username": user_data["username"], "xp": user_data.get("xp", 0)}
                )
            rank += 1
    else:
        lower_bound = max(1, user_rank["rank"] - 2)
        upper_bound = user_rank["rank"] + 2
        cursor = (
            user_table.find({"xp": {"$exists": True}})
            .sort("xp", -1)
        )
        rank = 1
        for user_data in cursor:
            if lower_bound <= rank <= upper_bound:
                if user_data["_id"] == ObjectId(user_id):
                    leaderboard_data.append(
                        {"rank": rank, "username": "You", "xp": user_data.get("xp", 0)}
                    )
                else:
                    leaderboard_data.append(
                        {"rank": rank, "username": user_data["username"], "xp": user_data.get("xp", 0)}
                    )
            rank += 1

    return {"leaderboard": leaderboard_data}

def get_user_rank(user_id: str) -> Dict[str, Any]:
    """
    Belirli bir kullanıcının sıralamasını ve XP'sini getiren fonksiyon.
    """
    # Kullanıcıyı bul
    user_data = user_table.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        return {"rank": 0, "username": "Unknown", "xp": 0}

    # Kullanıcının XP'sinden daha yüksek XP'si olan kullanıcıların sayısını bul
    higher_rank_count = user_table.count_documents({"xp": {"$gt": user_data.get("xp", 0)}})

    # Sıralama 1'den başladığı için +1 ekliyoruz
    rank = higher_rank_count + 1

    return {
        "rank": rank,
        "username": "You",  # Frontend'de gösterilecek şekilde "You" olarak işaretliyoruz
        "xp": user_data.get("xp", 0),
    }
