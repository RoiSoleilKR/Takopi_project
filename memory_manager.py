import json
import os
import shutil


LONG_TERM_MEMORY_FILE = "memory.json"
CANDIDATE_MEMORY_FILE = "candidate_memory.json"


def load_memory():
    """
    memory.json에서 장기 기억을 불러온다.
    파일이 없으면 빈 기억을 반환한다.
    파일 내용이 깨져 있으면 이름을 바꿔 보관하고 빈 기억을 반환한다.
    """

    if not os.path.exists(LONG_TERM_MEMORY_FILE):
        return {}

    try:
        with open(LONG_TERM_MEMORY_FILE, "r", encoding="utf-8") as f:
            memory = json.load(f)

        if not isinstance(memory, dict):
            return {}

        return memory

    except json.JSONDecodeError:
        # 덮어쓰기로 사라지지 않게 이름을 바꿔 보관한다
        os.replace(LONG_TERM_MEMORY_FILE, LONG_TERM_MEMORY_FILE + ".broken")
        print("⚠ memory.json이 손상되어 memory.json.broken으로 옮겼어요.")
        print("  내용을 고친 뒤 파일 이름을 memory.json으로 되돌려 주세요.")
        return {}

    except OSError:
        return {}
    

def load_candidate_memories():
    """
    candidate_memory.json에서 기억 후보를 불러온다.
    파일이 없거나 문제가 있으면 빈 목록을 반환한다.
    """

    if not os.path.exists(CANDIDATE_MEMORY_FILE):
        return []

    try:
        with open(CANDIDATE_MEMORY_FILE, "r", encoding="utf-8") as f:
            candidates = json.load(f)

        if not isinstance(candidates, list):
            return []

        return candidates

    except (json.JSONDecodeError, OSError):
        return []


def save_candidate_memories(candidates):
    """
    기억 후보 목록을 candidate_memory.json에 저장한다.
    """

    with open(CANDIDATE_MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(
            candidates,
            f,
            ensure_ascii=False,
            indent=4
        )


def add_candidate_memory(candidates, memory_type, content, reason):
    """
    새로운 기억 후보를 목록에 추가한다.
    이미 같은 내용의 후보가 있으면 추가하지 않는다.
    """

    # 이미 같은 내용의 기억 후보가 있는지 확인
    for candidate in candidates:
        if candidate.get("content") == content:
            return candidates

    candidate = {
        "type": memory_type,
        "content": content,
        "reason": reason
    }

    candidates.append(candidate)

    return candidates
    
    
def update_name(memory, name):
    memory["name"] = name
    return memory


def add_project(memory, project):
    if "projects" not in memory:
        memory["projects"] = []

    if project not in memory["projects"]:
        memory["projects"].append(project)

    return memory


def add_preference(memory, preference):
    if "preferences" not in memory:
        memory["preferences"] = []

    if preference not in memory["preferences"]:
        memory["preferences"].append(preference)

    return memory


def save_memory(memory):
    """
    장기 기억을 memory.json에 저장한다.
    저장하기 전에 기존 파일을 memory.json.bak으로 백업한다.
    """

    if os.path.exists(LONG_TERM_MEMORY_FILE):
        shutil.copy(LONG_TERM_MEMORY_FILE, LONG_TERM_MEMORY_FILE + ".bak")

    with open(LONG_TERM_MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(
            memory,
            f,
            ensure_ascii=False,
            indent=4
        )



def build_memory_prompt(memory):
    """
    장기 기억을 타코피가 읽을 수 있는
    System 메시지 형태의 문자열로 만든다.
    """

    profile = memory.get("profile", {})

    memory_text = f"""타코피의 장기 기억:

사용자의 이름:
{memory.get("name", "아직 모름")}

사용자의 기본 프로필:
{profile.get("university_major", "모름")}
{profile.get("current_stage", "모름")}

추가 프로필 정보:
"""

    for item in memory.get("additional_profile", []):
        memory_text += f"- {item}\n"

    memory_text += "\n사용자의 프로젝트 정보:\n"

    for project in memory.get("projects", []):
        memory_text += f"- {project}\n"

    memory_text += "\n사용자의 선호 사항:\n"

    for preference in memory.get("preferences", []):
        memory_text += f"- {preference}\n"

    memory_text += "\n사용자의 목표:\n"

    for goal in memory.get("goals", []):
        memory_text += f"- {goal}\n"

    memory_text += "\n기타 기억:\n"

    for item in memory.get("other_memories", []):
        memory_text += f"- {item}\n"

    return memory_text
