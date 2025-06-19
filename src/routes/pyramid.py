from datetime import datetime
from fastapi import APIRouter, HTTPException, Body, Depends, Query
from typing import Dict, List, Any, Optional
from bson import ObjectId  # ObjectId importu eksikti

# Model importları artık bu dosyadan değil, src.models.pyramid'den yapılmalı
from src.models.user import UserOut
from src.models.pyramid import PyramidOut, PyramidItem  # PyramidItem da gerekiyor
from src.services import pyramid_service
from src.services.authentication_service import verify_token
from src.services.content_check_service import check_user_content
from src.services.event_service import (
    create_pyramid_event,
    add_pyramid_step,
    update_pyramid_event,
    get_pyramid_event,
    get_pyramid_event_by_id,
    complete_pyramid_event,
    get_recent_completed_pyramid_events
)

router = APIRouter(prefix="/pyramid", tags=["Pyramid Exercise"])


@router.get("/list", response_model=List[PyramidOut])
async def get_user_pyramids(
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    limit: Optional[int] = Query(50, description="Maximum number of pyramids to return"),
    offset: Optional[int] = Query(0, description="Number of pyramids to skip"),
    user: UserOut = Depends(verify_token),
):
    """Get all pyramids for the authenticated user with optional filtering."""
    try:
        pyramids = pyramid_service.get_user_pyramids(
            user_id=user.id,
            completed=completed,
            limit=limit,
            offset=offset
        )
        return pyramids
    except Exception as e:
        print(f"Error in /list: {e}")
        raise HTTPException(
            status_code=500, detail="Kullanıcı piramitleri alınırken bir sunucu hatası oluştu."
        )


@router.post("/create", response_model=PyramidOut)
async def create_pyramid_endpoint(
    data: dict = Body(..., example={"start_sentence": "Örnek bir başlangıç cümlesi"}),
    user: UserOut = Depends(verify_token),
):
    """Kullanıcı için bir piramit alıştırması başlatır."""
    try:
        start_sentence = data.get("start_sentence", "")
        
        # Check content appropriateness
        if start_sentence:
            check_user_content(start_sentence, "sentence", str(user.id))
        
        new_pyramid = pyramid_service.create_pyramid(user, start_sentence)
        return new_pyramid
    except ValueError as ve:
        print(f"!!! YAKALANAN HATA DETAYI: {ve}")  # <-- BU SATIRI EKLEYİN
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Üretimde daha genel bir hata mesajı
        print(f"Error in /create: {e}")
        raise HTTPException(
            status_code=500, detail="Piramit oluşturulurken bir sunucu hatası oluştu."
        )


@router.post(
    "/preview/next-step-options",
    response_model=Dict[
        str, Any
    ],  # Dönüş tipi PyramidState["previewData"]'ya uygun olmalı
    summary="Bir sonraki adım için önizleme seçenekleri üretir",
)
async def preview_next_step_options_endpoint(
    data: dict = Body(..., example={"pyramid_id": "piramit_id_buraya"}),
    user: UserOut = Depends(verify_token),
):
    """Piramit durumunu değiştirmeden bir sonraki adım için olası seçenekleri üretir."""
    try:
        pyramid_id = data.get("pyramid_id")
        if not pyramid_id or not isinstance(pyramid_id, str) or not pyramid_id.strip():
            raise HTTPException(
                status_code=422, detail="Geçerli bir piramit ID'si gereklidir."
            )

        # Yetkilendirme (pyramid_service içinde de yapılabilir ama burada da bir katman olması iyi)
        pyramid_doc = pyramid_service.pyramid_table.find_one(
            {"_id": ObjectId(pyramid_id)}
        )
        if not pyramid_doc:
            raise HTTPException(
                status_code=404, detail="Belirtilen ID ile piramit bulunamadı."
            )
        if pyramid_doc.get("user_id") != user.id:
            raise HTTPException(
                status_code=403, detail="Bu piramidi görüntüleme yetkiniz yok."
            )

        preview_data = pyramid_service.preview_next_step_options(pyramid_id, user)
        return preview_data
    except ValueError as ve:  # Servisten gelen beklenen hatalar
        raise HTTPException(status_code=422, detail=str(ve))
    except HTTPException:  # Zaten HTTPException ise yeniden fırlat
        raise HTTPException(status_code=500, detail="Bilinmeyen HTTP hatası oluştu.")
    except Exception as e:
        print(f"Error in /preview/next-step-options: {e}")
        raise HTTPException(
            status_code=500,
            detail="Önizleme seçenekleri alınırken bir sunucu hatası oluştu.",
        )


