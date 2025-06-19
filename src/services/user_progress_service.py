from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import HTTPException
from src.database.database import user_progress_table, user_table
from src.services.xp_service import get_xp
from typing import Dict, Any, Optional

async def get_user_progress(user_id: str) -> Dict[str, Any]:
    """Kullanıcının ilerleme verisini alır"""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Kullanıcı var mı kontrol et
    user_data = user_table.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Kullanıcının XP verisini al
    user_xp_data = await get_xp(user_id)
    user_xp = user_xp_data.get("xp", 0) if user_xp_data else 0
    
    # İlerleme verisini al veya yeni oluştur
    progress_data = user_progress_table.find_one({"user_id": user_id})
    
    if not progress_data:
        # Yeni kullanıcı için ilerleme verisini oluştur
        current_date = datetime.now()
        start_of_week = current_date - timedelta(days=current_date.weekday())
        
        # Varsayılan haftalık hedef
        default_weekly_goal = 1000
        
        # Şu anki ilerlemeyi kullanıcının XP'si ile hesapla
        current_xp_for_week = min(user_xp, default_weekly_goal)  # Bu haftaya atanan XP
        progress_percentage = current_xp_for_week / default_weekly_goal
        remaining_xp = max(default_weekly_goal - current_xp_for_week, 0)
        
        default_progress = {
            "user_id": user_id,
            "progress": progress_percentage,
            "weekly_goal": default_weekly_goal, 
            "remaining": remaining_xp,
            "current_xp": current_xp_for_week,
            "week_start": start_of_week,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        user_progress_table.insert_one(default_progress)
        return default_progress
    
    # Hafta değişmiş mi kontrol et
    current_date = datetime.now()
    stored_week_start = progress_data.get("week_start")
    
    if stored_week_start and (current_date - stored_week_start).days >= 7:
        # Yeni hafta, progress'i XP'ye göre yeniden hesapla
        start_of_week = current_date - timedelta(days=current_date.weekday())
        weekly_goal = progress_data.get("weekly_goal", 1000)
        
        # Bu haftaya son XP'nin bir kısmını (örn. %25) atayalım
        current_week_xp = int(user_xp * 0.25)  # Son XP'nin %25'i bu haftaya
        current_week_xp = min(current_week_xp, weekly_goal)  # Hedefi aşmasını önle
        
        new_progress = current_week_xp / weekly_goal
        new_remaining = max(weekly_goal - current_week_xp, 0)
        
        user_progress_table.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "progress": new_progress,
                    "remaining": new_remaining,
                    "current_xp": current_week_xp,
                    "week_start": start_of_week,
                    "updated_at": datetime.now()
                }
            }
        )
        
        progress_data = user_progress_table.find_one({"user_id": user_id})
    
    # XP güncellemelerini kontrol et ve haftalık ilerlemeyi güncelle
    # Eğer kullanıcının XP'si, kayıtlı weekly_goal + current_xp'den büyükse, bir güncelleme olmuş demektir
    stored_weekly_goal = progress_data.get("weekly_goal", 1000)
    stored_current_xp = progress_data.get("current_xp", 0)
    
    # Kullanıcı yeni XP kazanmış olabilir, güncelleme yapalım
    if user_xp > stored_current_xp:
        # XP değişimi (bu hafta içinde kazanılan XP)
        xp_change = min(user_xp - stored_current_xp, stored_weekly_goal - stored_current_xp)
        
        # Sadece pozitif değişim varsa güncelleme yap
        if xp_change > 0:
            new_current_xp = stored_current_xp + xp_change
            new_progress = min(new_current_xp / stored_weekly_goal, 1.0)
            new_remaining = max(stored_weekly_goal - new_current_xp, 0)
            
            user_progress_table.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "progress": new_progress,
                        "remaining": new_remaining,
                        "current_xp": new_current_xp,
                        "updated_at": datetime.now()
                    }
                }
            )
            
            progress_data = user_progress_table.find_one({"user_id": user_id})
    
    return progress_data

async def update_user_progress(user_id: str, current_xp: int) -> Dict[str, Any]:
    """Kullanıcının ilerleme verisini günceller"""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Mevcut ilerleme verisini al
    progress_data = await get_user_progress(user_id)
    
    # Kullanıcının toplam XP verisini güncelle
    user_data = await get_xp(user_id)
    if user_data:
        existing_xp = user_data.get("xp", 0)
        
        # XP artışı varsa kullanıcının toplam XP'sini güncelle
        if current_xp > existing_xp:
            from src.services.xp_service import update_xp
            await update_xp(user_id, current_xp)
    
    # Haftalık hedef ve ilerlemeyi hesapla
    weekly_goal = progress_data.get("weekly_goal", 1000)
    new_progress = min(current_xp / weekly_goal, 1.0)
    remaining = max(weekly_goal - current_xp, 0)
    
    # Veritabanını güncelle
    user_progress_table.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "progress": new_progress,
                "remaining": remaining,
                "current_xp": current_xp,
                "updated_at": datetime.now()
            }
        }
    )
    
    return {
        "progress": new_progress,
        "remaining": remaining,
        "current_xp": current_xp,
        "weekly_goal": weekly_goal
    }

async def set_weekly_goal(user_id: str, goal: int) -> Dict[str, Any]:
    """Kullanıcının haftalık hedefini günceller"""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    if goal <= 0:
        raise HTTPException(status_code=400, detail="Weekly goal must be positive")
    
    # Mevcut ilerleme verisini al
    progress_data = await get_user_progress(user_id)
    current_xp = progress_data.get("current_xp", 0)
    
    # Yeni progress ve remaining değerlerini hesapla
    new_progress = min(current_xp / goal, 1.0)
    remaining = max(goal - current_xp, 0)
    
    # Veritabanını güncelle
    user_progress_table.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "weekly_goal": goal,
                "progress": new_progress,
                "remaining": remaining,
                "updated_at": datetime.now()
            }
        }
    )
    
    return {
        "weekly_goal": goal,
        "progress": new_progress,
        "remaining": remaining,
        "current_xp": current_xp
    }
