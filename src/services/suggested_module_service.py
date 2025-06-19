from collections import Counter
from src.models.user_event import EventType
from src.services.event_service import get_recent_learning_events, get_recent_completed_vocabulary_events

def get_suggested_module_type(user_id: str):
    """
    Kullanıcıya önerilecek modül tipini belirler.
    Son 5 günlük aktivitelere bakarak, hiç yapılmamış veya en az yapılmış aktiviteyi önerir.
    Vocabulary modülü için sadece tamamlanmış listeler dikkate alınır.
    
    Args:
        user_id (str): Kullanıcı ID
        
    Returns:
        str: Önerilen modül tipi
    """
    # Son 5 günlük aktiviteleri al
    recent_events = get_recent_learning_events(user_id)
    
    # Tüm olası modül tipleri
    all_module_types = {
        EventType.PYRAMID.value,
        EventType.VOCABULARY.value,
        EventType.WRITING.value,
        EventType.EMAIL.value
    }
    
    # Son 5 gündeki event tiplerini say
    event_counts = Counter()
    
    # Vocabulary dışındaki diğer event tiplerini say
    for event in recent_events:
        if event['event_type'] != EventType.VOCABULARY.value:
            event_counts[event['event_type']] += 1
    
    # Tamamlanmış vocabulary listelerini al ve say
    completed_vocab_events = get_recent_completed_vocabulary_events(user_id)
    if completed_vocab_events:
        event_counts[EventType.VOCABULARY.value] = len(completed_vocab_events)
    
    # Hiç yapılmamış aktiviteleri bul
    unused_types = all_module_types - set(event_counts.keys())
    
    if unused_types:
        # Hiç yapılmamış bir aktivite varsa onu öner
        return next(iter(unused_types))
    else:
        # Tüm aktiviteler yapılmışsa, en az yapılanı öner
        return min(event_counts.items(), key=lambda x: x[1])[0]