@router.post(
    "/update-step-selection",
    response_model=Dict[
        str, Any
    ],  # Örneğin: {"message": "...", "selected_sentence": "..."
    summary="Kullanıcının mevcut adımdaki seçimini kaydeder",
)
async def update_pyramid_step_selection_endpoint(
    data: dict = Body(
        ..., example={"pyramid_id": "piramit_id", "selected_option_index": 0}
    ),
    user: UserOut = Depends(verify_token),
):
    """Kullanıcının mevcut adımdaki seçilen opsiyonunu ve karşılık gelen cümleyi kaydeder."""
    try:
        pyramid_id = data.get("pyramid_id")
        selected_option_index = data.get("selected_option_index")

        if not pyramid_id or selected_option_index is None:
            raise HTTPException(
                status_code=422,
                detail="Piramit ID'si ve seçilen opsiyon indeksi gereklidir.",
            )
        if not isinstance(selected_option_index, int) or selected_option_index < 0:
            raise HTTPException(
                status_code=422,
                detail="Seçilen opsiyon indeksi geçerli bir pozitif tam sayı olmalıdır.",
            )

        pyramid_doc_auth = pyramid_service.pyramid_table.find_one(
            {"_id": ObjectId(pyramid_id)}
        )
        if not pyramid_doc_auth:
            raise HTTPException(status_code=404, detail="Piramit bulunamadı.")
        if pyramid_doc_auth.get("user_id") != user.id:
            raise HTTPException(
                status_code=403, detail="Bu piramidi güncelleme yetkiniz yok."
            )

        update_result = pyramid_service.save_user_selection_for_step(
            pyramid_id, selected_option_index
        )
        return (
            update_result  # Bu {"selected_sentence": "...", ...} gibi bir dict döndürür
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=400, detail=str(ve)
        )  # 400 Bad Request veya 404/422 olabilir
    except HTTPException:
        raise HTTPException(status_code=500, detail="Sunucu hatası oluştu.")
    except Exception as e:
        print(f"Error in /update-step-selection: {e}")
        raise HTTPException(
            status_code=500, detail="Seçim kaydedilirken bir sunucu hatası oluştu."
        )


@router.post(
    "/append-step",
    response_model=PyramidOut,
    summary="Önceden hazırlanmış bir adımı piramide ekler",
)
async def append_predefined_step_endpoint(
    data: Dict = Body(
        ..., example={"pyramid_id": "piramit_id", "next_step_item": "{...}"}
    ),
    user: UserOut = Depends(verify_token),
):
    """Frontend tarafından önceden oluşturulmuş ve kullanıcı tarafından seçilmiş bir sonraki adım verisini alıp piramide ekler."""
    try:
        pyramid_id = data.get("pyramid_id")
        next_step_item_dict = data.get("next_step_item")

        if not pyramid_id or not next_step_item_dict:
            raise HTTPException(
                status_code=422,
                detail="Piramit ID'si ve sonraki adım verisi gereklidir.",
            )
        if not isinstance(next_step_item_dict, dict):
            raise HTTPException(
                status_code=422,
                detail="Sonraki adım verisi sözlük formatında olmalıdır.",
            )

        pyramid_doc_auth = pyramid_service.pyramid_table.find_one(
            {"_id": ObjectId(pyramid_id)}
        )
        if not pyramid_doc_auth:
            raise HTTPException(status_code=404, detail="Piramit bulunamadı.")
        if pyramid_doc_auth.get("user_id") != user.id:
            raise HTTPException(
                status_code=403, detail="Bu piramidi güncelleme yetkiniz yok."
            )

        updated_pyramid = pyramid_service.append_given_step(
            pyramid_id, next_step_item_dict, user
        )
        return updated_pyramid  # Bu PyramidOut nesnesi olmalı
    except ValueError as ve:
        raise HTTPException(
            status_code=400, detail=str(ve)
        )  # Örn: Adım eklenemiyorsa (son adım vs.)
    except HTTPException:
        raise HTTPException(status_code=500, detail="Sunucu hatası oluştu.")
    except Exception as e:
        print(f"Error in /append-step: {e}")
        raise HTTPException(
            status_code=500, detail="Adım eklenirken bir sunucu hatası oluştu."
        )


