from ollama import chat
import json
import os
from datetime import datetime

from memory_manager import (
    load_memory,
    build_memory_prompt,
    load_candidate_memories,
    save_candidate_memories,
    add_candidate_memory,
)

MODEL = "takopi2"
MEMORY_FILE = "conversation.json"
SHOW_DEBUG = False  # 디버그 모드 설정 (True로 변경하면 원본 반환값 출력)

# 최근 대화 중 타코피에게 전달할 메시지 수
MAX_RECENT_MESSAGES = 20

# 장기 기억 후보 판단 함수


def judge_memory_candidate(user_input, memory):
    """
    사용자의 입력에서 장기 기억으로 남길 가치가 있는 정보를
    모두 추출한다.

    반환값:
    {
        "candidates": [
            {
                "type": "...",
                "content": "...",
                "reason": "..."
            }
        ]
    }

    기억할 정보가 없으면 candidates는 빈 목록이다.
    """

    memory_text = build_memory_prompt(memory)

    prompt = f"""
너는 타코피의 장기 기억 후보를 추출하는 역할이다.

사용자의 말에서 앞으로도 오랫동안 유효할 가능성이 높은
사용자 개인에 관한 정보를 찾아라.

중요한 원칙:
한 문장에 기억할 가치가 있는 정보가 여러 개 있다면,
각 정보를 빠짐없이 별도의 기억 후보로 추출한다.

하나의 정보만 선택하거나 여러 정보를 하나로 뭉뚱그리지 않는다.
각 후보는 서로 독립적으로 이해할 수 있도록 작성한다.

[기억할 수 있는 정보]
- 사용자의 이름과 지속적인 기본 정보
- 사용자가 직접 밝힌 지속적인 취향과 선호
- 사용자의 장기적인 목표
- 사용자가 지속적으로 진행하는 프로젝트
- 장기적으로 이어지는 학습이나 활동
- 사용자가 타코피와의 상호작용에서 중요하게 여기는 선호
- 반복적으로 나타나는 습관이나 가치관

[기억하지 않을 정보]
- 오늘, 방금, 어제 등 특정 시점의 일회성 활동
- 일시적인 감정이나 상태
- 단순한 인사나 질문
- 일반적인 지식이나 사용자와 무관한 사실
- 단순한 가정, 농담, 상상 속 상황
- 장기적인 의미가 없는 일회성 사건

[지속적인 활동 판단]
특정 활동을 오늘 한 번 했다는 사실만으로는 기억하지 않는다.
하지만 사용자가 해당 활동을 꾸준히 하고 있다고 명시하거나,
장기적으로 지속하는 활동임을 분명하게 밝힌 경우에는
기억 후보로 추출할 수 있다.

[정보 추출 원칙]
1. 사용자가 실제로 말한 내용을 기준으로 판단한다.
2. 사용자가 말하지 않은 성격, 동기, 취향, 감정을 추측하여 추가하지 않는다.
3. 하나의 문장에 목표와 선호 등 여러 정보가 있다면 각각 추출한다.
4. 기존 기억과 관련된 정보라도 새로운 세부 정보가 있다면
   기억 후보에서 임의로 제외하지 않는다.
5. 기존 기억과의 중복 여부는 여기서 판단하지 않는다.
   중복 검사는 별도의 함수가 담당한다.
6. 기존 기억에 이미 있는 정보만 반복한 경우에도
   이 함수에서는 기억할 가치가 있는지 자체를 판단한다.
7. 각 후보는 하나의 핵심 정보만 담도록 간결하게 작성한다.
8. 같은 내용을 표현만 바꾸어 여러 후보로 중복 추출하지 않는다.
9. 장기적으로 기억할 가치가 있는 정보가 없다면 빈 목록을 반환한다.

[현재 타코피의 장기 기억]
{memory_text}

[사용자의 새로운 말]
{user_input}

[type]은 다음 중 하나를 사용한다.
- name: 사용자의 이름
- profile: 사용자에 관한 지속적인 기본 정보
- preference: 취향, 선호, 비선호
- project: 지속적으로 진행하는 프로젝트나 활동
- goal: 장기적인 목표
- other: 위 유형에 해당하지 않는 예외적인 장기 기억

반드시 다음 JSON 형식으로만 대답한다.

{{
    "candidates": [
        {{
            "type": "goal",
            "content": "AI 개발자가 되고 싶어 함",
            "reason": "장기적인 직업적 목표이기 때문이다."
        }}
    ]
}}

위 내용은 형식의 예시일 뿐이다.
실제 사용자 발언에서 추출한 정보만 반환한다.
기억할 정보가 없다면 다음과 같이 반환한다.

{{
    "candidates": []
}}

다른 설명이나 마크다운 코드 블록은 추가하지 마라.
"""

    try:
        response = chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "너는 장기 기억 후보를 추출하는 담당자이다.",
                },
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.1, "num_ctx": 8192, "num_predict": 1024},
            think=False,
        )

        result_text = response.message.content.strip()

        # JSON 객체 부분을 추출한다.
        start = result_text.find("{")
        end = result_text.rfind("}")

        if start == -1 or end == -1 or end < start:
            raise ValueError("JSON 객체를 찾을 수 없다.")

        result = json.loads(result_text[start : end + 1])

        if not isinstance(result, dict):
            raise ValueError("응답이 JSON 객체가 아니다.")

        candidates = result.get("candidates")

        if not isinstance(candidates, list):
            raise ValueError("candidates가 목록이 아니다.")

        allowed_types = {
            "name",
            "profile",
            "preference",
            "project",
            "goal",
            "other",
        }

        validated_candidates = []

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            candidate_type = candidate.get("type")
            content = candidate.get("content")
            reason = candidate.get("reason")

            if candidate_type not in allowed_types:
                continue

            if not isinstance(content, str) or not content.strip():
                continue

            if not isinstance(reason, str):
                continue

            validated_candidates.append(
                {
                    "type": candidate_type,
                    "content": content.strip(),
                    "reason": reason.strip(),
                }
            )

        return {"candidates": validated_candidates}

    except (json.JSONDecodeError, ValueError, AttributeError, TypeError) as e:
        print(f"\n[기억 판단 오류] {e}")

        return {"candidates": []}

    except Exception as e:
        print(f"\n[기억 판단 오류] {e}")

        return {"candidates": []}


