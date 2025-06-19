from src.api_clients.vocabulary_prompts import create_vocabulary_list
from src.database.database import (
    user_table,
    vocabulary_table,
    vocabulary_statistics_table,
)
from src.models.vocabulary import (
    VocabularyList,
    HintUsageRequest,
    AttemptResult,
    VocabularyStatistics,
    VocabularyItem,
    SaveVocabularyRequest,
)
from bson import ObjectId
from datetime import datetime, timedelta
import random
import json
import os


def create_vocabulary(user_id: str, system_language: str = None):
    user = user_table.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise ValueError("User not found")

    purpose = user.get("purpose")
    # Add a default purpose if one isn't set in the user profile
    if not purpose:
        purpose = "general vocabulary"

    level = user.get("level")
    # Add a default level if one isn't set
    if not level:
        level = "intermediate"

    learning_language = user.get("learning_language")
    # Add a default language if one isn't set
    if not learning_language:
        learning_language = "English"

    # Get difficult words for this user by retrieving word statistics
    # and selecting words with high difficulty scores
    difficult_words = get_difficult_words(user_id)

    # Get recently seen words to avoid repeating them
    recently_seen_words = get_recently_seen_words(user_id, days=30)

    # Generate vocabulary list with prioritized difficult words
    vocab_list = create_vocabulary_with_difficult_words(
        purpose,
        level,
        learning_language,
        difficult_words,
        recently_seen_words,
        system_language,
    )

    vocab_data = vocab_list.model_dump()
    result = vocabulary_table.insert_one(vocab_data)

    vocab_id = result.inserted_id
    vocab_data["_id"] = str(vocab_id)

    user_table.update_one(
        {"_id": ObjectId(user_id)}, {"$push": {"vocabulary_lists": vocab_id}}
    )

    # Update last_seen for all words in this vocabulary list
    update_word_last_seen(user_id, vocab_list, system_language)

    # Shuffle the vocabulary words before returning to frontend
    if vocab_data.get("words"):
        random.shuffle(vocab_data["words"])

    return vocab_data


def create_vocabulary_with_difficult_words(
    purpose,
    level,
    learning_language,
    difficult_words,
    recently_seen_words,
    system_language=None,
):
    """
    Create a vocabulary list combining difficult words and new words

    Args:
        purpose: The user's learning purpose
        level: The user's proficiency level
        learning_language: The language being learned
        difficult_words: List of words the user has had difficulty with
        recently_seen_words: List of words the user has recently seen
        system_language: The user's system language

    Returns:
        VocabularyList object with a mix of difficult and new words
    """
    # Convert recently seen words to format expected by vocabulary generator
    excluded_words = recently_seen_words

    # Generate a fresh vocabulary list with excluded words
    vocabulary_list = create_vocabulary_list(
        purpose,
        level,
        learning_language,
        system_language,
        excluded_words=excluded_words,
    )

    # If we don't have any difficult words, just return the regular vocab list
    if not difficult_words or len(difficult_words) == 0:
        return vocabulary_list

    # We want difficult words to be 30-40% of the vocabulary list
    # Get a random percentage between 30-40%
    difficult_percentage = random.uniform(0.3, 0.4)

    # Calculate how many difficult words to include
    total_words = len(vocabulary_list.words)
    difficult_word_count = min(
        int(total_words * difficult_percentage), len(difficult_words)
    )

    # Select the highest scoring difficult words
    selected_difficult_words = difficult_words[:difficult_word_count]

    # Convert difficult words to VocabularyItem format
    difficult_vocab_items = []
    for word_stat in selected_difficult_words:
        # Only check for exact duplicates
        existing_word = next(
            (
                w
                for w in vocabulary_list.words
                if w.word.lower() == word_stat["word"].lower()
                and w.meaning.lower() == word_stat["meaning"].lower()
            ),
            None,
        )

        # Skip only if exact duplicate is found
        if existing_word:
            continue

        # Check if the stored system_language matches the current system_language
        # If they don't match, we should skip this word to avoid language mismatches
        word_system_language = word_stat.get("system_language", "English")
        if system_language and word_system_language != system_language:
            continue

        # Create a proper VocabularyItem object with all required fields
        difficult_vocab_items.append(
            VocabularyItem(
                word=word_stat["word"],
                meaning=word_stat["meaning"],
                relevantWords=word_stat.get(
                    "relevantWords",
                    ["related1", "related2", "related3", "related4", "related5"],
                ),
                emoji=word_stat.get("emoji", "📚"),  # Default emoji if none provided
            )
        )

    # If we have difficult words to add, replace some of the generated words
    if difficult_vocab_items:
        # Remove words from the end to make room for difficult words
        remaining_words = vocabulary_list.words[
            : total_words - len(difficult_vocab_items)
        ]

        # Add difficult words to the list and shuffle to mix difficult and new words
        all_words = difficult_vocab_items + remaining_words
        random.shuffle(all_words)

        # Update the vocabulary list
        vocabulary_list.words = all_words

    return vocabulary_list