@router.post(
    "/complete",
    response_model=Dict[str, Any],
    summary="Piramit alıştırmasını tamamlandı olarak işaretler",
)
async def complete_pyramid_endpoint(
    data: dict = Body(..., example={"pyramid_id": "piramit_id", "event_id": "event_id_optional", "skip_xp": False}),
    user: UserOut = Depends(verify_token),
):
    """Bir piramit alıştırmasını tamamlandı olarak işaretler ve isteğe bağlı olarak XP verir."""
    try:
        pyramid_id = data.get("pyramid_id")
        event_id = data.get("event_id")  # Optional event ID for tracking
        skip_xp = data.get("skip_xp", False)  # Flag to skip XP awarding
        
        if not pyramid_id:
            raise HTTPException(status_code=422, detail="Piramit ID'si gereklidir.")

        pyramid_doc_auth = pyramid_service.pyramid_table.find_one(
            {"_id": ObjectId(pyramid_id)}
        )
        if not pyramid_doc_auth:
            raise HTTPException(status_code=404, detail="Piramit bulunamadı.")
        if pyramid_doc_auth.get("user_id") != user.id:
            raise HTTPException(
                status_code=403, detail="Bu piramidi tamamlama yetkiniz yok."
            )
        if pyramid_doc_auth.get("completed"):
            return {"message": "Bu piramit zaten daha önce tamamlanmış.", "xp_earned": 0}

        if skip_xp:
            # Just mark as completed without XP
            pyramid_service.pyramid_table.update_one(
                {"_id": ObjectId(pyramid_id)},
                {"$set": {"completed": True, "updated_at": datetime.utcnow()}},
            )
            return {
                "message": "Piramit başarıyla tamamlandı.",
                "xp_earned": 0
            }
        else:
            # Complete the pyramid and award XP
            completion_result = await pyramid_service.complete_pyramid_with_xp(pyramid_id, user.id, event_id)
            
            return {
                "message": "Piramit başarıyla tamamlandı.",
                "xp_earned": completion_result.get("xp_earned", 0)
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /complete: {e}")
        raise HTTPException(
            status_code=500, detail="Piramit tamamlanırken bir sunucu hatası oluştu."
        )


@router.get(
    "/get/{pyramid_id}",
    response_model=PyramidOut,
    summary="ID ile piramit verisini getirir",
)
async def get_pyramid_endpoint(
    pyramid_id: str,
    user: UserOut = Depends(verify_token),
):
    """ID ile belirtilen piramidin verilerini getirir."""
    try:
        if not pyramid_id.strip():  # Boşluk kontrolü
            raise HTTPException(
                status_code=422, detail="Geçerli bir piramit ID'si gereklidir."
            )

        # get_pyramid_by_id Pyramid modelini döndürür.
        # FastAPI bunu response_model'e göre (PyramidOut) otomatik serialize eder.
        pyramid_model_instance = pyramid_service.get_pyramid_by_id(
            pyramid_id
        )  # Bu Pyramid Pydantic modelini döndürür

        # Yetkilendirme (get_pyramid_by_id içinde yapılmıyorsa burada yapılmalı)
        if pyramid_model_instance.user_id != user.id:
            raise HTTPException(
                status_code=403, detail="Bu piramidi görüntüleme yetkiniz yok."
            )

        return pyramid_model_instance  # FastAPI otomatik olarak PyramidOut'a dönüştürecektir (alanlar eşleşiyorsa)
        # Ya da manuel PyramidOut oluşturulabilir: PyramidOut.model_validate(pyramid_model_instance)
    except ValueError as ve:  # get_pyramid_by_id "Piramit bulunamadı" hatası fırlatırsa
        raise HTTPException(status_code=404, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /get/{pyramid_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Piramit verisi alınırken bir sunucu hatası oluştu."
        )


# Fallback olarak tutulan /create/next-step-options (isteğe bağlı)
# Eğer bu endpoint'i kaldırmayı düşünüyorsanız, buradan silebilirsiniz.
@router.delete(
    "/delete/{pyramid_id}",
    response_model=Dict[str, str],
    summary="Piramidi siler",
)
async def delete_pyramid_endpoint(
    pyramid_id: str,
    user: UserOut = Depends(verify_token),
):
    """Belirtilen ID'ye sahip piramidi siler."""
    try:
        if not pyramid_id.strip():
            raise HTTPException(
                status_code=422, detail="Geçerli bir piramit ID'si gereklidir."
            )

        result = pyramid_service.delete_pyramid(pyramid_id, user.id)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /delete/{pyramid_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Piramit silinirken bir sunucu hatası oluştu."
        )


@router.post(
    "/create/next-step-options-fallback",
    response_model=PyramidOut,
    summary="Bir sonraki adımı oluşturur (Fallback)",
    include_in_schema=False,
)
async def create_next_step_fallback_endpoint(
    data: dict = Body(...),
    user: UserOut = Depends(verify_token),
):
    """
    Piramidin bir sonraki adımını oluşturur ve ekler (piramit durumunu ilerletir).
    Bu endpoint, /append-step için önizleme verisi olmadığında bir fallback olarak kullanılabilir.
    """
    try:
        pyramid_id = data.get("pyramid_id")
        if not pyramid_id:
            raise HTTPException(status_code=422, detail="Piramit ID'si gereklidir.")

        pyramid_doc_auth = pyramid_service.pyramid_table.find_one(
            {"_id": ObjectId(pyramid_id)}
        )
        if not pyramid_doc_auth:
            raise HTTPException(status_code=404, detail="Piramit bulunamadı.")
        if pyramid_doc_auth.get("user_id") != user.id:
            raise HTTPException(
                status_code=403, detail="Bu piramidi güncelleme yetkiniz yok."
            )

        # Bu fonksiyon, önceki analizimizdeki gibi, kullanıcının son seçtiği cümleyi kullanacak şekilde
        # pyramid_service içinde güncellenmiş olmalı.
        updated_pyramid = pyramid_service.create_next_step_options(pyramid_id, user)
        return updated_pyramid
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /create/next-step-options-fallback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Bir sonraki adım oluşturulürken bir sunucu hatası oluştu (fallback).",
        )


# ==================== PYRAMID EVENT ENDPOINTS ====================

@router.post(
    "/event/create",
    response_model=Dict[str, Any],
    summary="Create a new pyramid event for tracking"
)
async def create_pyramid_event_endpoint(
    data: dict = Body(..., example={"pyramid_id": "pyramid_id_here"}),
    user: UserOut = Depends(verify_token),
):
    """Create a new pyramid event to track user progress."""
    try:
        pyramid_id = data.get("pyramid_id")
        if not pyramid_id:
            raise HTTPException(status_code=422, detail="Pyramid ID is required.")
        
        # Verify pyramid belongs to user
        pyramid_doc = pyramid_service.pyramid_table.find_one({"_id": ObjectId(pyramid_id)})
        if not pyramid_doc:
            raise HTTPException(status_code=404, detail="Pyramid not found.")
        if pyramid_doc.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Access denied to this pyramid.")
        
        event = create_pyramid_event(user.id, pyramid_id)
        return {
            "message": "Pyramid event created successfully.",
            "event_id": event["_id"],
            "pyramid_id": pyramid_id
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating pyramid event: {e}")
        raise HTTPException(status_code=500, detail="Error creating pyramid event.")


@router.put(
    "/event/{event_id}/add-step",
    response_model=Dict[str, Any],
    summary="Add a step to an existing pyramid event"
)
async def add_pyramid_step_endpoint(
    event_id: str,
    data: dict = Body(..., example={"step": {...}, "step_type": "expand"}),
    user: UserOut = Depends(verify_token),
):
    """Add a completed step to the pyramid event for tracking."""
    try:
        step_data = data.get("step")
        step_type = data.get("step_type")
        
        if not step_data or not step_type:
            raise HTTPException(status_code=422, detail="Step data and step type are required.")
        
        # Verify event belongs to user
        event = get_pyramid_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found.")
        if event.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Access denied to this event.")
        
        updated_event = add_pyramid_step(event_id, step_data, step_type)
        return {
            "message": "Step added to pyramid event successfully.",
            "event_id": event_id,
            "total_steps": updated_event.get("details", {}).get("total_steps", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error adding step to pyramid event: {e}")
        raise HTTPException(status_code=500, detail="Error adding step to pyramid event.")


@router.put(
    "/event/{event_id}/complete",
    response_model=Dict[str, Any],
    summary="Complete a pyramid event and calculate XP"
)
async def complete_pyramid_event_endpoint(
    event_id: str,
    user: UserOut = Depends(verify_token),
):
    """Complete a pyramid event and award XP to the user."""
    try:
        # Verify event belongs to user
        event = get_pyramid_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found.")
        if event.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Access denied to this event.")
        
        completed_event = await complete_pyramid_event(event_id)
        if not completed_event:
            raise HTTPException(status_code=500, detail="Failed to complete pyramid event.")
        
        xp_earned = completed_event.get("details", {}).get("xp_earned", 0)
        return {
            "message": "Pyramid event completed successfully.",
            "event_id": event_id,
            "xp_earned": xp_earned,
            "duration_seconds": completed_event.get("details", {}).get("duration_seconds", 0),
            "accuracy_rate": completed_event.get("details", {}).get("accuracy_rate", 0.0),
            "avg_time_per_step": completed_event.get("details", {}).get("avg_time_per_step", 0.0)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error completing pyramid event: {e}")
        raise HTTPException(status_code=500, detail="Error completing pyramid event.")


@router.get(
    "/event/{event_id}",
    response_model=Dict[str, Any],
    summary="Get pyramid event details"
)
async def get_pyramid_event_endpoint(
    event_id: str,
    user: UserOut = Depends(verify_token),
):
    """Get details of a specific pyramid event."""
    try:
        event = get_pyramid_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found.")
        if event.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Access denied to this event.")
        
        return {
            "event_id": event_id,
            "pyramid_id": event.get("event_id"),
            "completed": event.get("details", {}).get("completed", False),
            "total_steps": event.get("details", {}).get("total_steps", 0),
            "completed_steps": event.get("details", {}).get("completed_steps", 0),
            "duration_seconds": event.get("details", {}).get("duration_seconds", 0),
            "accuracy_rate": event.get("details", {}).get("accuracy_rate", 0.0),
            "avg_time_per_step": event.get("details", {}).get("avg_time_per_step", 0.0),
            "xp_earned": event.get("details", {}).get("xp_earned", 0),
            "session_start": event.get("details", {}).get("session_start"),
            "session_end": event.get("details", {}).get("session_end"),
            "step_types": event.get("details", {}).get("step_types", [])
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting pyramid event: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving pyramid event.")


@router.get(
    "/events/recent",
    response_model=List[Dict[str, Any]],
    summary="Get recent completed pyramid events"
)
async def get_recent_pyramid_events_endpoint(
    days: int = Query(5, description="Number of days to look back"),
    user: UserOut = Depends(verify_token),
):
    """Get recent completed pyramid events for the user."""
    try:
        events = get_recent_completed_pyramid_events(user.id, days)
        
        result = []
        for event in events:
            result.append({
                "event_id": str(event["_id"]),
                "pyramid_id": event.get("event_id"),
                "timestamp": event.get("timestamp"),
                "completed": event.get("details", {}).get("completed", False),
                "total_steps": event.get("details", {}).get("total_steps", 0),
                "duration_seconds": event.get("details", {}).get("duration_seconds", 0),
                "accuracy_rate": event.get("details", {}).get("accuracy_rate", 0.0),
                "xp_earned": event.get("details", {}).get("xp_earned", 0),
                "step_types": event.get("details", {}).get("step_types", [])
            })
        
        return result
    except Exception as e:
        print(f"Error getting recent pyramid events: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving recent pyramid events.")
