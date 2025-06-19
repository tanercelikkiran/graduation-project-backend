from typing import List
from pydantic import BaseModel
from datetime import datetime, timedelta
from collections import defaultdict
from src.services.event_service import get_recent_learning_events

class WeeklyProgressResponse(BaseModel):
    labels: List[str]
    data: List[int]

async def get_weekly_progress(user_id) -> WeeklyProgressResponse:
    # Son 7 günlük verileri al
    events = get_recent_learning_events(user_id=user_id, days=7)
    
    # Günlük XP'leri topla
    daily_xp = defaultdict(int)
    
    # Event tabanlı hesaplama - sadece gerçek etkinliklerden XP göster
    for event in events:
        # Timestamp'i datetime'a çevir ve gün başlangıcına ayarla
        event_date = event['timestamp'].replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Event'in XP değerini al (varsayılan 10 XP)
        xp = event.get('details', {}).get('xp_earned', 10)
        
        # Günlük toplama ekle
        daily_xp[event_date] = daily_xp[event_date] + xp
    
    # Son 7 günün tarihlerini oluştur
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    
    # Günleri API formatında döndürmek için
    day_names = {
        0: "monday",
        1: "tuesday",
        2: "wednesday",
        3: "thursday",
        4: "friday",
        5: "saturday",
        6: "sunday",
    }
    
    # Tarihleri gün isimlerine çevir ve her gün için XP değerlerini al
    labels = [day_names[date.weekday()] for date in dates]
    data = [daily_xp[date] for date in dates]
    
    return WeeklyProgressResponse(labels=labels, data=data)