def update_word_last_seen(
    user_id: str, vocab_list: VocabularyList, system_language: str = None
):
    """
    Update the last_seen timestamp for all words in a vocabulary list
    """
    current_time = datetime.utcnow()

    # Ensure system_language is set to a valid value
    if system_language is None:
        system_language = "English"  # Fallback to English if not provided

    for word_item in vocab_list.words:
        # Try to find existing word statistics
        word_stat = vocabulary_statistics_table.find_one(
            {"user_id": user_id, "word": word_item.word, "meaning": word_item.meaning}
        )

        if word_stat:
            # Update last_seen time and ensure system_language is set
            vocabulary_statistics_table.update_one(
                {
                    "user_id": user_id,
                    "word": word_item.word,
                    "meaning": word_item.meaning,
                },
                {
                    "$set": {
                        "last_seen": current_time,
                        "system_language": system_language,  # Ensure system_language is updated
                        "relevantWords": word_item.relevantWords,  # Store relevant words
                        "emoji": word_item.emoji,  # Store emoji
                    }
                },
            )
        else:
            # Create a new entry if this is the first time seeing this word
            new_vocabulary_stat = VocabularyStatistics(
                user_id=user_id,
                word=word_item.word,
                meaning=word_item.meaning,
                system_language=system_language,  # Store the system language
                relevantWords=word_item.relevantWords,  # Store relevant words
                emoji=word_item.emoji,  # Store emoji
                first_seen=current_time,
                last_seen=current_time,
            )

            vocabulary_statistics_table.insert_one(new_vocabulary_stat.model_dump())


def track_hint_usage(user_id: str, hint_data: HintUsageRequest):
    """
    Track when a user uses a hint on a word
    """
    current_time = datetime.utcnow()

    # Find existing word statistics
    word_stat = vocabulary_statistics_table.find_one(
        {"user_id": user_id, "word": hint_data.word, "meaning": hint_data.meaning}
    )

    # Ensure system_language has a value
    system_language = hint_data.system_language
    if system_language is None:
        system_language = "English"  # Fallback to English if not provided

    update_data = {
        "last_attempt": current_time,
        "system_language": system_language,  # Always update system_language
    }

    # Add the appropriate hint counter
    if hint_data.hint_type == "letter":
        hint_field = "letter_hints"
    elif hint_data.hint_type == "relevant_word":
        hint_field = "relevant_word_hints"
    elif hint_data.hint_type == "emoji":
        hint_field = "emoji_hints"
    else:
        raise ValueError(f"Invalid hint type: {hint_data.hint_type}")

    if word_stat:
        # Increment the appropriate hint counter
        vocabulary_statistics_table.update_one(
            {"user_id": user_id, "word": hint_data.word, "meaning": hint_data.meaning},
            {"$inc": {hint_field: 1}, "$set": update_data},
        )
    else:
        # Create a new entry for this word
        new_word_stat = VocabularyStatistics(
            user_id=user_id,
            word=hint_data.word,
            meaning=hint_data.meaning,
            system_language=system_language,
            first_seen=current_time,
            last_seen=current_time,
            last_attempt=current_time,
            # Add empty but proper relevant words array and default emoji
            relevantWords=["related1", "related2", "related3", "related4", "related5"],
            emoji="📚",
        )

        # Set the appropriate hint value
        setattr(new_word_stat, hint_field, 1)

        vocabulary_statistics_table.insert_one(new_word_stat.model_dump())

    return {"status": "success", "message": "Hint usage tracked successfully"}


