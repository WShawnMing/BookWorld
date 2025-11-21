import sys
sys.path.append("../")
from bw_utils import *
from extract_utils import *
import os
import csv
import json
from datetime import datetime

config = load_json_file("./extract_config4.json")

def load_progress(book_source):
    """Load processing progress"""
    progress_file = f"./data/.progress_{book_source}.json"
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading progress file: {e}")
    return {
        "last_chapter_idx": -1,
        "last_chunk_idx": -1,
        "completed": False
    }

def save_progress(book_source, chapter_idx, chunk_idx, completed=False):
    """Save processing progress"""
    progress_file = f"./data/.progress_{book_source}.json"
    ensure_dir("./data/")
    progress = {
        "last_chapter_idx": chapter_idx,
        "last_chunk_idx": chunk_idx,
        "completed": completed,
        "timestamp": str(datetime.now())
    }
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def load_existing_character_info(book_source):
    """Load existing character info from files"""
    characters_info = {}
    role_dir = f"./data/roles/{book_source}"
    if os.path.exists(role_dir):
        for role_folder in os.listdir(role_dir):
            role_path = os.path.join(role_dir, role_folder, "role_info.json")
            if os.path.exists(role_path):
                try:
                    with open(role_path, 'r', encoding='utf-8') as f:
                        role_info = json.load(f)
                        characters_info[role_info["role_name"]] = role_info
                except Exception as e:
                    print(f"Error loading role info from {role_path}: {e}")
    if characters_info:
        print(f"Loaded existing info for {len(characters_info)} characters")
    return characters_info

def load_existing_location_info(book_source):
    """Load existing location info from file"""
    location_file = f"./data/locations/{book_source}.json"
    if os.path.exists(location_file):
        try:
            with open(location_file, 'r', encoding='utf-8') as f:
                locations_info = json.load(f)
                print(f"Loaded existing info for {len(locations_info)} locations")
                return locations_info
        except Exception as e:
            print(f"Error loading location info from {location_file}: {e}")
    return {}



def get_default_character_info(role_name,language,other_role_names):
    default_character_info = {
    "role_name": role_name,
    "role_code": convert_name_to_code(role_name,language),
    "source": book_source,
    "profile": "",
    "activity":1,
    "nickname": role_name,
    "relation": {convert_name_to_code(role_name,language):{
        "relation":[], 
        "detail":"" } for role_name in other_role_names}
    }
    return default_character_info

def get_defaule_location_info(location_name,language):
    default_location_info = {
        "location_name": location_name,
        "location_code": convert_name_to_code(location_name,language),
        "description": "",
        "detail": "",
    }
    return default_location_info

def process_character_chunk(chunk, character_name, language):
    if language == 'zh':
        prompt = f"""分析以下文本并提取关于{character_name}的信息。
    关注其性格、外貌、身材、背景和关键特征，贴合原文。
    如果文本中不包含关于{character_name}的相关信息，请回复 'NO_INFO'。
    
    文本：
    {chunk}
    
    提供角色简介的简明摘要。"""
    else:
        prompt = f"""Analyze the following text and extract information about {character_name}. 
        Focus on their personality, background, and key characteristics.
        If the text doesn't contain relevant information about {character_name}, respond with 'NO_INFO'.
        
        Text:
        {chunk}
        
        Provide a concise summary of the character's profile."""
    
    response = llm.chat(prompt)
    if response.strip() != 'NO_INFO':
        return response.strip()
    return None

def process_character_relation(chunk, char1, char2, language):
    if language == 'zh':
        prompt = f"""分析以下文本中{char1}和{char2}之间的关系。
    关注他们的互动、彼此的感觉以及关系动态，贴合原文。
    如果文本中不包含关于他们关系的相关信息，请回复 'NO_INFO'。
    
    文本：
    {chunk}
    
    提供他们关系的简明描述。"""
    else:
        prompt = f"""Analyze the relationship between {char1} and {char2} in the following text.
        Focus on their interaction, feelings towards each other, and relationship dynamics.
        If the text doesn't contain relevant information about their relationship, respond with 'NO_INFO'.
        
        Text:
        {chunk}
        
        Provide a concise description of their relationship."""
    
    response = llm.chat(prompt)
    if response.strip() != 'NO_INFO':
        return response.strip()
    return None

