import sys
sys.path.append("../")
from bw_utils import *
from extract_utils import *
import os
import json
from datetime import datetime

config = load_json_file("./extract_config.json")

book_path = config["book_path"]
try:
    book_name = os.path.basename(book_path).split(".")[0]
except Exception as e:
    book_name = config["book_source"] if config["book_source"] else "new_book_1"
language = config["language"] if config["language"] else lang_detect(book_name)
book_source = config["book_source"] if config["book_source"] else book_name
print(language,book_source)

def load_progress(book_source):
    """Load processing progress"""
    progress_file = f"./data/.progress_settings_{book_source}.json"
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
    progress_file = f"./data/.progress_settings_{book_source}.json"
    ensure_dir("./data/")
    progress = {
        "last_chapter_idx": chapter_idx,
        "last_chunk_idx": chunk_idx,
        "completed": completed,
        "timestamp": str(datetime.now())
    }
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def load_existing_settings(book_source):
    """Load existing settings from jsonl file"""
    path = f"./worlds/{book_source}/world_details/{book_source}.jsonl"
    dic_settings = {}
    lis_settings = []
    
    if os.path.exists(path):
        print(f"Loading existing settings from {path}...")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        term = item.get('term', '')
                        if term:
                            # Reconstruct dictionary structure
                            # Check if it's already in dic_settings (should not happen in valid jsonl but possible)
                            if term not in dic_settings:
                                dic_settings[term] = {
                                    'nature': item.get('nature', []),
                                    'detail': item.get('detail', []),
                                    'source': item.get('source', [])
                                }
                            else:
                                # Merge if duplicate terms exist
                                dic_settings[term]['nature'].extend(item.get('nature', []))
                                dic_settings[term]['detail'].extend(item.get('detail', []))
                                dic_settings[term]['source'].extend(item.get('source', []))
                        else:
                            lis_settings.append(item)
        except Exception as e:
             print(f"Error loading existing settings: {e}")
             
    print(f"Loaded {len(dic_settings)} terms and {len(lis_settings)} general settings")
    return dic_settings, lis_settings

def incremental_save_settings(book_source, dic_settings, lis_settings):
    """Save settings to jsonl file"""
    path = f"./worlds/{book_source}/world_details/{book_source}.jsonl"
    ensure_dir(os.path.dirname(path))
    
    # Prepare list for saving
    dic_settings2 = dict(sorted(dic_settings.items(), key=lambda x:x[0]))
    all_settings = []
    
    # Add non-term settings
    all_settings.extend(lis_settings)
    
    # Add term settings
    for term in dic_settings2:
        value = dic_settings2[term]
        all_settings.append({
            'term': term, 
            'nature': value["nature"], 
            'detail': value["detail"],
            'source': value["source"]
        })
    
    save_jsonl_file(path, all_settings)
    return path
for key in config:
    if "API_KEY" in key and config[key]:
        os.environ[key] = config[key]

llm = get_models(config["llm_model_name"])
data = get_chapters(book_path) # chapters = [{"idx":"","title":"","content":""}]

# Load progress and existing data
progress = load_progress(book_source)
print(f"Progress loaded: Chapter {progress['last_chapter_idx']}, Chunk {progress['last_chunk_idx']}")

dic_settings, lis_settings = load_existing_settings(book_source)

EXTRACT_SETTINGS_PROMPT = """
Identify the world-building elements and facts reflected in the given text from {source}, 
focusing on unique aspects such as magical systems in fantasy works, levels of technological advancement in science fiction, 
pivotal historical events, cultural consensus... 
Utilize your reasoning skills to uncover the underlying facts hidden beneath the surface.
** Make sure the settings you extract are common to most people in the world **

- Target text:
{text}

Notice that:
1.**Don't include any name, action, status of certain characters**. 
If the character's actions reflect certain social norms or settings, keep only the reflected part.
2.Don't include temporary event or seasonal description like 'It's raining...' or 'It's winter...'
3.Avoid using ambiguous or trival pronouns like 'their','The room'. 
4.Avoid describing specific environment, such as 'The room's small and shabby condition...', 

- If the fact is about an infrequent term or terms, write the extracted fat following this format:
[term](nature):detail
- If the fact contains no certain term, write it with natural language. 
Each extracted fact should be separated by a newline.
"""