def compare_memory_candidate(new_candidate, existing_candidates, memory):
    """
    새로운 기억 후보를 기존 장기 기억 및 기억 후보와 비교한다.

    반환값:
    {
        "relation": "new" / "duplicate" / "error",
        "reason": "판단 이유"
    }
    """

    if not existing_candidates and not memory:
        return {
            "relation": "new",
            "reason": "기존 장기 기억과 기억 후보가 모두 없다.",
        }

    prompt = f"""
너는 타코피의 장기 기억을 관리하는 담당자이다.

새로운 기억 후보가 기존 기억과 의미적으로 중복되는지 판단해라.

[판단 규칙]

1. 단어가 다르더라도 핵심적으로 같은 사실이나 선호,
목표를 나타낸다면 "duplicate"로 판단한다.

2. 같은 주제에 관한 정보라도 서로 다른 사실을 담고 있다면
"new"로 판단한다.

3. 기존 기억보다 새로운 후보에 더 구체적인 정보가 있더라도,
핵심 정보가 동일하다면 우선 "duplicate"로 판단한다.
단, 새로운 후보에 추가된 정보가 있다는 사실을 reason에 명시한다.
정보를 합치는 작업은 이 함수에서 수행하지 않는다.

4. 기존 기억에 없는 새로운 세부 선호나 사실은
관련된 기억이 있다는 이유만으로 중복 처리하지 않는다.

5. 이름, 프로젝트, 취향, 목표 등 기억의 유형을 고려하되,
유형이 다르다는 이유만으로 중복을 놓치지 않는다.

6. 새로운 후보가 기존 기억과 모순되는 경우,
단순한 중복으로 단정하지 않는다. 현재 선택지에서는
"new"로 분류하고, reason에 정보 충돌 가능성을 명시한다.
이후 별도의 검토가 필요하다.

[기존 장기 기억]
{json.dumps(memory, ensure_ascii=False, indent=4)}

[기존 기억 후보]
{json.dumps(existing_candidates, ensure_ascii=False, indent=4)}

[새로운 기억 후보]
{json.dumps(new_candidate, ensure_ascii=False, indent=4)}

반드시 다음 JSON 형식으로만 대답해라.

{{
    "relation": "new 또는 duplicate",
    "reason": "판단 이유"
}}

다른 설명이나 마크다운 코드 블록은 추가하지 마라.
"""

    try:
        response = chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "너는 기억의 중복 여부를 신중하게 판단하는 관리자이다.",
                },
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.1, "num_ctx": 8192, "num_predict": 256},
            think=False,
        )

        result_text = response.message.content.strip()
        if SHOW_DEBUG:
            print(f"\n[중복 검사 원본 응답] {result_text!r}")

        # 마크다운 코드 블록이 포함된 경우를 처리한다.
        if result_text.startswith("```"):
            lines = result_text.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            result_text = "\n".join(lines).strip()

        # JSON 객체 부분을 추출한다.
        start = result_text.find("{")
        end = result_text.rfind("}")

        if start == -1 or end == -1 or end < start:
            raise ValueError("JSON 객체를 찾을 수 없다.")

        comparison = json.loads(result_text[start : end + 1])

        # 응답 구조와 값 검증
        if not isinstance(comparison, dict):
            raise ValueError("응답이 JSON 객체가 아니다.")

        if comparison.get("relation") not in ("new", "duplicate"):
            raise ValueError("relation 값이 올바르지 않다.")

        if not isinstance(comparison.get("reason"), str):
            raise ValueError("reason이 문자열이 아니다.")

        return comparison

    except (json.JSONDecodeError, ValueError, AttributeError, TypeError) as e:
        print(f"\n[기억 중복 검사 오류] {e}")

        return {
            "relation": "error",
            "reason": "모델 응답의 형식이 올바르지 않다.",
        }

    except Exception as e:
        print(f"\n[기억 중복 검사 오류] {e}")

        return {
            "relation": "error",
            "reason": "중복 검사 중 예기치 않은 오류가 발생했다.",
        }