def process_location_chunk(chunk, location_name, language):
    if language == 'zh':
        prompt = f"""分析以下文本并提取关于{location_name}的信息。
    关注其物理描述、重要性和关键特征，贴合原文。
    如果文本中不包含关于{location_name}的相关信息，请回复 'NO_INFO'。
    
    文本：
    {chunk}
    
    提供该地点的简明描述。"""
    else:
        prompt = f"""Analyze the following text and extract information about {location_name}.
        Focus on its physical description, significance, and key features.
        If the text doesn't contain relevant information about {location_name}, respond with 'NO_INFO'.
        
        Text:
        {chunk}
        
        Provide a concise description of the location."""
    
    response = llm.chat(prompt)
    if response.strip() != 'NO_INFO':
        return response.strip()
    return None

def update_character_info(character_name, new_profile):
    # Ensure character exists in target_characters_info
    if character_name not in target_characters_info:
        target_characters_info[character_name] = get_default_character_info(
            character_name, language, [name for name in target_character_names if name != character_name]
        )
    
    # Ensure profile field exists
    if "profile" not in target_characters_info[character_name]:
        target_characters_info[character_name]["profile"] = ""
    
    if new_profile:
        current_profile = target_characters_info[character_name]["profile"]
        if current_profile:
            target_characters_info[character_name]["profile"] = current_profile + "\n" + new_profile
        else:
            target_characters_info[character_name]["profile"] = new_profile

def update_character_relation(char1, char2, new_relation):
    if new_relation:
        char1_code = convert_name_to_code(char1, language)
        char2_code = convert_name_to_code(char2, language)
        
        # Ensure char1 exists in target_characters_info
        if char1 not in target_characters_info:
            target_characters_info[char1] = get_default_character_info(
                char1, language, [name for name in target_character_names if name != char1]
            )
        
        # Ensure relation dictionary exists for char1
        if "relation" not in target_characters_info[char1]:
            target_characters_info[char1]["relation"] = {}
        
        # Ensure relation structure exists for char2
        if char2_code not in target_characters_info[char1]["relation"]:
             target_characters_info[char1]["relation"][char2_code] = {
                "relation": [], 
                "detail": ""
             }

        current_relation = target_characters_info[char1]["relation"][char2_code]["detail"]
        if current_relation:
            target_characters_info[char1]["relation"][char2_code]["detail"] = current_relation + "\n" + new_relation
        else:
            target_characters_info[char1]["relation"][char2_code]["detail"] = new_relation

def update_location_info(location_name, new_description):
    location_code = convert_name_to_code(location_name,language)
    if location_code not in target_locations_info:
        target_locations_info[location_code] = get_defaule_location_info(location_name, language)
    
    if new_description:
        current_description = target_locations_info[location_code]["description"]
        if current_description:
            target_locations_info[location_code]["description"] = current_description + "\n" + new_description
        else:
            target_locations_info[location_code]["description"] = new_description

def save_role_info(role_info):
    """Save individual role information to specified path"""
    role_code = role_info["role_code"]
    role_dir = f"./data/roles/{book_source}/{role_code}"
    ensure_dir(role_dir)
    
    role_path = f"{role_dir}/role_info.json"
    save_json_file(role_path, role_info)
    return role_path

def save_location_info(locations_info):
    """Save all location information to specified path"""
    location_dir = f"./data/locations"
    ensure_dir(location_dir)
    
    location_path = f"{location_dir}/{book_source}.json"
    save_json_file(location_path, locations_info)
    return location_path

def save_world_info(world_info):
    world_dir = f"./data/worlds/{book_source}"
    ensure_dir(world_dir)
    
    world_path = f"{world_dir}/general.json"
    save_json_file(world_path, world_info)
    return world_path