def track_attempt_result(user_id: str, attempt_data: AttemptResult):
    """
    Track when a user attempts to answer a word
    """
    current_time = datetime.utcnow()

    # Find existing word statistics
    word_stat = vocabulary_statistics_table.find_one(
        {"user_id": user_id, "word": attempt_data.word, "meaning": attempt_data.meaning}
    )

    # Ensure system_language has a value
    system_language = attempt_data.system_language
    if system_language is None:
        system_language = "English"  # Fallback to English if not provided

    # Determine which counter to increment
    success_field = "successful_attempts" if attempt_data.success else "failed_attempts"

    update_data = {
        "last_attempt": current_time,
        "system_language": system_language,  # Always update system_language
    }

    if word_stat:
        # Increment the appropriate counter
        vocabulary_statistics_table.update_one(
            {
                "user_id": user_id,
                "word": attempt_data.word,
                "meaning": attempt_data.meaning,
            },
            {"$inc": {success_field: 1}, "$set": update_data},
        )
    else:
        # Create a new entry for this word
        new_word_stat = VocabularyStatistics(
            user_id=user_id,
            word=attempt_data.word,
            meaning=attempt_data.meaning,
            system_language=system_language,
            first_seen=current_time,
            last_seen=current_time,
            last_attempt=current_time,
            # Add empty but proper relevant words array and default emoji
            relevantWords=["related1", "related2", "related3", "related4", "related5"],
            emoji="📚",
        )

        # Set the appropriate attempt value
        setattr(new_word_stat, success_field, 1)

        vocabulary_statistics_table.insert_one(new_word_stat.model_dump())

    return {"status": "success", "message": "Attempt result tracked successfully"}


def get_difficult_words(user_id: str, limit: int = 20, recency_days: int = 30):
    """
    Get a list of difficult words for a user based on word statistics

    Args:
        user_id: The user ID
        limit: Maximum number of difficult words to return
        recency_days: Only consider words seen in the last N days

    Returns:
        List of word statistics objects with difficulty scores
    """
    # Find all word statistics for this user
    word_stats = list(vocabulary_statistics_table.find({"user_id": user_id}))

    # If no stats found, return empty list
    if not word_stats:
        return []

    # Calculate difficulty score for each word
    scored_words = []
    for word_stat in word_stats:
        # Create WordStatistics object to calculate score
        stat_obj = VocabularyStatistics(**word_stat)
        difficulty_score = stat_obj.calculate_difficulty_score()

        # Add score to the word stat dictionary
        word_stat["difficulty_score"] = difficulty_score
        scored_words.append(word_stat)

    # Sort by difficulty score (highest first)
    sorted_words = sorted(
        scored_words, key=lambda w: w.get("difficulty_score", 0), reverse=True
    )

    # Limit to the requested number of words
    return sorted_words[:limit]


