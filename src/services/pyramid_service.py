from concurrent.futures import ThreadPoolExecutor
import random
from datetime import datetime, timezone
from typing import Dict, List, Union, Optional

from bson import ObjectId

# Model importları src.models.pyramid'den yapılmalı
from src.models.pyramid import (
    Pyramid,  # Ana DB modeli (alias _id içerir)
    PyramidOut,  # API çıkış modeli
    PyramidItem,  # Union tipi: PyramidExpandItem, PyramidShrinkItem, etc.
    PyramidOptionsBase,
    PyramidShrinkOptions,
    PyramidExpandOptions,
    PyramidReplaceOptions,
    PyramidParaphOptions,
    PyramidShrinkItem,
    PyramidExpandItem,
    PyramidReplaceItem,
    PyramidParaphItem,
    PyramidOptionConcreteTypes,  # T için kullanılan Union
)
from src.models.user import UserOut
from src.api_clients.pyramid_prompts import (
    shrink_sentence as ai_shrink_sentence,
    expand_sentence as ai_expand_sentence,
    replace_word as ai_replace_word,
    paraphrase_sentence as ai_paraphrase_sentence,
    get_first_sentence as ai_get_first_sentence,
)
from src.database.database import user_table, pyramid_table
from src.services.event_service import (
    create_pyramid_event,
    get_pyramid_event_by_id,
    update_pyramid_event,
    complete_pyramid_event,
)
from src.services.xp_service import get_xp, update_xp


def _collect_option_words_from_previous_steps(
    pyramid_steps: List[PyramidItem],
) -> List[str]:
    """
    Collect all option_words from previous pyramid steps to avoid repetition in AI generation.

    Args:
        pyramid_steps: List of completed pyramid steps

    Returns:
        List of words that should be excluded from future AI generation
    """
    all_option_words = []
    for step in pyramid_steps:
        if hasattr(step, "option_words") and step.option_words:
            all_option_words.extend(step.option_words)

    # Remove duplicates while preserving order
    seen = set()
    unique_words = []
    for word in all_option_words:
        if word and word.lower() not in seen:
            seen.add(word.lower())
            unique_words.append(word)

    return unique_words


# Pydantic modelleri zaten `src.models.pyramid` altında tanımlı, burada tekrar tanımlamaya gerek yok.
# PyramidStepTypeModels = Union[PyramidExpandItem, PyramidParaphItem, PyramidReplaceItem, PyramidShrinkItem] # Bu zaten PyramidItem


def _parse_step_item_from_dict(step_dict: Dict, expected_step_type: str) -> PyramidItem:
    """Gelen sözlüğü, beklenen adım türüne göre Pydantic modeline dönüştürür."""
    # step_dict['step_type'] alanı, preview_next_step_options tarafından doldurulmuş olabilir.
    # expected_step_type ise pyramid.step_types listesinden gelir. İkisi tutarlı olmalı.

    # Gelen dict'in Pydantic modelinin __init__ metoduna uygun olması gerekir.
    # Model dosyalarında step_type alanları Literal olarak tanımlandığı için,
    # Pydantic gelen dict'teki step_type ile modeldeki Literal'ı eşleştirecektir.
    try:
        if expected_step_type == "expand":
            return PyramidExpandItem.model_validate(step_dict)
        elif expected_step_type == "paraphrase":
            # PyramidParaphOptions, options listesinde PyramidParaphItem içinde olacak
            return PyramidParaphItem.model_validate(step_dict)
        elif expected_step_type == "replace":
            return PyramidReplaceItem.model_validate(step_dict)
        elif expected_step_type == "shrink":
            return PyramidShrinkItem.model_validate(step_dict)
        else:
            raise ValueError(
                f"Bilinmeyen veya beklenmeyen adım türü ({expected_step_type}) için ayrıştırma yapılamadı."
            )
    except Exception as e:  # PydanticValidationError dahil
        # print(f"Pydantic validation error while parsing step item for type {expected_step_type}: {e}")
        # print(f"Data causing error: {step_dict}")
        raise ValueError(
            f"Adım verisi ({expected_step_type}) Pydantic modeline dönüştürülemedi: {e}"
        )


