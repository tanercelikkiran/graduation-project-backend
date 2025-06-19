from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from src.database.database import saved_sentence_table
from src.models.saved_sentence import SavedSentence, SaveSentenceRequest


def save_sentence(user_id: str, save_data: SaveSentenceRequest) -> Dict[str, Any]:
    """
    Save a sentence to the saved_sentence_table
    """
    try:
        # Check if the sentence is already saved
        existing_sentence = saved_sentence_table.find_one({
            "user_id": user_id,
            "sentence": save_data.sentence,
            "meaning": save_data.meaning
        })
        
        if existing_sentence:
            return {
                "status": "error",
                "message": "Sentence is already saved",
                "isSaved": True
            }
        
        # Create the saved sentence object
        saved_sentence = SavedSentence(
            user_id=user_id,
            sentence=save_data.sentence,
            meaning=save_data.meaning,
            transformation_type=save_data.transformation_type,
            source_sentence=save_data.source_sentence,
            pyramid_id=save_data.pyramid_id,
            step_number=save_data.step_number,
            saved_at=datetime.utcnow()
        )
        
        # Insert into saved_sentence_table
        result = saved_sentence_table.insert_one(saved_sentence.dict())
        
        if result.inserted_id:
            return {
                "status": "success",
                "message": "Sentence saved successfully",
                "isSaved": True
            }
        else:
            return {
                "status": "error",
                "message": "Failed to save sentence",
                "isSaved": False
            }
            
    except Exception as e:
        print(f"Error saving sentence: {e}")
        return {
            "status": "error",
            "message": "An error occurred while saving the sentence",
            "isSaved": False
        }


def unsave_sentence(user_id: str, sentence: str, meaning: str) -> Dict[str, Any]:
    """
    Remove a saved sentence from the saved_sentence_table
    """
    try:
        result = saved_sentence_table.delete_one({
            "user_id": user_id,
            "sentence": sentence,
            "meaning": meaning
        })
        
        if result.deleted_count > 0:
            return {
                "status": "success",
                "message": "Sentence removed from saved list",
                "isSaved": False
            }
        else:
            return {
                "status": "error",
                "message": "Sentence not found in saved list",
                "isSaved": False
            }
            
    except Exception as e:
        print(f"Error removing saved sentence: {e}")
        return {
            "status": "error",
            "message": "An error occurred while removing the sentence",
            "isSaved": False
        }


def get_saved_sentences(user_id: str) -> Dict[str, Any]:
    """
    Get all saved sentences for a user from saved_sentence_table
    """
    try:
        # Get all saved sentences for the user, sorted by saved_at (most recent first)
        saved_sentences_cursor = saved_sentence_table.find(
            {"user_id": user_id}
        ).sort("saved_at", -1)
        
        saved_sentences = list(saved_sentences_cursor)
        
        # Convert ObjectId to string for JSON serialization
        for sentence in saved_sentences:
            if "_id" in sentence:
                sentence["_id"] = str(sentence["_id"])
        
        return {
            "status": "success",
            "saved_sentences": saved_sentences
        }
        
    except Exception as e:
        print(f"Error fetching saved sentences: {e}")
        return {
            "status": "error",
            "message": "An error occurred while fetching saved sentences",
            "saved_sentences": []
        }


def is_sentence_saved(user_id: str, sentence: str, meaning: str) -> Dict[str, Any]:
    """
    Check if a sentence is saved by the user in saved_sentence_table
    """
    try:
        saved_sentence = saved_sentence_table.find_one({
            "user_id": user_id,
            "sentence": sentence,
            "meaning": meaning
        })
        
        is_saved = saved_sentence is not None
        
        return {
            "status": "success",
            "isSaved": is_saved,
            "message": "Sentence is saved" if is_saved else "Sentence is not saved"
        }
        
    except Exception as e:
        print(f"Error checking if sentence is saved: {e}")
        return {
            "status": "error",
            "message": "An error occurred while checking sentence status",
            "isSaved": False
        }


def get_saved_sentences_count(user_id: str) -> int:
    """
    Get the count of saved sentences for a user from saved_sentence_table
    """
    try:
        count = saved_sentence_table.count_documents({"user_id": user_id})
        return count
        
    except Exception as e:
        print(f"Error getting saved sentences count: {e}")
        return 0