def get_recently_seen_words(user_id: str, days: int = 30):
    """
    Get a list of words recently seen by the user

    Args:
        user_id: The user ID
        days: Number of days to look back

    Returns:
        List of word statistics objects
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    recently_seen = list(
        vocabulary_statistics_table.find(
            {"user_id": user_id, "last_seen": {"$gte": cutoff_date}}
        )
    )
    return recently_seen


def get_word_statistics(user_id: str):
    """
    Get word statistics for a user
    """
    word_stats = list(vocabulary_statistics_table.find({"user_id": user_id}))

    # Convert MongoDB ObjectId to string
    for stat in word_stats:
        if "_id" in stat:
            stat["_id"] = str(stat["_id"])

        # Convert datetime objects to ISO format strings
        for time_field in ["first_seen", "last_seen", "last_attempt"]:
            if time_field in stat and isinstance(stat[time_field], datetime):
                stat[time_field] = stat[time_field].isoformat()

    return {"word_statistics": word_stats}


def return_test_data(user_id: str):
    user_data = user_table.find_one({"_id": ObjectId(user_id)})

    if not user_data:
        raise ValueError("User not found")

    # Check if the user has any vocabulary lists
    if "vocabulary_lists" in user_data and user_data["vocabulary_lists"]:
        vocab_list = vocabulary_table.find_one(
            {"_id": {"$in": user_data["vocabulary_lists"]}}
        )

        if vocab_list:
            # Found a vocabulary list, return it
            result = dict(vocab_list)
            result["_id"] = str(result["_id"])
            # Shuffle the vocabulary words before returning to frontend
            if result.get("words"):
                random.shuffle(result["words"])
            return result

    # If no vocabulary list found, create one
    # Pass the system_language if available, otherwise default in create_vocabulary
    system_language = user_data.get("system_language")
    vocab_data = create_vocabulary(user_id, system_language)
    return vocab_data


def save_vocabulary(user_id: str, save_data: SaveVocabularyRequest):
    """
    Save a vocabulary word to the user's saved_vocabularies list

    Args:
        user_id: The user ID
        save_data: The vocabulary word to save

    Returns:
        Dictionary with status and message
    """
    if not ObjectId.is_valid(user_id):
        raise ValueError("Invalid user ID")

    # Find the user
    user = user_table.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise ValueError("User not found")

    # Create saved vocabulary entry
    saved_vocab = {
        "word": save_data.word,
        "meaning": save_data.meaning,
        "relevantWords": save_data.relevantWords,
        "emoji": save_data.emoji,
        "saved_at": datetime.utcnow(),
    }

    # Check if this word is already saved
    existing_saved = next(
        (
            item
            for item in user.get("saved_vocabularies", [])
            if item.get("word") == save_data.word
            and item.get("meaning") == save_data.meaning
        ),
        None,
    )

    if existing_saved:
        return {"status": "info", "message": "This vocabulary word is already saved"}

    # Add to user's saved vocabularies
    user_table.update_one(
        {"_id": ObjectId(user_id)}, {"$push": {"saved_vocabularies": saved_vocab}}
    )

    return {"status": "success", "message": "Vocabulary word saved successfully"}


def unsave_vocabulary(user_id: str, word: str, meaning: str):
    """
    Remove a saved vocabulary word from the user's saved_vocabularies list

    Args:
        user_id: The user ID
        word: The word to unsave
        meaning: The meaning of the word

    Returns:
        Dictionary with status and message
    """
    if not ObjectId.is_valid(user_id):
        raise ValueError("Invalid user ID")

    # Find the user
    user = user_table.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise ValueError("User not found")

    # Remove the saved vocabulary
    result = user_table.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"saved_vocabularies": {"word": word, "meaning": meaning}}},
    )

    if result.modified_count == 0:
        return {
            "status": "info",
            "message": "Vocabulary word was not found in saved list",
        }

    return {"status": "success", "message": "Vocabulary word removed from saved list"}


def get_saved_vocabularies(user_id: str):
    """
    Get all saved vocabularies for a user

    Args:
        user_id: The user ID

    Returns:
        List of saved vocabulary words
    """
    if not ObjectId.is_valid(user_id):
        raise ValueError("Invalid user ID")

    # Find the user
    user = user_table.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise ValueError("User not found")

    # Return saved vocabularies, or empty list if none exists
    saved_vocabularies = user.get("saved_vocabularies", [])

    return {"saved_vocabularies": saved_vocabularies}


def is_vocabulary_saved(user_id: str, word: str, meaning: str):
    """
    Check if a vocabulary word is saved by the user

    Args:
        user_id: The user ID
        word: The word to check
        meaning: The meaning of the word

    Returns:
        Dictionary indicating if the word is saved
    """
    if not ObjectId.is_valid(user_id):
        raise ValueError("Invalid user ID")

    # Find the user
    user = user_table.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise ValueError("User not found")

    # Check if the word is in saved vocabularies
    saved_vocabularies = user.get("saved_vocabularies", [])
    is_saved = any(
        item.get("word") == word and item.get("meaning") == meaning
        for item in saved_vocabularies
    )

    return {"isBookmarked": is_saved}


def get_user_vocabulary_lists(user_id: str):
    """
    Get all vocabulary lists created by a user

    Args:
        user_id: The user ID

    Returns:
        List of vocabulary lists with titles and metadata
    """
    if not ObjectId.is_valid(user_id):
        raise ValueError("Invalid user ID")

    # Find the user
    user = user_table.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise ValueError("User not found")

    # Get the vocabulary list IDs for this user
    vocab_list_ids = user.get("vocabulary_lists", [])

    # Fetch all vocabulary lists
    vocabulary_lists = []

    for vocab_id in vocab_list_ids:
        # Fetch the vocabulary list from the database
        vocab_list = vocabulary_table.find_one({"_id": vocab_id})
        if vocab_list:
            # Extract basic metadata for display
            vocab_data = {
                "id": str(vocab_id),
                "title": f"Vocabulary List {len(vocabulary_lists) + 1}",  # Default title
                "word_count": len(vocab_list.get("words", [])),
                "created_at": vocab_id.generation_time.isoformat(),
            }
            vocabulary_lists.append(vocab_data)

    return {"vocabulary_lists": vocabulary_lists}


def rework_vocabulary_list(vocabulary_list_id: str, user_id: str):
    """
    Rework (shuffle) a vocabulary list and return the shuffled words

    Args:
        vocabulary_list_id: ID of the vocabulary list to rework
        user_id: The user ID (for validation)

    Returns:
        The vocabulary list with words in a random order
    """
    if not ObjectId.is_valid(user_id):
        raise ValueError("Invalid user ID format")

    # Find the user to get their language preferences
    user = user_table.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise ValueError("User not found")

    # Try to find as a user-owned vocabulary list first
    if ObjectId.is_valid(vocabulary_list_id):
        # Check if this vocabulary list belongs to the user
        if ObjectId(vocabulary_list_id) in user.get("vocabulary_lists", []):
            # Get the vocabulary list from database
            vocab_list = vocabulary_table.find_one({"_id": ObjectId(vocabulary_list_id)})
            if vocab_list:
                # Shuffle the words in the vocabulary list
                words = vocab_list.get("words", [])
                random.shuffle(words)

                # Update the vocabulary list with shuffled words
                vocabulary_table.update_one(
                    {"_id": ObjectId(vocabulary_list_id)}, {"$set": {"words": words}}
                )

                # Return the updated vocabulary list
                updated_vocab = vocabulary_table.find_one({"_id": ObjectId(vocabulary_list_id)})

                # Convert ObjectId to string
                if updated_vocab and "_id" in updated_vocab:
                    updated_vocab["_id"] = str(updated_vocab["_id"])

                return {
                    "status": "success",
                    "message": "Vocabulary list reworked successfully",
                    "vocabulary_list": updated_vocab,
                }

    # If not found as user list, try to find as a popular list
    try:
        # Get user's language preferences for popular list lookup
        user_learning_language = user.get("learning_language", "English")
        user_system_language = user.get("system_language", "English")
        
        # Get the path to the writing-lists directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        writing_lists_dir = os.path.join(current_dir, "..", "writing-lists")
        
        # Try to find the popular list by ID (filename without .json)
        filename = f"{vocabulary_list_id}.json"
        file_path = os.path.join(writing_lists_dir, filename)
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                vocab_data = json.load(file)
                
                # Check if the languages match user's preferences
                file_learning_language = vocab_data.get("learning-language", "")
                file_system_language = vocab_data.get("system-language", "")
                
                if (file_learning_language == user_learning_language and 
                    file_system_language == user_system_language):
                    
                    # Get words and shuffle them
                    words = vocab_data.get("words", [])
                    if words:
                        random.shuffle(words)
                    
                    # Return the shuffled popular list data
                    return {
                        "status": "success",
                        "message": "Popular vocabulary list reworked successfully",
                        "vocabulary_list": {
                            "_id": vocabulary_list_id,
                            "title": vocab_data.get("title", "Popular Vocabulary List"),
                            "learning_language": file_learning_language,
                            "system_language": file_system_language,
                            "words": words,
                            "word_count": len(words),
                            "source": "popular"
                        },
                    }
                else:
                    raise ValueError("Popular list language mismatch with user preferences")
        
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading popular vocabulary file: {e}")
    
    raise ValueError("Vocabulary list not found or not accessible by this user")


def delete_vocabulary_list(vocabulary_list_id: str, user_id: str):
    """
    Delete a vocabulary list from the database and remove it from the user's list

    Args:
        vocabulary_list_id: ID of the vocabulary list to delete
        user_id: The user ID (for validation)

    Returns:
        Dictionary indicating success or failure
    """
    if not ObjectId.is_valid(vocabulary_list_id) or not ObjectId.is_valid(user_id):
        raise ValueError("Invalid ID format")

    # Find the user to verify they own this vocabulary list
    user = user_table.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise ValueError("User not found")

    # Check if this vocabulary list belongs to the user
    if ObjectId(vocabulary_list_id) not in user.get("vocabulary_lists", []):
        raise ValueError("Vocabulary list not found or not owned by this user")

    # Get the vocabulary list
    vocab_list = vocabulary_table.find_one({"_id": ObjectId(vocabulary_list_id)})
    if not vocab_list:
        raise ValueError("Vocabulary list not found")

    # Delete the vocabulary list from the vocabulary collection
    vocabulary_table.delete_one({"_id": ObjectId(vocabulary_list_id)})

    # Remove the vocabulary list ID from the user's vocabulary_lists array
    user_table.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"vocabulary_lists": ObjectId(vocabulary_list_id)}},
    )

    return {"status": "success", "message": "Vocabulary list deleted successfully"}


def get_popular_vocabularies(user_id: str):
    """
    Get popular vocabulary lists based on user's learning and system languages
    
    Args:
        user_id: The user ID
        
    Returns:
        List of popular vocabulary lists matching the user's languages
    """
    if not ObjectId.is_valid(user_id):
        raise ValueError("Invalid user ID")
    
    # Find the user to get their language preferences
    user = user_table.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise ValueError("User not found")
    
    # Get user's language preferences
    user_learning_language = user.get("learning_language", "English")
    user_system_language = user.get("system_language", "English")
    
    # Get the path to the writing-lists directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    writing_lists_dir = os.path.join(current_dir, "..", "writing-lists")
    
    popular_lists = []
    
    # Read all JSON files in the writing-lists directory
    try:
        for filename in os.listdir(writing_lists_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(writing_lists_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as file:
                    vocab_data = json.load(file)
                    
                    # Check if the languages match
                    file_learning_language = vocab_data.get("learning-language", "")
                    file_system_language = vocab_data.get("system-language", "")
                    
                    if (file_learning_language == user_learning_language and 
                        file_system_language == user_system_language):
                        
                        # Get words and shuffle them before returning to frontend
                        words = vocab_data.get("words", [])
                        if words:
                            random.shuffle(words)
                        
                        # Add metadata and format for frontend
                        popular_list = {
                            "id": filename.replace('.json', ''),
                            "title": vocab_data.get("title", "Popular Vocabulary List"),
                            "learning_language": file_learning_language,
                            "system_language": file_system_language,
                            "words": words,
                            "word_count": len(words),
                            "source": "popular"
                        }
                        popular_lists.append(popular_list)
                        
    except (OSError, json.JSONDecodeError) as e:
        # Log error but don't fail completely
        print(f"Error reading popular vocabulary files: {e}")
    
    return {"popular_vocabularies": popular_lists}