def save_map(target_location_names,default_distance = 1):
    location_codes = [convert_name_to_code(name,language) for name in target_location_names]
    map_dir = f"./data/maps"
    ensure_dir(map_dir)
    
    map_path = f"{map_dir}/{book_source}.csv"
    
    n = len(location_codes)
    matrix = []

    header = [""] + location_codes
    matrix.append(header)

    for i in range(n):
        row = [location_codes[i]]
        for j in range(n):
            if i == j:
                row.append(0)
            else:
                row.append(default_distance)
        matrix.append(row)

    with open(map_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(matrix)
    
    return map_path

def save_json_file(path, data):
    """Save data as JSON file"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_main_characters(text, language):
    """Extract main characters from the text using LLM"""
    if language == 'zh':
        prompt = f"""分析以下文本并识别主要角色。
    关注那些：
    1. 在故事中频繁出现
    2. 对情节有重大影响
    3. 是叙事的核心
    
    对于每个角色，提供他们的名字和一个简短的理由，说明为什么他们很重要。
    格式：名字：理由
    
    文本：
    {text}
    
    列出主要角色（最多10个）："""
    else:
        prompt = f"""Analyze the following text and identify the main characters.
        Focus on characters who:
        1. Appear frequently throughout the story
        2. Have significant impact on the plot
        3. Are central to the narrative
        
        For each character, provide their name and a brief reason why they are important.
        Format: name: reason
        
        Text:
        {text}
        
        List the main characters (maximum 10):"""
    
    response = llm.chat(prompt)
    characters = []
    for line in response.strip().split('\n'):
        if ':' in line:
            name = line.split(':')[0].strip()
            characters.append(name)
    return characters

def extract_key_locations(text, language):
    """Extract key locations from the text using LLM"""
    if language == 'zh':
        prompt = f"""分析以下文本并识别关键地点。
    关注那些：
    1. 经常被提及
    2. 对故事有重要意义
    3. 是情节的核心
    
    对于每个地点，提供它的名字和一个简短的理由，说明为什么它很重要。
    格式：名字：理由
    
    文本：
    {text}
    
    列出关键地点（最多10个）："""
    else:
        prompt = f"""Analyze the following text and identify the key locations.
        Focus on places that:
        1. Are frequently mentioned
        2. Have significant importance to the story
        3. Are central to the plot
        
        For each location, provide its name and a brief reason why it is important.
        Format: name: reason
        
        Text:
        {text}
        
        List the key locations (maximum 10):"""
    
    response = llm.chat(prompt)
    locations = []
    for line in response.strip().split('\n'):
        if ':' in line:
            name = line.split(':')[0].strip()
            locations.append(name)
    return locations

def process_large_text(text, max_length=10000):
    """Process large text by splitting into overlapping chunks"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_length
        if end >= len(text):
            chunks.append(text[start:])
            break
        # Find the last period or newline before max_length
        last_period = text.rfind('.', start, end)
        last_newline = text.rfind('\n', start, end)
        split_point = max(last_period, last_newline)
        if split_point == -1:
            split_point = end
        chunks.append(text[start:split_point + 1])
        start = split_point + 1
    return chunks

def auto_extract_targets(extract_chars=True, extract_locs=True):
    """Automatically extract target characters and locations from the book"""
    print("Starting automatic extraction...")
    
    # Combine all chapter contents
    full_text = ""
    for chapter in data:
        full_text += chapter['content'] + "\n"
    
    # Process text in chunks to handle context limits
    text_chunks = process_large_text(full_text)
    
    # Extract characters and locations from each chunk
    all_characters = set()
    all_locations = set()
    
    for chunk in text_chunks:
        if extract_chars:
            characters = extract_main_characters(chunk, language)
            all_characters.update(characters)
        if extract_locs:
            locations = extract_key_locations(chunk, language)
            all_locations.update(locations)
    
    # Convert sets to lists
    target_character_names = list(all_characters)
    target_location_names = list(all_locations)
    
    print(f"Extracted {len(target_character_names)} main characters and {len(target_location_names)} key locations")
    return target_character_names, target_location_names


if __name__ == "__main__":
    
    target_character_names = config["target_character_names"] if "target_character_names" in config else []
    target_location_names = config["target_location_names"] if "target_location_names" in config else []
    book_path = config["book_path"]
    try:
        book_name = os.path.basename(book_path).split(".")[0]
    except Exception as e:
        book_name = config["book_source"] if config["book_source"] else "new_book_1"
    language = config["language"] if config["language"] else lang_detect(book_name)
    book_source = config["book_source"] if config["book_source"] else book_name
    print(language,book_source)
    for key in config:
        if "API_KEY" in key and config[key]:
            os.environ[key] = config[key]
    target_characters_info = {}
    target_locations_info = {}
    
    
    if config["if_auto_extract"]:
        llm = get_models(config["llm_model_name"])
        data = get_chapters(book_path) # chapters = [{"idx":"","title":"","content":""}]
        
        if not target_character_names:
            print("No target characters specified. Starting automatic extraction...")
            extracted_chars, _ = auto_extract_targets(extract_chars=True, extract_locs=False)
            target_character_names = extracted_chars
            
            # Update config with extracted targets
            config["target_character_names"] = target_character_names
            # config["target_location_names"] = target_location_names # We don't auto-extract locations anymore unless specified
            save_json_file("./extract_config.json", config)
            
            print("Updated config file with extracted characters")
            print(target_character_names)
        
        # Load progress and existing data
        progress = load_progress(book_source)
        print(f"Progress loaded: Chapter {progress['last_chapter_idx']}, Chunk {progress['last_chunk_idx']}")
        
        # Load existing data to memory to continue updating
        existing_chars = load_existing_character_info(book_source)
        target_characters_info.update(existing_chars)
        
        existing_locs = load_existing_location_info(book_source)
        target_locations_info.update(existing_locs)

        # Ensure all target characters have entries in target_characters_info (even if empty)
        for char_name in target_character_names:
             if char_name not in target_characters_info:
                # Initialize if not exists
                pass # Will be initialized in update_character_info
        
        # main
        total_chapters = len(data)
        for idx, chapter in enumerate(data):
            # Skip already processed chapters
            if idx < progress['last_chapter_idx']:
                print(f"Skipping Chapter {chapter.get('idx', idx+1)} (already processed)")
                continue

            print(f"Processing Chapter {chapter.get('idx', idx+1)}: {chapter.get('title', 'Unknown Title')}...")
            text = chapter['content']
            if language == 'en':
                chunks = split_text_by_max_words(text, max_words=2000)
            else:
                chunks = split_text_by_max_words(text, max_words=4000)
            
            start_chunk = 0
            # If resuming current chapter, set start chunk
            if idx == progress['last_chapter_idx']:
                start_chunk = progress['last_chunk_idx'] + 1
                if start_chunk >= len(chunks):
                    # Should not happen if logic is correct, but just in case
                    start_chunk = 0 
            
            for i in range(start_chunk, len(chunks)):
                chunk = chunks[i]
                print(f"  - Processing Chunk {i+1}/{len(chunks)}")
                # Profile
                for character in target_character_names:
                    if character in chunk:
                        new_profile = process_character_chunk(chunk, character, language)
                        if new_profile:
                            print(f"    > Extracted profile for {character}")
                            update_character_info(character, new_profile)
                            # Save immediately
                            if character in target_characters_info:
                                save_role_info(target_characters_info[character])

                # Relation
                for j, char1 in enumerate(target_character_names):
                    for char2 in target_character_names[j+1:]:
                        if char1 in chunk and char2 in chunk:
                            char1_pos = chunk.find(char1)
                            char2_pos = chunk.find(char2)
                            if abs(char1_pos - char2_pos) <= 100:
                                new_relation = process_character_relation(chunk, char1, char2, language)
                                if new_relation:
                                    print(f"    > Extracted relation between {char1} and {char2}")
                                    update_character_relation(char1, char2, new_relation)
                                    # Save immediately (char1 relation updated)
                                    if char1 in target_characters_info:
                                        save_role_info(target_characters_info[char1])

                # Location
                for location in target_location_names:
                    if location in chunk:
                        new_description = process_location_chunk(chunk, location, language)
                        if new_description:
                            print(f"    > Extracted info for location {location}")
                            update_location_info(location, new_description)
                            # Save immediately (optional, can be frequent)
                            save_location_info(target_locations_info)
                
                # Save progress after chunk
                save_progress(book_source, idx, i, completed=False)
        
        # Mark as completed
        save_progress(book_source, len(data)-1, 0, completed=True)

        # Replace the original save results section
        print("Starting to save extracted data (Final check)...")

        # Save role information
        for role_info in target_characters_info.values():
            role_path = save_role_info(role_info)
            print(f"Role information saved: {role_path}")

        # Save location information
        location_path = save_location_info(target_locations_info)
        print(f"Location information saved: {location_path}")

        print(f"Data extraction completed!")
        print(f"Role information saved to ./data/roles/{book_source}/")
        print(f"Location information saved to {location_path}")
    else:
        for role_name in target_character_names:
            target_characters_info[convert_name_to_code(role_name,language)] = get_default_character_info(role_name,language,[name for name in target_character_names if name != role_name])
        for role_info in target_characters_info.values():
            role_path = save_role_info(role_info)
            print(f"Role information saved: {role_path}")

        for loc_name in target_location_names:
            target_locations_info[convert_name_to_code(loc_name,language)] = get_defaule_location_info(loc_name,language)
        location_path = save_location_info(target_locations_info)
        print(f"Location information saved: {location_path}")

    world_path = save_world_info({
    "source": book_source,
    "world_name": "",
    "description": "",
    "language":language    
    })
    print(f"World information saved: {world_path}")
    
    map_path = save_map(target_location_names, 1)
    print(f"Map saved: {map_path}")
    
    preset = {
        "experiment_subname": "1",
        "world_file_path":f"./data/worlds/{book_source}/general.json",
        "map_file_path":f"./data/maps/{book_source}.csv",
        "loc_file_path":f"./data/locations/{book_source}.json",
        "role_file_dir":"./data/roles/",
        "role_agent_codes":[convert_name_to_code(name,language) for name in target_character_names],
        "intervention":"",
        "script":"",
        "source":book_source,
        "language":language

    }
    ensure_dir("./experiment_presets/")
    preset_path = f"./experiment_presets/{book_source}.json"
    save_json_file(preset_path,preset)
    print(f"Preset generated: {preset_path}")