EXTRACT_SETTINGS_PROMPT_ZH = """
识别来自《{source}》的给定文本中反映的世界观设定要素和事实，
重点关注独特方面，如奇幻作品中的魔法系统、科幻小说中的科技水平、关键历史事件、文化共识等……
运用你的推理能力，挖掘隐藏在表面之下的潜在事实。
** 确保你提取的设定是该世界中大多数人所共知的/普遍存在的 **

- 目标文本：
{text}

注意：
1. **不要包含特定角色的任何名字、动作、状态**。
如果角色的行为反映了某些社会规范或设定，只保留反映出的规范部分。
2. 不要包含临时事件或季节性描述，如“天下着雨……”或“现在是冬天……”。
3. 避免使用模糊或微不足道的代词，如“他们的”、“房间”。
4. 避免描述特定环境，如“房间狭小破旧……”，除非它反映了普遍的世界设定。

- 如果事实是关于某个生僻术语或特定名词，请按照以下格式书写提取的事实：
[术语](性质):详细描述
- 如果事实不包含特定术语，请使用自然语言书写。
每个提取的事实应单独占一行。
"""

if language == 'zh':
    EXTRACT_SETTINGS_PROMPT = EXTRACT_SETTINGS_PROMPT_ZH
    EXTRACT_SETTINGS_PROMPT += """
==输出示例（请使用目标文本相同的语言）==
[多斯拉克](民族):多斯拉克文化中，马是重要的象征，战士的地位和成就与他们的骑术密切相关。
[黑暗森林法则](理论):黑暗森林法则是对人类未能发现外星文明的一种假想解释。该假说认为宇宙中存在许多外星文明，但它们都沉默而多疑。该假说假设任何航天文明都会将其他智能生命视为不可避免的威胁，并因此摧毁任何暴露其行踪的新生文明。
在这个世界，在室内打伞被视为一种不吉利的行为。
"""
else:
    EXTRACT_SETTINGS_PROMPT += """
==Example output(use the same language with the Target text)==
[Invisibility Cloak](artifact):Invisibility Cloak grants the wearer complete invisibility by concealing them from sight, making it an invaluable tool for stealth and evasion.
In this world, throwing stones into rivers is considered an unlucky symbol.
    """


    
def update_settings(dic,lis,settings,source):
    settings = clear_blank_row(settings)
    for row in settings.split("\n"):
        parsed = parse_fact(row)
        if parsed:
            term,nature,detail = parsed
            if not term:
                lis.append({'term':term,'nature':[nature],'detail':[detail],'source':[source]})
                continue
            if term not in dic:
                dic[term] = {"nature":[nature],
                            "detail":[detail],
                            "source":[source]}
            else:
                if nature not in dic[term]["nature"]:
                    dic[term]["nature"].append(nature)
                if source not in dic[term]["source"]:
                    dic[term]["source"].append(source)
                dic[term]["detail"].append(detail)
        else:
            lis.append({'term':"",'nature':"",'detail':[row],'source':[source]})
        
    return dic,lis


for idx_c, chapter in enumerate(data):
    # Skip processed chapters
    if idx_c < progress['last_chapter_idx']:
        print(f"Skipping Chapter {chapter['idx']}: {chapter['title']} (already processed)")
        continue

    text = chapter['content']
    title = chapter['title']
    idx = chapter["idx"]
    print(f"Processing Chapter {idx}: {title}...")
    if language == 'en':
        chunks = split_text_by_max_words(text,max_words=2000)
    else:
        chunks = split_text_by_max_words(text,max_words=4000)
    
    start_chunk = 0
    if idx_c == progress['last_chapter_idx']:
        start_chunk = progress['last_chunk_idx'] + 1
    
    for i in range(start_chunk, len(chunks)):
        chunk = chunks[i]
        print(f"  - Processing Chunk {i+1}/{len(chunks)}")
        prompt = EXTRACT_SETTINGS_PROMPT.format(**{
            "text":chunk,
            "source":book_source
        })
        output = clear_blank_row(llm.chat(prompt))
        if output:
            print(f"    > Extracted settings:\n{output}")
        dic_settings,lis_settings = update_settings(dic_settings, lis_settings, output,f"{idx}_{title}")
        
        # Incremental save
        incremental_save_settings(book_source, dic_settings, lis_settings)
        save_progress(book_source, idx_c, i, completed=False)

# Final save
path = incremental_save_settings(book_source, dic_settings, lis_settings)
save_progress(book_source, len(data)-1, 0, completed=True)
print(f"Extaction on {book_source} has finished. The extracted settings have been saved to", path)