def create_pyramid(user: UserOut, start_sentence_str: str) -> PyramidOut:
    user_from_db = user_table.find_one({"_id": ObjectId(user.id)})
    if not user_from_db:
        raise ValueError("Kullanıcı bulunamadı ve piramit oluşturulamadı.")

    # Use level from authenticated user if present, otherwise fall back to DB
    user_level = getattr(user, "level", None) or user_from_db.get("level")
    if not user_level:
        raise ValueError("Kullanıcı seviyesi bulunamadı ve piramit oluşturulamadı.")

    # purpose alanı UserOut modelinde varsa user.purpose, yoksa DB'den veya varsayılan.
    # UserOut modelinizde purpose alanı olduğunu varsayıyorum.
    user_purpose = getattr(
        user, "purpose", "General Knowledge"
    )  # UserOut'ta purpose yoksa varsayılan

    sentence_for_first_step = (
        start_sentence_str
        if start_sentence_str
        else get_initial_sentence(user.learning_language, user_level, user_purpose)
    )

    total_steps = set_total_steps(user_level)
    step_types = set_step_types(total_steps, user_level)
    if not step_types:
        raise ValueError("Piramit için adım türleri oluşturulamadı.")

    pyramid_mongo_id = ObjectId()
    first_step_type = step_types[0]

    step_creator_fn_map = {
        "expand": create_expand_options,
        "paraphrase": create_paraphrase_options,
        "replace": create_replace_options,
        "shrink": create_shrink_options,
    }
    creator_fn = step_creator_fn_map.get(first_step_type)
    if not creator_fn:
        raise ValueError(
            f"Geçersiz ilk adım türü: {first_step_type}"
        )  # creator_fn PyramidItem (Union) tipinde bir nesne döndürmeli
    # For the first step, there are no previous option_words to exclude
    first_step_item: PyramidItem = creator_fn(
        sentence_for_first_step,
        user.learning_language,
        user.system_language,
        user_purpose,
        user_level,
        [],  # No excluded words for first step
    )

    pyramid_instance_data = {
        "_id": str(pyramid_mongo_id),  # Pydantic modeli için str ID
        "user_id": user.id,
        "step_types": step_types,
        "steps": [first_step_item],
        "total_steps": total_steps,
        "last_step": 0,
        "completed": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    # Pydantic modelini oluştur (DB'ye yazmadan önce)
    pyramid_pydantic_instance = Pyramid.model_validate(pyramid_instance_data)

    # Veritabanına yazmak için Pydantic modelini MongoDB'ye uygun dict'e çevir
    # _id ObjectId olmalı, diğer alanlar Pydantic modelinden.
    pyramid_dict_for_db = pyramid_pydantic_instance.model_dump(
        by_alias=True
    )  # by_alias _id'yi handle eder
    pyramid_dict_for_db["_id"] = pyramid_mongo_id  # ObjectId olarak ayarla

    pyramid_table.insert_one(pyramid_dict_for_db)
    user_table.update_one(
        {"_id": ObjectId(user.id)}, {"$push": {"pyramids": str(pyramid_mongo_id)}}
    )

    # create_pyramid_event(user.id, str(pyramid_mongo_id)) # Gerekirse

    return PyramidOut.model_validate(
        pyramid_pydantic_instance.model_dump()
    )  # Pyramid'den PyramidOut'a


def get_initial_sentence(learning_language: str, user_level: str, purpose: str) -> str:
    try:
        ai_sentence = ai_get_first_sentence(
            learning_language, user_level=user_level, purpose=purpose
        )
        if (
            ai_sentence and isinstance(ai_sentence, str) and ai_sentence.strip()
        ):  # AI'dan boş string gelme ihtimaline karşı
            return ai_sentence.strip()
    except Exception as e:
        print(f"AI ile ilk cümle üretimi başarısız: {e}")

    # Varsayılan cümleler (AI başarısız olursa)
    # Bu cümleler, prompt'taki kurallara (uzunluk, kelime çeşitliliği vb.) uygun olmalı
    if learning_language == "Turkish":
        if user_level.startswith("A"):
            return "Ali dün okula gitmedi çünkü hastaydı."
        else:
            return "Dün gece nerede olduğunu bilmemesine rağmen sıkıntıyla aramaya devam etti."
    elif learning_language == "English":
        if user_level.startswith("A"):
            return "My friend has a new car and it is red."
        else:
            return "Despite not knowing where he was last night, he continued to search in distress."
    return f"This is a default sentence for {learning_language} ({user_level})."


def get_pyramid_by_id(
    pyramid_id: str,
) -> Pyramid:  # Artık ana Pyramid modelini döndürüyor
    pyramid_data_dict = pyramid_table.find_one({"_id": ObjectId(pyramid_id)})
    if not pyramid_data_dict:
        raise ValueError("Piramit bulunamadı.")

    pyramid_data_dict["_id"] = str(pyramid_data_dict["_id"])

    try:
        return Pyramid.model_validate(pyramid_data_dict)
    except Exception as e:  # PydanticValidationError
        print(
            f"Piramit verisi ({pyramid_id}) Pydantic modeline dönüştürülürken hata: {e}"
        )
        print(f"Hatalı veri: {pyramid_data_dict}")
        raise ValueError(f"Piramit verisi ({pyramid_id}) okunamadı veya bozuk.")


def get_user_pyramids(
    user_id: str,
    completed: Optional[bool] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
) -> List[PyramidOut]:
    """Get all pyramids for a specific user from user's pyramids field."""
    from src.database.database import user_table

    # First, get the user and their pyramid IDs
    user_doc = user_table.find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        return []

    pyramid_ids = user_doc.get("pyramids", [])
    if not pyramid_ids:
        return []

    # Convert string IDs to ObjectIds
    pyramid_object_ids = []
    for pid in pyramid_ids:
        try:
            pyramid_object_ids.append(ObjectId(pid))
        except Exception as e:
            print(f"Invalid pyramid ID {pid}: {e}")
            continue

    if not pyramid_object_ids:
        return []

    # Build query to find pyramids by IDs
    query = {"_id": {"$in": pyramid_object_ids}}

    # Add completion filter if specified
    if completed is not None:
        query["completed"] = completed

    # Query the database with pagination, sorted by creation date (newest first)
    cursor = pyramid_table.find(query).sort("created_at", -1).skip(offset).limit(limit)

    pyramids = []
    for pyramid_doc in cursor:
        pyramid_doc["_id"] = str(pyramid_doc["_id"])
        try:
            pyramid_model = Pyramid.model_validate(pyramid_doc)
            pyramids.append(PyramidOut.model_validate(pyramid_model.model_dump()))
        except Exception as e:
            print(f"Error parsing pyramid {pyramid_doc.get('_id', 'unknown')}: {e}")
            continue

    return pyramids


def save_user_selection_for_step(pyramid_id: str, selected_option_index: int) -> Dict:
    pyramid = get_pyramid_by_id(pyramid_id)  # Pyramid Pydantic modeli
    if pyramid.completed:
        raise ValueError("Bu piramit zaten tamamlanmış, seçim kaydedilemez.")
    if pyramid.last_step >= len(pyramid.steps):
        raise ValueError("Piramitte tutarsız adım verisi veya son adımda hata.")

    current_step_item = pyramid.steps[pyramid.last_step]
    if not current_step_item.options or not (
        0 <= selected_option_index < len(current_step_item.options)
    ):
        raise ValueError(
            "Geçersiz seçenek indeksi veya mevcut adımda seçenek bulunmuyor."
        )

    selected_option_obj: PyramidOptionConcreteTypes = current_step_item.options[
        selected_option_index
    ]

    selected_sentence_str = ""
    if isinstance(selected_option_obj, PyramidParaphOptions):
        selected_sentence_str = selected_option_obj.paraphrased_sentence
    elif hasattr(
        selected_option_obj, "sentence"
    ):  # Diğer tüm option tipleri (Expand, Shrink, Replace) 'sentence' alanına sahip olmalı
        selected_sentence_str = getattr(selected_option_obj, "sentence")

    if not selected_sentence_str:
        raise ValueError(
            f"Seçilen opsiyondan ({selected_option_obj}) geçerli bir cümle çıkarılamadı."
        )

    # Pydantic modelini güncelle (bu DB'ye yazılmaz, sadece bir sonraki adım için temel oluşturur)
    pyramid.steps[pyramid.last_step].selected_option = selected_option_index
    pyramid.steps[pyramid.last_step].selected_sentence = selected_sentence_str
    pyramid.updated_at = datetime.now(timezone.utc)

    # Veritabanında SADECE o adımı ve updated_at'i güncelle
    update_fields_for_db = {
        f"steps.{pyramid.last_step}.selected_option": selected_option_index,
        f"steps.{pyramid.last_step}.selected_sentence": selected_sentence_str,
        "updated_at": pyramid.updated_at,
    }

    result = pyramid_table.update_one(
        {"_id": ObjectId(pyramid_id)}, {"$set": update_fields_for_db}
    )
    if result.modified_count == 0:
        print(
            f"Uyarı: save_user_selection_for_step - Piramit {pyramid_id} için güncelleme 0 dokümanı etkiledi."
        )

    return {
        "message": "Seçim başarıyla kaydedildi.",
        "selected_sentence": selected_sentence_str,
    }


def append_given_step(
    pyramid_id: str, next_step_item_dict: Dict, user: UserOut
) -> PyramidOut:
    pyramid = get_pyramid_by_id(pyramid_id)  # Pyramid Pydantic modeli
    if pyramid.completed:
        raise ValueError("Bu piramit zaten tamamlanmış, yeni adım eklenemez.")
    if pyramid.last_step >= pyramid.total_steps - 1:
        raise ValueError("Tüm adımlar zaten tamamlanmış. Yeni adım eklenemez.")

    expected_next_step_type = pyramid.step_types[pyramid.last_step + 1]

    # Gelen dict'ten Pydantic PyramidItem (Union) modelini oluştur
    parsed_next_step_item = _parse_step_item_from_dict(
        next_step_item_dict, expected_next_step_type
    )

    # Pydantic model listesini güncelle
    pyramid.steps.append(parsed_next_step_item)
    pyramid.last_step += 1
    pyramid.updated_at = datetime.now(timezone.utc)

    # Veritabanını güncellemek için Pydantic modelini MongoDB'ye uygun dict'e çevir
    pyramid_dict_for_db_update = {
        "steps": [
            step.model_dump(exclude_none=True) for step in pyramid.steps
        ],  # exclude_none önemli
        "last_step": pyramid.last_step,
        "updated_at": pyramid.updated_at,
    }
    pyramid_table.update_one(
        {"_id": ObjectId(pyramid_id)}, {"$set": pyramid_dict_for_db_update}
    )

    return PyramidOut.model_validate(
        pyramid.model_dump()
    )  # Güncellenmiş Pyramid'den PyramidOut oluştur


def delete_pyramid(pyramid_id: str, user_id: str):  # user_id eklendi yetkilendirme için
    # Yetkilendirme: Sadece kendi piramidini silebilmeli
    pyramid_doc = pyramid_table.find_one(
        {"_id": ObjectId(pyramid_id), "user_id": user_id}
    )
    if not pyramid_doc:
        raise ValueError("Piramit bulunamadı veya silme yetkiniz yok.")

    delete_result = pyramid_table.delete_one({"_id": ObjectId(pyramid_id)})
    if delete_result.deleted_count == 0:
        # Bu durum yukarıdaki find_one ile zaten yakalanmış olmalı
        raise ValueError("Piramit bulunamadı veya zaten silinmiş.")

    user_table.update_one(
        {"_id": ObjectId(user_id)}, {"$pull": {"pyramids": pyramid_id}}
    )
    return {"message": "Piramit başarıyla silindi."}


def set_total_steps(user_level: str) -> int:
    level_to_steps = {
        "A1 - Beginner": 8,
        "A2 - Elementary": 9,
        "B1 - Intermediate": 11,
        "B2 - Upper Intermediate": 12,
        "C1 - Advanced": 14,
        "C2 - Proficient": 15,
    }
    return level_to_steps.get(user_level, 11)  # Varsayılan 11


def set_step_types(total_steps: int, level: str) -> List[str]:
    transformation_types = ["expand", "paraphrase", "replace", "shrink"]
    type_ratios: Dict[str, List[float]] = {
        "A1 - Beginner": [0.3, 0.4, 0.2, 0.1],
        "A2 - Elementary": [0.3, 0.3, 0.15, 0.25],
        "B1 - Intermediate": [0.35, 0.2, 0.1, 0.35],
        "B2 - Upper Intermediate": [0.25, 0.3, 0.15, 0.3],
        "C1 - Advanced": [0.2, 0.35, 0.1, 0.35],
        "C2 - Proficient": [0.15, 0.35, 0.1, 0.4],
    }
    ratios = type_ratios.get(level, type_ratios["B1 - Intermediate"])
    step_array: List[str] = []
    for i, transformation_type in enumerate(transformation_types):
        num_steps = round(total_steps * ratios[i])
        step_array.extend([transformation_type] * num_steps)

    current_total_steps = len(step_array)
    if current_total_steps < total_steps:
        for _ in range(total_steps - current_total_steps):
            step_array.append(random.choice(transformation_types))
    elif current_total_steps > total_steps:
        step_array = step_array[:total_steps]

    if (
        not step_array and total_steps > 0
    ):  # Eğer step_array hala boşsa ve total_steps > 0 ise
        step_array = [random.choice(transformation_types) for _ in range(total_steps)]

    random.shuffle(step_array)
    
    # Ensure shrink is never the first step
    if step_array and step_array[0] == "shrink":
        # Find a non-shrink step to swap with
        for i in range(1, len(step_array)):
            if step_array[i] != "shrink":
                # Swap the first position with this non-shrink step
                step_array[0], step_array[i] = step_array[i], step_array[0]
                break
        
        # If all steps are shrink (unlikely but defensive), change the first to expand
        if step_array[0] == "shrink":
            step_array[0] = "expand"
    
    return step_array


def create_next_step_options(pyramid_id: str, user: UserOut) -> PyramidOut:
    """(FALLBACK) Bir sonraki adımı oluşturur. Ana akış /append-step kullanır."""
    pyramid = get_pyramid_by_id(pyramid_id)
    if pyramid.completed:
        raise ValueError("Bu piramit zaten tamamlanmış.")
    if pyramid.last_step >= pyramid.total_steps - 1:
        raise ValueError("Tüm adımlar zaten tamamlanmış.")

    next_step_type = pyramid.step_types[pyramid.last_step + 1]
    current_completed_step = pyramid.steps[pyramid.last_step]

    sentence_for_next_step = current_completed_step.selected_sentence
    if not sentence_for_next_step:  # selected_sentence yoksa (olmamalı ama fallback)
        sentence_for_next_step = current_completed_step.initial_sentence

    step_creator_fn_map = {
        "expand": create_expand_options,
        "paraphrase": create_paraphrase_options,
        "replace": create_replace_options,
        "shrink": create_shrink_options,
    }
    creator_fn = step_creator_fn_map.get(next_step_type)
    if not creator_fn:
        raise ValueError(
            f"Bilinmeyen adım türü: {next_step_type}"
        )  # Collect option words from previous steps to avoid repetition
    excluded_words = _collect_option_words_from_previous_steps(pyramid.steps)

    next_step_item: PyramidItem = creator_fn(
        sentence_for_next_step,
        user.learning_language,
        user.system_language,
        getattr(user, "purpose", "General Knowledge"),
        user.level,  # user.level ve purpose UserOut'tan
        excluded_words,  # Pass excluded words to avoid repetition
    )

    pyramid.steps.append(next_step_item)
    pyramid.last_step += 1
    pyramid.updated_at = datetime.now(timezone.utc)

    pyramid_dict_for_db_update = {
        "steps": [step.model_dump(exclude_none=True) for step in pyramid.steps],
        "last_step": pyramid.last_step,
        "updated_at": pyramid.updated_at,
    }
    pyramid_table.update_one(
        {"_id": ObjectId(pyramid_id)}, {"$set": pyramid_dict_for_db_update}
    )
    return PyramidOut.model_validate(pyramid)


def preview_next_step_options(pyramid_id: str, user: UserOut) -> Dict:
    pyramid = get_pyramid_by_id(pyramid_id)
    if pyramid.completed:
        return {
            "pyramid_id": pyramid_id,
            "next_step_type": None,
            "current_step": pyramid.last_step,
            "preview_steps": [],
            "message": "Bu piramit zaten tamamlanmış.",
        }
    if pyramid.last_step >= pyramid.total_steps - 1:
        return {
            "pyramid_id": pyramid_id,
            "next_step_type": None,
            "current_step": pyramid.last_step,
            "preview_steps": [],
            "message": "Tüm adımlar tamamlanmış.",
        }

    next_step_type_for_preview = pyramid.step_types[pyramid.last_step + 1]
    current_step_item = pyramid.steps[pyramid.last_step]

    sentences_to_base_preview_on: List[str] = []
    if current_step_item.options:
        for option in current_step_item.options:
            sentence_from_option = ""
            if isinstance(option, PyramidParaphOptions):
                sentence_from_option = option.paraphrased_sentence
            elif hasattr(option, "sentence"):  # Diğer tüm Pyramid...Options tipleri
                sentence_from_option = getattr(option, "sentence")

            if sentence_from_option:
                sentences_to_base_preview_on.append(sentence_from_option)
            else:
                print(f"Uyarı: Preview için opsiyondan cümle alınamadı: {option}")

    if (
        not sentences_to_base_preview_on
    ):  # Eğer seçenek yoksa veya seçeneklerden cümle çıkarılamadıysa
        print(
            f"Uyarı: Piramit {pyramid_id}, adım {pyramid.last_step} için önizleme oluşturulacak seçenek bulunamadı. Initial_sentence kullanılacak."
        )
        sentences_to_base_preview_on = [current_step_item.initial_sentence]

    step_creator_fn_map = {
        "expand": create_expand_options,
        "paraphrase": create_paraphrase_options,
        "replace": create_replace_options,
        "shrink": create_shrink_options,
    }
    creator_fn_for_preview = step_creator_fn_map.get(next_step_type_for_preview)
    if not creator_fn_for_preview:
        raise ValueError(
            f"Önizleme için bilinmeyen adım türü: {next_step_type_for_preview}"
        )

    preview_steps_generated: List[Dict] = (
        []
    )  # Dict listesi olarak dönecek (PyramidItem.model_dump())

    def create_preview_for_sentence(sentence_input: str) -> Optional[Dict]:
        """Helper function to create a preview for a single sentence."""
        try:
            # Collect option words from previous steps for preview generation
            excluded_words_for_preview = _collect_option_words_from_previous_steps(
                pyramid.steps
            )

            # creator_fn PyramidItem döndürür
            preview_item_pydantic: PyramidItem = creator_fn_for_preview(
                sentence_input,
                user.learning_language,
                user.system_language,
                getattr(user, "purpose", "General Knowledge"),
                user.level,
                excluded_words_for_preview,  # Pass excluded words to avoid repetition
            )
            if preview_item_pydantic:
                # Frontend'e göndermeden önce Pydantic modelini dict'e çevir
                return preview_item_pydantic.model_dump(exclude_none=True)
        except Exception as e:
            print(
                f"Önizleme adımı oluşturulurken hata (cümle: '{sentence_input}', tip: {next_step_type_for_preview}): {e}"
            )
        return None

    # ThreadPoolExecutor kullanarak AI çağrılarını paralel olarak işle
    with ThreadPoolExecutor(
        max_workers=min(len(sentences_to_base_preview_on), 3)
    ) as executor:
        # Tüm görevleri başlat
        future_to_sentence = {
            executor.submit(create_preview_for_sentence, sentence): sentence
            for sentence in sentences_to_base_preview_on
        }

        # Sonuçları topla
        for future in future_to_sentence:
            result = future.result()
            if result is not None:
                preview_steps_generated.append(result)

    if not preview_steps_generated and sentences_to_base_preview_on:
        print(
            f"Uyarı: Piramit {pyramid_id} için önizleme adımı üretilemedi, ancak girdi cümleleri mevcuttu."
        )

    return {
        "pyramid_id": pyramid_id,
        "next_step_type": next_step_type_for_preview,
        "current_step": pyramid.last_step,
        "preview_steps": preview_steps_generated,
    }


# --- AI İstemcisi Sarmalayıcıları ---
# Bunlar src.api_clients.pyramid_prompts'taki AI fonksiyonlarını çağırır
# ve beklenen Pydantic PyramidItem alt tiplerini döndürür.


def create_expand_options(
    sentence: str,
    learning_language: str,
    system_language: str,
    purpose: str,
    user_level: str,
    excluded_words: List[str] = None,
) -> PyramidExpandItem:
    if excluded_words is None:
        excluded_words = []

    ai_result_dict = ai_expand_sentence(
        sentence,
        learning_language,
        system_language,
        purpose,
        user_level,
        excluded_words,
    )
    if not ai_result_dict:  # AI'dan None dönerse
        print(
            f"Uyarı: ai_expand_sentence None döndürdü ('{sentence}'). Varsayılan boş item oluşturuluyor."
        )
        # initial_sentence ve initial_sentence_meaning AI'dan gelmeli,
        # eğer gelmiyorsa, AI prompt'ları güncellenmeli.
        # Şimdilik, gelen cümleyi initial_sentence olarak kullanıyoruz.
        return PyramidExpandItem(
            initial_sentence=sentence,
            initial_sentence_meaning="Anlam alınamadı",
            options=[],
        )

    # Extract expand words for option_words field
    expand_item = PyramidExpandItem.model_validate(ai_result_dict)
    option_words = [
        option.expand_word for option in expand_item.options if option.expand_word
    ]
    expand_item.option_words = option_words

    return expand_item


def create_paraphrase_options(
    sentence: str,
    learning_language: str,
    system_language: str,
    purpose: str,
    user_level: str,
    excluded_words: List[str] = None,
) -> PyramidParaphItem:
    if excluded_words is None:
        excluded_words = []

    ai_result_dict = ai_paraphrase_sentence(
        sentence,
        learning_language,
        system_language,
        purpose,
        user_level,
        excluded_words,
    )
    if not ai_result_dict:
        print(
            f"Uyarı: ai_paraphrase_sentence None döndürdü ('{sentence}'). Varsayılan boş item oluşturuluyor."
        )
        return PyramidParaphItem(
            initial_sentence=sentence,
            initial_sentence_meaning="Anlam alınamadı",
            options=[],
        )

    # Extract paraphrased sentences for option_words field
    paraphrase_item = PyramidParaphItem.model_validate(ai_result_dict)
    option_words = [
        option.paraphrased_sentence
        for option in paraphrase_item.options
        if option.paraphrased_sentence
    ]
    paraphrase_item.option_words = option_words

    return paraphrase_item


def create_replace_options(
    sentence: str,
    learning_language: str,
    system_language: str,
    purpose: str,
    user_level: str,
    excluded_words: List[str] = None,
) -> PyramidReplaceItem:
    if excluded_words is None:
        excluded_words = []

    ai_result_dict = ai_replace_word(
        sentence,
        learning_language,
        system_language,
        user_level,
        purpose,
        excluded_words,
    )
    if not ai_result_dict:
        print(
            f"Uyarı: ai_replace_word None döndürdü ('{sentence}'). Varsayılan boş item oluşturuluyor."
        )
        return PyramidReplaceItem(
            initial_sentence=sentence,
            initial_sentence_meaning="Anlam alınamadı",
            options=[],
        )

    # Extract both replaced and changed words for option_words field
    replace_item = PyramidReplaceItem.model_validate(ai_result_dict)
    option_words = []
    for option in replace_item.options:
        if option.replaced_word:
            option_words.append(option.replaced_word)
        if option.changed_word:
            option_words.append(option.changed_word)
    replace_item.option_words = option_words

    return replace_item


def create_shrink_options(
    sentence: str,
    learning_language: str,
    system_language: str,
    purpose: str,
    user_level: str,
    excluded_words: List[str] = None,
) -> PyramidShrinkItem:
    if excluded_words is None:
        excluded_words = []

    ai_result_dict = ai_shrink_sentence(
        sentence,
        learning_language,
        system_language,
        purpose,
        user_level,
        excluded_words,
    )
    if not ai_result_dict:
        print(
            f"Uyarı: ai_shrink_sentence None döndürdü ('{sentence}'). Varsayılan boş item oluşturuluyor."
        )
        return PyramidShrinkItem(
            initial_sentence=sentence,
            initial_sentence_meaning="Anlam alınamadı",
            options=[],
        )

    # Extract removed words for option_words field
    shrink_item = PyramidShrinkItem.model_validate(ai_result_dict)
    option_words = [
        option.removed_word for option in shrink_item.options if option.removed_word
    ]
    shrink_item.option_words = option_words

    return shrink_item


async def complete_pyramid_with_xp(
    pyramid_id: str, user_id: str, event_id: str = None
) -> Dict:
    """
    Complete a pyramid exercise and award XP to the user using the new event system.

    Args:
        pyramid_id: ID of the pyramid to complete
        user_id: ID of the user completing the pyramid
        event_id: Optional event ID for tracking (if None, will try to find existing event)

    Returns:
        Dictionary with completion status and XP earned
    """
    try:
        # Mark pyramid as completed in pyramid_table
        pyramid_table.update_one(
            {"_id": ObjectId(pyramid_id)},
            {"$set": {"completed": True, "updated_at": datetime.utcnow()}},
        )

        # Get the pyramid to extract step information
        pyramid_doc = pyramid_table.find_one({"_id": ObjectId(pyramid_id)})
        if not pyramid_doc:
            raise ValueError("Pyramid not found")

        # Handle event tracking
        if event_id:
            # Complete existing event
            completed_event = await complete_pyramid_event(event_id)
            total_xp = completed_event.get("details", {}).get("xp_earned", 0) if completed_event else 0
        else:
            # Try to find existing pyramid event
            existing_event = get_pyramid_event_by_id(user_id, pyramid_id)
            if existing_event:
                # Complete the existing event
                completed_event = await complete_pyramid_event(existing_event["_id"])
                total_xp = completed_event.get("details", {}).get("xp_earned", 0) if completed_event else 0
            else:
                # Create a new event and immediately complete it with pyramid data
                items = pyramid_doc.get("items", [])
                step_types = pyramid_doc.get("step_types", [])
                
                new_event = create_pyramid_event(user_id, pyramid_id)
                if new_event:
                    # Update the event with pyramid completion data
                    update_pyramid_event(
                        new_event["_id"],
                        {
                            "total_steps": len(items),
                            "completed_steps": len(items),
                            "step_types": step_types,
                            "steps_detail": items,
                        }
                    )
                    # Complete the event
                    completed_event = await complete_pyramid_event(new_event["_id"])
                    total_xp = completed_event.get("details", {}).get("xp_earned", 0) if completed_event else 0
                else:
                    # Fallback to old XP calculation if event creation fails
                    base_xp = 25
                    bonus_xp = len(items) * 5
                    total_xp = base_xp + bonus_xp
                    
                    # Award XP manually
                    current_user_data = await get_xp(user_id)
                    if current_user_data:
                        current_xp = current_user_data.get("xp", 0)
                        await update_xp(user_id, current_xp + total_xp)

        return {
            "status": "success", 
            "xp_earned": total_xp, 
            "pyramid_completed": True,
            "event_id": event_id
        }

    except Exception as e:
        print(f"Error completing pyramid with XP: {e}")
        return {"status": "error", "xp_earned": 0, "error": str(e)}


# Test fonksiyonları (eğer hala bu dosyada tutuluyorsa)
# ... (test_create_expand_options vb.) ...
