
from memory_manager import (
    load_memory,
    save_memory,
    load_candidate_memories,
    save_candidate_memories,
    update_name,
    add_project,
    add_preference
)


def add_profile(memory, content):
    """
    새로운 프로필 정보를 추가한다.
    기존 profile 딕셔너리는 유지하고,
    추가 정보는 additional_profile 목록에 저장한다.
    """

    if "additional_profile" not in memory:
        memory["additional_profile"] = []

    if content not in memory["additional_profile"]:
        memory["additional_profile"].append(content)

    return memory


def add_goal(memory, content):
    """
    새로운 목표를 장기 기억에 추가한다.
    """

    if "goals" not in memory:
        memory["goals"] = []

    if content not in memory["goals"]:
        memory["goals"].append(content)

    return memory


def add_other(memory, content):
    """
    기타 기억을 장기 기억에 추가한다.
    """

    if "other_memories" not in memory:
        memory["other_memories"] = []

    if content not in memory["other_memories"]:
        memory["other_memories"].append(content)

    return memory


def approve_candidate(memory, candidate):
    """
    사용자가 승인한 기억 후보를
    장기 기억에 적절한 형태로 추가한다.
    """

    memory_type = candidate.get("type")
    content = candidate.get("content")

    if not isinstance(content, str) or not content.strip():
        print("오류: 기억 내용이 올바르지 않습니다.")
        return False

    if memory_type == "name":
        update_name(memory, content)

    elif memory_type == "profile":
        add_profile(memory, content)

    elif memory_type == "preference":
        add_preference(memory, content)

    elif memory_type == "project":
        add_project(memory, content)

    elif memory_type == "goal":
        add_goal(memory, content)

    elif memory_type == "other":
        add_other(memory, content)

    else:
        print(f"알 수 없는 기억 유형입니다: {memory_type}")
        return False

    return True


def review_memories():
    """
    기억 후보를 하나씩 확인하고,
    사용자의 선택에 따라 승인하거나 보류한다.
    """

    memory = load_memory()
    candidates = load_candidate_memories()

    if not candidates:
        print("\n검토할 기억 후보가 없습니다!")
        return

    print("=" * 60)
    print("장기 기억 검토 시스템")
    print("=" * 60)

    index = 0

    while index < len(candidates):

        candidate = candidates[index]

        print("\n" + "-" * 60)
        print(f"기억 후보 {index + 1} / {len(candidates)}")
        print("-" * 60)

        print(f"유형: {candidate.get('type', 'unknown')}")
        print(f"내용: {candidate.get('content', '')}")
        print(f"이유: {candidate.get('reason', '없음')}")

        print("\n1. 승인")
        print("2. 보류")
        print("3. 폐기")
        print("4. 수정 후 승인")
        print("5. 검토 종료")

        choice = input("\n선택: ").strip()

        if choice == "1":

            if approve_candidate(memory, candidate):

                try:
                    # 먼저 장기 기억을 저장한다.
                    save_memory(memory)

                    # 저장에 성공한 경우에만 후보 목록에서 제거한다.
                    candidates.pop(index)
                    save_candidate_memories(candidates)

                    print("\n기억을 장기 기억에 등록했습니다!")

                except OSError as e:
                    print(f"\n파일 저장 중 오류가 발생했습니다: {e}")
                    print("기억 후보는 가능한 한 유지한 상태로 검토를 종료합니다.")
                    break

        elif choice == "2":

            print("\n이 기억은 보류합니다.")
            index += 1

        elif choice == "3":

            candidates.pop(index)    # index는 올리지 않는다 (다음 후보가 같은 자리로 올라옴)
            save_candidate_memories(candidates)
            print("\n후보를 폐기했습니다.")

        elif choice == "4":

            new_content = input("수정할 내용: ").strip()

            if not new_content:
                print("\n내용이 비어 있어서 취소했습니다.")
                continue

            edited = dict(candidate)       # 원본은 두고 복사본의 내용만 고침
            edited["content"] = new_content

            if approve_candidate(memory, edited):

                try:
                    save_memory(memory)
                    candidates.pop(index)
                    save_candidate_memories(candidates)
                    print("\n수정한 내용을 장기 기억에 등록했습니다!")

                except OSError as e:
                    print(f"\n파일 저장 중 오류가 발생했습니다: {e}")
                    break

        elif choice == "5":

            print("\n기억 검토를 종료합니다.")
            break


        else:

            print("\n잘못된 입력입니다. 다시 선택해주세요.")

    print("\n" + "=" * 60)
    print("기억 검토 종료!")
    print(f"남은 기억 후보: {len(candidates)}개")
    print("=" * 60)


if __name__ == "__main__":
    review_memories()