# 타코피와의 마지막 대화로부터 경과한 시간을 계산하는 함수
def get_elapsed_time(messages):
    """
    가장 최근 assistant 메시지의 timestamp와
    현재 시각의 차이를 계산한다.
    """

    last_timestamp = None

    # 가장 최근 assistant 메시지 찾기
    for message in reversed(messages):
        if message.get("role") == "assistant" and message.get("timestamp"):
            last_timestamp = message["timestamp"]
            break

    # 이전 대화가 없다면 None 반환
    if last_timestamp is None:
        return None

    try:
        last_time = datetime.fromisoformat(last_timestamp)
        current_time = datetime.now().astimezone()

        elapsed = current_time - last_time

        return elapsed

    except (ValueError, TypeError):
        return None


# 마지막 대화 이후 경과 시간을 타코피에게 알려줄 문장 생성 함수
def build_time_context(messages):
    """
    마지막 대화 이후 경과 시간을 타코피에게 전달할 문장으로 만든다.
    """

    elapsed = get_elapsed_time(messages)

    if elapsed is None:
        return "이전 대화의 시간이 기록되어 있지 않다."

    total_seconds = int(elapsed.total_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if days > 0:
        return f"마지막으로 이야기한 뒤 약 {days}일이 지났다."
    elif hours > 0:
        return f"마지막으로 이야기한 뒤 약 {hours}시간 {minutes}분이 지났다."
    elif minutes > 0:
        return f"마지막으로 이야기한 뒤 약 {minutes}분이 지났다."
    else:
        return f"마지막으로 이야기한 뒤 약 {seconds}초가 지났다."

class Takopi:
    def __init__(self):
        self.model = MODEL

        # 1. 기존 대화 기록 로드 (conversation.json)
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
        else:
            self.messages = []

        # 2. 장기 기억 기록 로드 (memory.json)
        self.memory = load_memory()
        

    def main(self):
        print("타코피와의 대화를 시작해보자!")
        print("종료하려면 /bye 를 입력해줘.\n")

        while True:
            user_input = input("나 >>> ")

            if user_input.strip() == "/bye":
                print("대화를 종료할게 피!")
                break

            if not user_input.strip():
                continue

            # 사용자의 새 입력이 들어온 현재 시각 기록
            timestamp = datetime.now().astimezone().isoformat()

            # 사용자의 새 입력을 전체 대화 기록에 추가
            self.messages.append(
                {"role": "user", "content": user_input, "timestamp": timestamp}
            )

            try:
                # memory.json 내용을 프롬프트로 변환
                memory_text = build_memory_prompt(self.memory)

                # 마지막 대화 이후 경과 시간을 타코피에게 알려줄 문장 생성
                time_context = build_time_context(self.messages)

                # 전체 대화 파일에서 최근 대화 분리 및 메시지 결합
                # conversation.json은 계속 커지지만 모델에게는 최근 N개만 전달
                recent_messages = self.messages[-MAX_RECENT_MESSAGES:]

                # 타코피에게 최종 전달할 대화 컨텍스트 구성
                context_messages = (
                    [
                        {
                            "role": "user",
                            "content": f"""다음은 타코피의 장기 기억이야.
                대화할 때 참고하되, 타코피의 성격과 말투는 기존 규칙을 그대로 유지해.

                {memory_text}"""
                        },
                        {
                            "role": "system",
                            "content": f"""현재 대화 시간 정보:

                {time_context}

                이 시간 정보는 실제로 측정된 현재 대화의 시간 정보이며 사실이다.

                타코피는 평소 대화에서는 이 정보를 굳이 언급하지 않아도 된다.
                하지만 사용자가 마지막 대화 이후 얼마나 시간이 지났는지, 언제 이야기했는지,
                얼마나 오랜만인지 등 시간에 관한 질문을 하면 반드시 이 정보를 참고해서 대답한다.

                시간을 알 수 없다고 말하거나 시간을 측정할 수 없다고 말하지 않는다.
                위에 제공된 시간 정보를 사용해서 자연스럽게 대답한다."""
                        },
                    ]
                    + recent_messages
                    + [
                        {
                            "role": "user",
                            "content": f"""[타코피의 고유 말투 유지 규칙]

                과거 대화 기록에 등장하는 말투와 관계없이
                타코피는 자신의 고유한 성격과 말투를 유지한다.

                타코피는 평소 문장 끝에 자연스럽게 '피!'를 붙인다.

                예시:
                안녕 피!
                정말 기뻐 피!
                같이 놀자 피!
                고마워 피!

                과거 대화의 말투를 그대로 모방하지 않는다.
                타코피 고유의 말투를 일관되게 유지한다.

                ---

                사용자의 질문:
                {recent_messages[-1]["content"]}"""
                        }
                    ]
                )

                # --------------------------------------------------------
                # Ollama 호출 (전체 messages 대신 컨텍스트용 context_messages 전달)
                # --------------------------------------------------------
                # memory.json의 하드웨어 설정 수치 로드 및 예외 처리용 기본값 세팅
                project_config = self.memory.get("takopi_project", {})
                ctx_limit = project_config.get("current_context_limit", 16384)
                pred_limit = project_config.get("current_generation_limit", 3072)

                # print("\n===== 컨텍스트 확인 =====")
                # print("메시지 개수:", len(context_messages))
                # print("ctx_limit:", ctx_limit)
                # print("pred_limit:", pred_limit)

                # for i, msg in enumerate(context_messages):
                #     print(f"[{i}] role={msg['role']}")
                #     print(f"메시지 길이: {len(msg['content'])}")
                #     print(msg["content"])
                #     print("-------------------------")
                response = chat(
                    model=self.model,
                    messages=context_messages,
                    think=False,
                    options={"num_ctx": ctx_limit, "num_predict": pred_limit},
                )
                # print("\n===== 생성 상태 확인 =====")
                # print("종료 사유:", response.done_reason)
                # print("입력 토큰:", response.prompt_eval_count)
                # print("출력 토큰:", response.eval_count)
                # print("출력 내용:", repr(response.message.content))
                # print("==========================")

                # 안전하게 딕셔너리 형태로 콘텐츠 추출
                full_content = response.message.content

                # 생각 태그 내부 내용 청소 (Gemma 4 추론 출력 대응)
                if "<|think|>" in full_content:
                    parts = full_content.split("</|think|>")
                    takopi_reply = (
                        parts[-1].strip()
                        if len(parts) > 1
                        else full_content.split("<|think|>")[-1].strip()
                    )
                else:
                    takopi_reply = full_content.strip()
                if not takopi_reply:
                    takopi_reply = full_content

                print(f"타코피 >>> {takopi_reply}\n")

                # 기억할 가치가 있다고 판단된 경우
                memory_result = judge_memory_candidate(user_input, self.memory)

                if SHOW_DEBUG:
                    print("\n[기억 판단 원본 반환값]")
                    print(json.dumps(memory_result, ensure_ascii=False, indent=4))
                    
                memory_candidates = memory_result.get("candidates", [])

                if memory_result.get("error"):
                    print("[기억 판단] 판단 중 오류가 나서 이번엔 건너뛸게!")

                elif not memory_candidates:
                    print("[기억 판단] 기억할 만한 새로운 정보가 없어!")

                else:
                    candidates = load_candidate_memories()

                    for memory_candidate in memory_candidates:
                        # 장기 기억과 기존 기억 후보를 모두 비교한다.
                        comparison = compare_memory_candidate(
                            memory_candidate, candidates, self.memory
                        )

                        if comparison["relation"] == "new":
                            candidates = add_candidate_memory(
                                candidates,
                                memory_candidate["type"],
                                memory_candidate["content"],
                                memory_candidate["reason"],
                            )

                            save_candidate_memories(candidates)

                            print("[기억 저장] 새로운 기억 후보를 저장했어!")

                        elif comparison["relation"] == "duplicate":
                            print(
                                "[기억 저장] 기존 기억과 중복되어 저장하지 않았어!"
                            )

                        else:
                            print(
                                "[기억 저장] 중복 여부를 판단하지 못해 저장하지 않았어."
                            )
                        if SHOW_DEBUG:
                            print("\n[기억 판단]")
                            print(f"종류: {memory_candidate['type']}")
                            print(f"내용: {memory_candidate['content']}")
                            print(f"이유: {memory_candidate['reason']}")
                            
                                                
                # 타코피의 답변이 생성된 현재 시각 기록
                assistant_timestamp = datetime.now().astimezone().isoformat()

                # 타코피의 답변을 전체 대화 기록(messages)에 추가
                self.messages.append(
                    {
                        "role": "assistant",
                        "content": full_content,
                        "timestamp": assistant_timestamp,
                    }
                )

                # -----------------------------
                # 대화 기록 파일에 저장 (전체 기록 보존)
                # -----------------------------
                with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.messages, f, ensure_ascii=False, indent=4)

            except Exception as e:
                # 오류가 난 턴의 user 메시지를 되돌린다 (user가 연속으로 쌓이는 것 방지)
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()
                print(f"\n[오류 발생] 대화 중 문제가 생겼어 피!: {e}\n")

if __name__ == "__main__":
    takopi = Takopi()
    takopi.main()
